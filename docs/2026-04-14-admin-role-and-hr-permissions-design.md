# SmartHR 管理员角色与 HR 权限扩展 · 设计文档

- 日期: 2026-04-14
- 状态: 已确认,待实施
- 影响范围: 后端权限模型、前端菜单与页面、数据库 schema、VPS 部署

## 1. 背景与目标

当前系统只有 `hr` 和 `manager` 两个角色,其中 `manager` 同时承担了"用人经理"(创建职位)和"系统管理员"(账号 CRUD)两项不相关的职责,违反最小权限原则。本次改造拆开这两件事,并补齐以下业务诉求:

1. HR 也能创建/编辑职位(原来只有 manager 可以)
2. 系统能重置任意用户的密码
3. 新增独立的 `admin` 角色,专职账号管理
4. 变更部署到腾讯云 VPS

## 2. 角色与权限矩阵

| 能力 | admin | hr | manager |
|---|:---:|:---:|:---:|
| 建/编辑职位(不限部门) | ❌ | ✅ | ✅ |
| 上传简历 | ❌ | ✅ | ❌ |
| 查看/编辑候选人 | ❌ | ✅ | ✅ |
| 导出 Excel | ❌ | ✅ | ❌ |
| 用户 CRUD + 重置密码 | ✅ | ❌ | ❌ |
| 修改自己的密码 | ✅ | ✅ | ✅ |
| 登录系统 | ✅ | ✅ | ✅ |

设计原则:
- `admin` 纯账号管理员,**看不到**任何业务数据(职位/候选人/简历),降低隐私泄露风险
- `manager` 失去用户管理权限,回归"用人经理"本职
- `hr` 得到职位创建/编辑能力,范围为**全部门**

## 3. 数据模型变更

### 3.1 `users` 表

新增字段:

```sql
ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT 0;
```

语义:
- `true` — 用户下次登录必须先改密码才能使用系统
- `false` — 正常使用

设置规则:

| 场景 | must_change_password |
|---|:---:|
| 迁移时所有现有账号 | `false` |
| 种子 `admin / Admin@2026` | `true` |
| admin 新建的账号 | `true` |
| admin 重置密码后 | `true` |
| 用户自助修改密码成功 | `false` |

### 3.2 Pydantic schema

`UserCreate.role` 正则从 `^(hr|manager)$` 放宽为 `^(hr|manager|admin)$`。
`UserResponse` 增加 `must_change_password: bool`。
新增 `UserUpdate`(可改 display_name、role)。
新增 `AdminResetPasswordRequest`(admin 为他人设新密码)。

## 4. 后端路由变更

### 4.1 权限调整

| 路由 | 旧 | 新 |
|---|---|---|
| `POST /api/positions` | `manager` | `hr, manager` |
| `PUT /api/positions/{id}` | `manager` | `hr, manager` |
| `POST /api/users` | `manager` | `admin` |
| `PUT /api/users/{id}` (新增) | — | `admin` |
| `DELETE /api/users/{id}` | `manager` | `admin` |
| `POST /api/users/{id}/reset-password` (新增) | — | `admin` |
| `GET /api/users` | 登录即可 | 登录即可(不变) |

### 4.2 登录响应

`POST /api/auth/login` 和 `POST /api/auth/refresh` 响应中 `user` 对象包含 `must_change_password` 字段。

### 4.3 强制改密拦截

新增依赖 `require_password_current(user)`:
- 若 `user.must_change_password == true`,除 `POST /api/auth/change-password` 外所有受保护路由返回 `HTTP 428 Precondition Required`,响应体 `{"detail": "Password change required", "code": "MUST_CHANGE_PASSWORD"}`
- 自助改密成功后 `must_change_password` 置 false

实现方式:在 `get_current_user` 之后加一层 `get_current_active_user`,除改密接口外所有路由用新依赖。

### 4.4 重置密码接口

```
POST /api/users/{user_id}/reset-password
Body: { "new_password": "..." }   # 走复杂度校验
Auth: admin
副作用: user.password_hash 更新,must_change_password = true
```

不允许 admin 重置自己 —— 自己用改密接口即可。

### 4.5 删除保护

- 不允许删除自己(已存在)
- 不允许删除最后一个 admin(新增)

## 5. 前端变更

