# SmartHR 开发日志

## 2026-03-29 项目启动

- 完成需求分析和 MVP 设计规范
- 确定技术栈：FastAPI + React + SQLite + MinerU + DeepSeek
- 定义双角色模型（HR / 用人经理）
- 设计数据模型（Users, JobPositions, Candidates, UploadBatches）
- 定义 15 个 API 端点
- 产出 UI 设计稿（indigo #6366f1 主题，白色侧边栏）

## 2026-03-30 后端开发

- **项目脚手架** — FastAPI 应用结构、SQLAlchemy 模型、Pydantic schemas、配置系统
- **认证系统** — JWT 登录/刷新、bcrypt 密码哈希、角色权限（require_role 依赖注入）
- **职位 CRUD** — 创建/编辑（经理专属）、列表、详情（含候选人统计）
- **上传管道** — ZIP/PDF 上传、ZIP 解压、文件校验、后台异步处理
- **候选人管理** — 列表（筛选/排序）、详情、部分更新、简历 PDF 服务
- **AI 服务** — MinerU PDF 解析（graceful fallback）、DeepSeek 简历筛选（结构化 JSON 输出）
- **Excel 导出** — openpyxl 生成，匹配公司模板格式
- **用户管理** — 列表、创建、删除（防自删）
- **种子数据** — admin（经理）和 hr 两个测试用户

## 2026-03-30 前端开发

- **项目脚手架** — React 19 + Vite + TypeScript + Ant Design 6 + Zustand
- **路由系统** — 登录页、职位管理、简历上传、候选人列表、用户管理
- **API 层** — Axios 实例，JWT 自动附加 + 401 刷新拦截器
- **认证** — 登录页、ProtectedRoute 守卫、Zustand 用户状态
- **布局** — 白色侧边栏 + 顶栏用户信息
- **5 个完整页面** — 全部对接后端 API，非 stub

## 2026-03-30 代码审查与修复（Superpowers）

使用 superpowers 插件进行全量代码审查，发现并修复：

### 前端修复（9 Critical + 12 Important）
- Token 刷新竞态条件 → 添加 mutex Promise
- TypeScript 类型错误（`_retry` 属性、`React.ReactNode` 未导入）
- React hook 依赖问题 → 将 fetch 逻辑移入 useEffect
- 简历 PDF `window.open()` 无认证 → 改用 axios blob 下载
- 所有 API 调用站点添加 try/catch 错误处理
- `ai_screening_result` 类型安全（移除 `as any`）
- 添加 React Error Boundary
- 职位编辑支持状态切换（招聘中/已关闭）
- 密码最低长度从 4 提升至 6

### 后端修复（安全加固）
- 路径遍历防护 — `validate_resume_path()` 校验文件路径在 uploads 目录内
- ZIP 提取加固 — 防 zip slip（basename 检查）、防 zip bomb（50MB 单文件限制、200 文件上限）
- 输入校验 — UserCreate 添加字段约束（username 2-32, password 6-128, role 正则）
- 排序列白名单 — `sort_by` 参数仅允许安全列名

## 2026-03-30 MinerU API 适配

- 发现原始 `mineru_service.py` 与 MinerU v4 API 不匹配
- 重写为正确的 v4 精准解析流程：
  1. `POST /api/v4/file-urls/batch` → 获取签名上传 URL
  2. `PUT` 文件到 OSS
  3. 轮询 `GET /api/v4/extract-results/batch/{id}` 等待完成
  4. 下载结果 zip → 提取 `full.md`
- 移除 `MINERU_API_URL` 配置（base URL 固定为 mineru.net）

## 2026-03-30 工程化

- 添加 `start.sh` 一键启动脚本（自动生成 SECRET_KEY、安装依赖、初始化数据库、启动服务）
- 更新 `.env.example`
- 编写 README
- 推送至 GitHub: https://github.com/irisfeng/smartHR

## 待办

- [ ] 浏览器端到端实测
- [ ] 后端 API 单元测试
- [ ] 部署方案（Docker / 云服务）
