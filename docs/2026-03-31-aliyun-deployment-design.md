# SmartHR 阿里云部署方案设计

> 方案：单台 ECS + Docker Compose，高性价比，面向内部小团队使用

## 1. ECS 选型

| 项目 | 选择 | 理由 |
|------|------|------|
| 规格 | 2C4G（ecs.e-c1m2.large） | FastAPI + PostgreSQL + Nginx 足够 |
| 地域 | cn-shanghai（华东二） | 团队在上海 |
| 系统盘 | 40G ESSD Entry | 系统 + Docker 镜像 |
| 数据盘 | 50G 高效云盘，挂载到 /data | 简历 PDF + 数据库，独立便于备份 |
| 镜像 | Ubuntu 22.04 LTS | Docker 生态成熟 |
| 带宽 | 按量付费 5Mbps | 内部使用足够，80 份 PDF 约 1 分钟传完 |
| 购买方式 | 包年（新用户首年优惠 99-200 元） | |

**预估月成本：~100-150 元**（ECS 包年分摊 + 带宽按量）

## 2. 域名与备案（并行）

部署分两阶段并行推进：

- **立即上线**：公网 IP + 安全组白名单 + 自签 HTTPS
- **同步进行**：注册 .cn 域名（29 元/首年），提交个人 ICP 备案（3-20 个工作日）

备案通过后切换到域名 + Let's Encrypt 正式 HTTPS 证书。

### 备案流程

1. 阿里云备案系统提交材料（身份证、手机号、域名证书）— 30 分钟
2. 阿里云初审 — 1 个工作日
3. 提交管局 — 自动
4. 工信部短信核验 — 当天
5. 管局审核 — 1-20 个工作日（多数 3-5 天）

## 3. 服务架构

一台 ECS 上通过 Docker Compose 运行 3 个容器：

```
┌─────────────────── ECS 2C4G ───────────────────┐
│                                                  │
│  ┌──────────┐    ┌──────────────┐               │
│  │  Nginx   │───>│  FastAPI     │               │
│  │ :443/:80 │    │  Gunicorn    │               │
│  │          │    │  :8000       │               │
│  │ 前端静态  │    └──────┬───────┘               │
│  │ SSL 终止 │           │                        │
│  └──────────┘    ┌──────▼───────┐               │
│                  │ PostgreSQL   │               │
│                  │ :5432        │               │
│                  └──────────────┘               │
│                                                  │
│  数据盘 /data                                     │
│  ├── postgres/    (数据库文件)                     │
│  ├── uploads/     (简历 PDF)                      │
│  └── backups/     (每日自动备份)                   │
└──────────────────────────────────────────────────┘
         │
         ▼ 外部 API
   MinerU + DeepSeek
```

### 容器清单

| 容器 | 镜像 | 作用 |
|------|------|------|
| nginx | nginx:alpine | 反代 API、托管前端静态文件、自签 HTTPS |
| api | python:3.12-slim + 项目代码 | FastAPI + Gunicorn（2 workers） |
| db | postgres:16-alpine | 数据库，数据持久化到数据盘 |

### 数据持久化

所有数据写入 `/data`（单独挂载的数据盘）：

- `postgres/` — 数据库文件，volume 映射
- `uploads/` — 简历 PDF 原文件
- `backups/` — 每日 pg_dump 自动备份，保留 7 天轮转

## 4. 安全方案

### 4.1 网络层 — 阿里云安全组

| 方向 | 端口 | 来源 | 用途 |
|------|------|------|------|
| 入 | 443 | 团队 IP 白名单 | HTTPS 访问 |
| 入 | 80 | 团队 IP 白名单 | 自动跳转到 443 |
| 入 | 22 | 仅管理员 IP | SSH 运维 |
| 入 | 其他 | 全部拒绝 | |

安全组 IP 白名单是最强防线 — 不在名单里的 IP 连 TCP 握手都完成不了。

### 4.2 传输层 — HTTPS

- 阶段一：Nginx 自签证书（浏览器提示不安全，点继续即可）
- 阶段二（备案后）：Let's Encrypt 正式证书，certbot 自动续签

### 4.3 应用层 — 代码调整

| 项 | 调整内容 |
|------|-----------|
| SECRET_KEY | 换成 64 字符强随机值 |
| CORS | 从硬编码 localhost 改为 .env 环境变量 ALLOWED_ORIGINS |
| API 文档 | 生产环境关闭 /docs 和 /redoc |
| 默认密码 | 统一初始密码 Smart2026!，首次登录后各自修改 |