### 5.1 路由与菜单 (`AppLayout.tsx`)

```
admin   -> 只显示: 用户管理
hr      -> 职位管理、简历上传、候选人管理
manager -> 职位管理、候选人管理          (移除"用户管理"菜单)
```

若用户访问无权限的路由(直接输 URL),前端路由守卫重定向到默认首页。

### 5.2 PositionsPage

- "新建职位"、"编辑"按钮显示条件放宽为 `role === 'hr' || role === 'manager'`

### 5.3 UsersPage

- 角色下拉选项增加 `admin`(标签色:红色,区别于 manager 紫色、hr 蓝色)
- 每行增加"重置密码"按钮 —— 弹窗输入新密码(带复杂度提示),提交后提示"已重置,请把临时密码告知用户,其下次登录需自行修改"
- 新增"编辑"按钮,改 display_name 和 role
- 最后一个 admin 的删除按钮禁用

### 5.4 ForceChangePasswordPage(新增)

- 极简表单:旧密码 + 新密码 + 确认新密码
- 提交成功后刷新 user store,跳回首页默认路由
- 全局路由守卫:登录态下 `user.must_change_password === true` 且当前路径不是 `/force-change-password`,一律重定向到该页
- 此页不显示主导航,降低误操作

### 5.5 authStore

- `user` 类型增加 `must_change_password: boolean`
- 登录、刷新后写入
- `/auth/change-password` 成功后把字段置 false(或重新请求 `/auth/me`)

## 6. 迁移与种子

### 6.1 迁移脚本 `scripts/migrate_add_admin.py`

幂等脚本,可重复执行:

1. 检测 `users` 表是否已有 `must_change_password` 列,没有则 `ALTER TABLE` 加上,默认 0
2. 检测是否存在角色为 `admin` 的账号,没有则插入:
   - username: `admin`
   - password: `Admin@2026`(bcrypt hash)
   - role: `admin`
   - display_name: `系统管理员`
   - must_change_password: `1`
3. 打印当前 admin 账号列表,提示首次密码

### 6.2 `backend/seed.py`

在已有种子数据中追加 admin 账号,保持本地与生产一致。

## 7. 测试策略

后端新增/修改的测试用例:
- admin 可 CRUD 账号、重置密码,manager/hr 返回 403
- admin 不能删自己、不能删最后一个 admin
- hr 可以 POST/PUT 职位
- 必须改密状态下,业务接口返回 428,改密接口放行
- 改密后 must_change_password 置 false

前端:若已有 Playwright/Vitest 测试补 admin 登录流程、强制改密流程,未有则至少人工走一遍 checklist(见 §9)。

## 8. VPS 部署步骤

目标:腾讯云 124.222.82.73:9527,Docker Compose。

```bash
ssh root@124.222.82.73
cd /path/to/smartHR
git pull
docker-compose exec backend python scripts/migrate_add_admin.py   # 迁移
docker-compose build backend frontend
docker-compose up -d
```

验收:
- 浏览器访问登录页,用 `admin / Admin@2026` 登录 → 应被强制跳到改密页
- admin 改密后只看到"用户管理"菜单
- 用现有 hr 账号登录 → 能看到"职位管理"的"新建职位"按钮
- 用现有 manager 账号登录 → "用户管理"菜单消失

回滚:
- 代码回滚 `git checkout <old-sha> && docker-compose build && up -d`
- 数据层面 `must_change_password` 列可以保留,不影响旧代码

## 9. 人工验收 Checklist

- [ ] admin 首次登录强制改密
- [ ] admin 只看到用户管理
- [ ] admin 能创建 hr/manager/admin 三种账号
- [ ] admin 能重置任意非自身账号密码
- [ ] admin 不能删自己,不能删最后一个 admin
- [ ] hr 能创建任意部门的职位
- [ ] hr 能编辑任意部门的职位
- [ ] manager 仍然能建/改职位,看不到用户管理
- [ ] 被 admin 重置密码的用户下次登录被强制改密
- [ ] 改完密码后菜单按新角色正常显示

## 10. 非范围

以下**不在**本次范围内,如需要另立设计:
- 邮件/短信重置密码
- 操作审计日志(admin 做了什么)
- 角色细粒度权限(按部门隔离候选人)
- 多 admin 的权限分级
- SSO/OAuth 登录