### 4.4 运维安全

- SSH 密钥登录，禁用密码登录
- Docker 内部网络隔离，PostgreSQL 不暴露到公网（仅容器间通信）
- 数据库密码通过 .env 注入，不进代码仓库
- .env 文件权限设为 600

## 5. 预置用户（空库起步）

不迁移现有开发数据，生产环境从空库开始，预置 10 个账户：

| 用户名 | 角色 | 部门 | 初始密码 |
|--------|------|------|----------|
| hr | hr | 人事 | Smart2026! |
| mgr_delivery | manager | 交付 | Smart2026! |
| mgr_rd | manager | 产研 | Smart2026! |
| mgr_marketing | manager | 市场 | Smart2026! |
| mgr_ops1 | manager | 运营1 | Smart2026! |
| mgr_ops2 | manager | 运营2 | Smart2026! |
| mgr_sales1 | manager | 销售1 | Smart2026! |
| mgr_sales2 | manager | 销售2 | Smart2026! |
| mgr_finance | manager | 财务 | Smart2026! |
| mgr_hr | manager | 人事 | Smart2026! |

## 6. 需要编写的文件

### 6.1 Docker 相关

| 文件 | 内容 |
|------|------|
| `Dockerfile` | 后端 Python 镜像（基于 python:3.12-slim） |
| `docker-compose.yml` | 编排 nginx + api + db 三个服务 |
| `nginx/default.conf` | Nginx 配置（反代 + 静态文件 + HTTPS） |
| `nginx/generate-cert.sh` | 自签证书生成脚本 |
| `.env.production` | 生产环境变量模板 |

### 6.2 代码调整

| 文件 | 改动 |
|------|------|
| `backend/app/config.py` | 新增 ALLOWED_ORIGINS、DATABASE_URL 配置项 |
| `backend/app/main.py` | CORS 从硬编码改为读 ALLOWED_ORIGINS；生产环境关闭 /docs |
| `backend/app/database.py` | 支持 PostgreSQL 连接字符串（DATABASE_URL） |
| `frontend/vite.config.ts` | 不影响（构建产物由 Nginx 直接托管） |

### 6.3 运维脚本

| 文件 | 内容 |
|------|------|
| `scripts/backup.sh` | 每日 pg_dump + 7 天轮转 |
| `scripts/deploy.sh` | 首次部署一键脚本（安装 Docker、拉代码、启动） |
| `scripts/update.sh` | 代码更新脚本（git pull + rebuild + restart） |

## 7. 部署流程

### 7.1 首次部署（约 1-2 小时）

```
1. 购买 ECS（cn-shanghai, 2C4G）+ 挂载 50G 数据盘
2. 安全组配置（白名单 IP + 端口规则）
3. SSH 密钥登录，安装 Docker + Docker Compose
4. git clone 项目代码
5. 配置 .env（数据库密码、API Keys、SECRET_KEY）
6. docker compose up -d  ← 一键拉起全部服务
7. 初始化数据库 + seed 默认用户
8. 修改默认密码，验证所有功能
```

### 7.2 日常运维

| 操作 | 命令 |
|------|------|
| 查看状态 | `docker compose ps` |
| 查看日志 | `docker compose logs -f api` |
| 更新代码 | `git pull && docker compose up -d --build api` |
| 手动备份 | `docker compose exec db pg_dump -U smarthr smarthr > backup.sql` |
| 恢复备份 | `cat backup.sql \| docker compose exec -T db psql -U smarthr smarthr` |

### 7.3 域名切换（备案通过后）

```
1. DNS 解析 A 记录 → ECS 公网 IP
2. 安装 certbot，获取 Let's Encrypt 证书
3. 更新 nginx/default.conf 证书路径
4. 更新 .env ALLOWED_ORIGINS 为正式域名
5. docker compose restart nginx api
```

## 8. 成本汇总

| 项目 | 费用 |
|------|------|
| ECS 2C4G 包年 | ~99-200 元/年（新用户优惠） |
| 数据盘 50G | ~15 元/月 |
| 带宽按量 5Mbps | ~10-30 元/月（内部使用量小） |
| .cn 域名 | 29 元/首年 |
| SSL 证书 | 免费（自签 / Let's Encrypt） |
| **月均合计** | **~100-150 元** |
