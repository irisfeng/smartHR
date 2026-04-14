# SmartHR 阿里云部署 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Docker 化 SmartHR 并准备阿里云 ECS 一键部署能力

**Architecture:** 单台 ECS 运行 Docker Compose（Nginx + FastAPI/Gunicorn + PostgreSQL），数据持久化到独立数据盘 /data，安全组 IP 白名单 + 自签 HTTPS

**Tech Stack:** Docker, Docker Compose, PostgreSQL 16, Nginx, Gunicorn, Let's Encrypt, aliyun-cli

**Design Doc:** `docs/2026-03-31-aliyun-deployment-design.md`

---

## File Structure

### New Files
- `backend/Dockerfile` — Python 后端镜像
- `docker-compose.yml` — 编排 3 个服务（nginx, api, db）
- `nginx/default.conf` — Nginx 反代 + 静态文件 + HTTPS
- `nginx/generate-cert.sh` — 自签证书生成脚本
- `.env.production` — 生产环境变量模板
- `scripts/backup.sh` — 每日数据库备份 + 7 天轮转
- `scripts/deploy.sh` — ECS 首次部署一键脚本
- `scripts/update.sh` — 代码更新脚本

### Modified Files
- `backend/app/config.py` — 新增 DATABASE_URL, ALLOWED_ORIGINS, ENV
- `backend/app/database.py` — 支持 PostgreSQL 连接
- `backend/app/main.py` — CORS 从环境变量读取，生产环境关闭 /docs
- `backend/seed.py` — 10 个预置用户
- `backend/requirements.txt` — 添加 psycopg2-binary, gunicorn

---

### Task 1: 后端支持 PostgreSQL + 环境变量配置

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/database.py`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: 在 requirements.txt 添加 PostgreSQL 驱动和 Gunicorn**

在 `backend/requirements.txt` 末尾追加：
```
psycopg2-binary==2.9.9
gunicorn==22.0.0
```

- [ ] **Step 2: 修改 config.py，新增 DATABASE_URL、ALLOWED_ORIGINS、ENV**

替换 `backend/app/config.py` 全部内容为：

```python
import logging
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    env: str = "dev"  # "dev" or "prod"

    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    database_url: str = "sqlite:///smarthr.db"

    allowed_origins: str = "http://localhost:5173"

    mineru_api_key: str = ""

    ai_api_url: str = "https://api.deepseek.com/v1"
    ai_api_key: str = ""
    ai_model: str = "deepseek-chat"

    upload_dir: str = "uploads"
    max_upload_size_mb: int = 100

    class Config:
        env_file = ".env"

settings = Settings()

if settings.secret_key == "change-me":
    logger.warning(
        "SECRET_KEY is using the default value 'change-me'. "
        "Set a strong SECRET_KEY in .env for production use."
    )
```

- [ ] **Step 3: 修改 database.py，从 DATABASE_URL 读取连接**

替换 `backend/app/database.py` 全部内容为：

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: 本地验证现有功能不受影响**

Run: `cd backend && python -c "from app.database import engine; print(engine.url)"`
Expected: `sqlite:///smarthr.db`（本地默认仍然使用 SQLite）

Run: `cd backend && python -m pytest tests/ -x -q`
Expected: 全部通过（现有测试不受影响）

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/app/database.py backend/requirements.txt
git commit -m "feat: support PostgreSQL via DATABASE_URL, add ALLOWED_ORIGINS and ENV config"
```

---

### Task 2: CORS 环境变量化 + 生产环境关闭 /docs

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: 修改 main.py**

替换 `backend/app/main.py` 全部内容为：

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.routers import auth_router, positions_router, upload_router, candidates_router, export_router, users_router

Base.metadata.create_all(bind=engine)

docs_url = "/docs" if settings.env != "prod" else None
redoc_url = "/redoc" if settings.env != "prod" else None

app = FastAPI(title="SmartHR API", docs_url=docs_url, redoc_url=redoc_url)

origins = [o.strip() for o in settings.allowed_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(positions_router.router)
app.include_router(upload_router.router)
app.include_router(candidates_router.router)
app.include_router(export_router.router)
app.include_router(users_router.router)

@app.get("/api/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 2: 本地验证**

Run: `cd backend && python -m pytest tests/ -x -q`
Expected: 全部通过

Run: `cd backend && python -c "from app.main import app; print([r.path for r in app.routes if 'docs' in r.path])"`
Expected: 包含 `/docs`（dev 模式下 docs 可用）

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: CORS from env var, disable /docs in production"
```

---

### Task 3: 更新 seed.py — 10 个预置用户

**Files:**
- Modify: `backend/seed.py`

- [ ] **Step 1: 替换 seed.py 全部内容**

```python
from app.database import engine, SessionLocal, Base
from app.models import User
from app.auth import hash_password

Base.metadata.create_all(bind=engine)
db = SessionLocal()

USERS = [
    ("hr",            "hr",      "人事",  "HR专员"),
    ("mgr_delivery",  "manager", "交付",  "交付经理"),
    ("mgr_rd",        "manager", "产研",  "产研经理"),
    ("mgr_marketing", "manager", "市场",  "市场经理"),
    ("mgr_ops1",      "manager", "运营1", "运营经理1"),
    ("mgr_ops2",      "manager", "运营2", "运营经理2"),
    ("mgr_sales1",    "manager", "销售1", "销售经理1"),
    ("mgr_sales2",    "manager", "销售2", "销售经理2"),
    ("mgr_finance",   "manager", "财务",  "财务经理"),
    ("mgr_hr",        "manager", "人事",  "人事经理"),
]

DEFAULT_PASSWORD = "Smart2026!"

created = 0
for username, role, _dept, display_name in USERS:
    if not db.query(User).filter(User.username == username).first():
        db.add(User(
            username=username,
            password_hash=hash_password(DEFAULT_PASSWORD),
            role=role,
            display_name=display_name,
        ))
        created += 1

db.commit()
print(f"Seeded {created} new users ({len(USERS)} total defined)")
db.close()
```

- [ ] **Step 2: Commit**

```bash
git add backend/seed.py
git commit -m "feat: production seed with 10 preset users (1 HR + 9 managers)"
```

---

### Task 4: 后端 Dockerfile

**Files:**
- Create: `backend/Dockerfile`

- [ ] **Step 1: 创建 backend/Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "2", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "900"]
```

注意：`--timeout 900` 是因为 MinerU 批量解析轮询可达 10 分钟。

- [ ] **Step 2: 创建 backend/.dockerignore**

```
__pycache__
*.pyc
.venv
.env
smarthr.db
uploads/
tests/
.pytest_cache
```

- [ ] **Step 3: Commit**

```bash
git add backend/Dockerfile backend/.dockerignore
git commit -m "feat: add backend Dockerfile with Gunicorn"
```

---

### Task 5: Nginx 配置 + 自签证书脚本

**Files:**
- Create: `nginx/default.conf`
- Create: `nginx/generate-cert.sh`

- [ ] **Step 1: 创建 nginx/default.conf**

```nginx
server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name _;

    ssl_certificate     /etc/nginx/certs/selfsigned.crt;
    ssl_certificate_key /etc/nginx/certs/selfsigned.key;

    client_max_body_size 120M;

    # 前端静态文件
    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 反代
    location /api/ {
        proxy_pass http://api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 900s;
    }
}
```

- [ ] **Step 2: 创建 nginx/generate-cert.sh**

```bash
#!/bin/bash
set -e
CERT_DIR="/etc/nginx/certs"
mkdir -p "$CERT_DIR"
if [ ! -f "$CERT_DIR/selfsigned.crt" ]; then
    openssl req -x509 -nodes -days 365 \
        -newkey rsa:2048 \
        -keyout "$CERT_DIR/selfsigned.key" \
        -out "$CERT_DIR/selfsigned.crt" \
        -subj "/CN=smarthr/O=SmartHR/C=CN"
    echo "Self-signed certificate generated."
else
    echo "Certificate already exists, skipping."
fi
```

- [ ] **Step 3: Commit**

```bash
git add nginx/
git commit -m "feat: add Nginx config with self-signed HTTPS and API proxy"
```

---

### Task 6: docker-compose.yml

**Files:**
- Create: `docker-compose.yml`

- [ ] **Step 1: 创建 docker-compose.yml（项目根目录）**

```yaml
services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-smarthr}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD in .env}
      POSTGRES_DB: ${POSTGRES_DB:-smarthr}
    volumes:
      - ${DATA_DIR:-./data}/postgres:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U smarthr"]
      interval: 5s
      retries: 5

  api:
    build: ./backend
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER:-smarthr}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB:-smarthr}
      SECRET_KEY: ${SECRET_KEY:?Set SECRET_KEY in .env}
      ENV: ${ENV:-prod}
      ALLOWED_ORIGINS: ${ALLOWED_ORIGINS:-https://localhost}
      MINERU_API_KEY: ${MINERU_API_KEY:-}
      AI_API_URL: ${AI_API_URL:-https://api.deepseek.com/v1}
      AI_API_KEY: ${AI_API_KEY:-}
      AI_MODEL: ${AI_MODEL:-deepseek-chat}
      UPLOAD_DIR: /data/uploads
    volumes:
      - ${DATA_DIR:-./data}/uploads:/data/uploads

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    depends_on:
      - api
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
      - ./nginx/generate-cert.sh:/generate-cert.sh:ro
      - ./frontend/dist:/usr/share/nginx/html:ro
      - nginx-certs:/etc/nginx/certs
    entrypoint: /bin/sh -c "apk add --no-cache openssl && sh /generate-cert.sh && nginx -g 'daemon off;'"

volumes:
  nginx-certs:
```

- [ ] **Step 2: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: add docker-compose with nginx, api, and postgres services"
```

---

### Task 7: 生产环境变量模板

**Files:**
- Create: `.env.production`

- [ ] **Step 1: 创建 .env.production**

```env
# === SmartHR 生产环境配置 ===
# 复制为 .env 后填入实际值

# 环境标识
ENV=prod

# JWT 密钥（部署脚本会自动生成）
SECRET_KEY=change-me

# 数据库（Docker Compose 自动拼接，这里只需设密码）
POSTGRES_USER=smarthr
POSTGRES_PASSWORD=CHANGE_THIS_TO_STRONG_PASSWORD
POSTGRES_DB=smarthr

# 数据目录（ECS 数据盘挂载点）
DATA_DIR=/data

# CORS 允许的源（阶段一用 IP，备案后换域名）
ALLOWED_ORIGINS=https://YOUR_ECS_PUBLIC_IP

# MinerU PDF 解析
MINERU_API_KEY=your-mineru-key

# DeepSeek AI 筛选
AI_API_URL=https://api.deepseek.com/v1
AI_API_KEY=your-deepseek-key
AI_MODEL=deepseek-chat
```

- [ ] **Step 2: 确保 .gitignore 包含 .env 但不包含 .env.production**

检查项目根目录 `.gitignore`，确保有 `.env` 但没有 `.env.production`。如果没有 `.gitignore`，创建一个：

```
.env
backend/.env
backend/smarthr.db
backend/uploads/
backend/__pycache__/
backend/.venv/
data/
```

- [ ] **Step 3: Commit**

```bash
git add .env.production .gitignore
git commit -m "feat: add production env template and gitignore"
```

---

### Task 8: 运维脚本

**Files:**
- Create: `scripts/backup.sh`
- Create: `scripts/deploy.sh`
- Create: `scripts/update.sh`

- [ ] **Step 1: 创建 scripts/backup.sh**

```bash
#!/bin/bash
# 每日数据库备份，保留 7 天
set -e

BACKUP_DIR="${DATA_DIR:-/data}/backups"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/smarthr_${TIMESTAMP}.sql.gz"

docker compose exec -T db pg_dump -U smarthr smarthr | gzip > "$BACKUP_FILE"
echo "Backup saved: $BACKUP_FILE"

# 删除 7 天前的备份
find "$BACKUP_DIR" -name "smarthr_*.sql.gz" -mtime +7 -delete
echo "Old backups cleaned."
```

- [ ] **Step 2: 创建 scripts/deploy.sh**

```bash
#!/bin/bash
# SmartHR ECS 首次部署脚本
set -e

echo "=== SmartHR 首次部署 ==="

# 1. 安装 Docker
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker && systemctl start docker
    echo "Docker installed."
fi

# 2. 格式化并挂载数据盘（假设 /dev/vdb）
if ! mountpoint -q /data; then
    echo "Mounting data disk..."
    mkfs.ext4 -F /dev/vdb
    mkdir -p /data
    mount /dev/vdb /data
    echo "/dev/vdb /data ext4 defaults 0 2" >> /etc/fstab
    echo "Data disk mounted at /data"
fi
mkdir -p /data/{postgres,uploads,backups}

# 3. 配置环境变量
cd /opt/smarthr
if [ ! -f .env ]; then
    cp .env.production .env
    # 自动生成 SECRET_KEY
    SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
    sed -i "s|SECRET_KEY=change-me|SECRET_KEY=${SECRET}|" .env
    echo ""
    echo "⚠️  请编辑 .env 填入以下配置："
    echo "   - POSTGRES_PASSWORD（数据库密码）"
    echo "   - ALLOWED_ORIGINS（你的 ECS 公网 IP）"
    echo "   - MINERU_API_KEY"
    echo "   - AI_API_KEY"
    echo ""
    echo "   nano /opt/smarthr/.env"
    echo ""
    echo "编辑完成后重新运行此脚本。"
    exit 0
fi

# 4. 构建前端
echo "Building frontend..."
cd frontend
if command -v node &> /dev/null; then
    npm install && npm run build
else
    echo "Node.js not found, installing..."
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
    apt-get install -y nodejs
    npm install && npm run build
fi
cd ..

# 5. 启动服务
echo "Starting services..."
docker compose up -d --build

# 6. 等待数据库就绪，初始化用户
echo "Waiting for database..."
sleep 5
docker compose exec api python seed.py

echo ""
echo "=== 部署完成 ==="
echo "访问地址: https://$(curl -s ifconfig.me)"
echo ""
echo "默认账户密码: Smart2026!（请尽快修改）"
echo "  HR: hr"
echo "  经理: mgr_delivery, mgr_rd, mgr_marketing, mgr_ops1, mgr_ops2,"
echo "        mgr_sales1, mgr_sales2, mgr_finance, mgr_hr"
```

- [ ] **Step 3: 创建 scripts/update.sh**

```bash
#!/bin/bash
# 代码更新脚本
set -e

cd /opt/smarthr

echo "=== SmartHR 更新 ==="

# 1. 备份数据库
echo "Backing up database..."
bash scripts/backup.sh

# 2. 拉取最新代码
echo "Pulling latest code..."
git pull

# 3. 重新构建前端
echo "Building frontend..."
cd frontend && npm install && npm run build && cd ..

# 4. 重建并重启 api 容器
echo "Rebuilding api container..."
docker compose up -d --build api

# 5. 运行数据库迁移（如有新用户）
docker compose exec api python seed.py

echo "=== 更新完成 ==="
```

- [ ] **Step 4: 设置脚本可执行 + Commit**

```bash
chmod +x scripts/backup.sh scripts/deploy.sh scripts/update.sh
git add scripts/
git commit -m "feat: add deploy, update, and backup scripts"
```

---

### Task 9: 构建前端并本地 Docker 验证

- [ ] **Step 1: 构建前端静态文件**

Run: `cd frontend && npm run build`
Expected: `dist/` 目录生成，包含 `index.html` 和 `assets/`

- [ ] **Step 2: 本地 Docker Compose 冒烟测试**

创建临时 `.env` 用于本地测试：

```bash
cat > .env << 'EOF'
ENV=dev
SECRET_KEY=test-secret-key-for-local-docker
POSTGRES_USER=smarthr
POSTGRES_PASSWORD=localtest123
POSTGRES_DB=smarthr
ALLOWED_ORIGINS=https://localhost
MINERU_API_KEY=
AI_API_URL=https://api.deepseek.com/v1
AI_API_KEY=
AI_MODEL=deepseek-chat
EOF
```

Run: `docker compose up -d --build`
Expected: 3 个容器全部 healthy/running

Run: `docker compose ps`
Expected:
```
NAME       SERVICE   STATUS
smarthr-db-1      db       running (healthy)
smarthr-api-1     api      running
smarthr-nginx-1   nginx    running
```

- [ ] **Step 3: 验证 API 和前端**

Run: `curl -k https://localhost/api/health`
Expected: `{"status":"ok"}`

Run: `curl -k -o /dev/null -s -w "%{http_code}" https://localhost/`
Expected: `200`

- [ ] **Step 4: 初始化用户并测试登录**

Run: `docker compose exec api python seed.py`
Expected: `Seeded 10 new users (10 total defined)`

Run: `curl -k -s https://localhost/api/auth/login -H 'Content-Type: application/json' -d '{"username":"hr","password":"Smart2026!"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK' if 'access_token' in d else 'FAIL')"`
Expected: `OK`

- [ ] **Step 5: 清理本地测试环境**

```bash
docker compose down -v
rm .env
```

- [ ] **Step 6: Commit 前端构建产物（如果需要）或添加到 .gitignore**

前端 `dist/` 在服务器上构建，不需要提交。确认 `.gitignore` 包含 `frontend/dist/`。

```bash
git add -A
git commit -m "chore: finalize Docker deployment setup"
```

---

### Task 10: 设置 cron 自动备份

此任务在 ECS 部署完成后执行。

- [ ] **Step 1: 在 ECS 上配置 crontab**

```bash
crontab -e
```

添加：
```
0 3 * * * cd /opt/smarthr && bash scripts/backup.sh >> /data/backups/cron.log 2>&1
```

- [ ] **Step 2: 验证 cron**

Run: `crontab -l | grep backup`
Expected: 显示上面添加的行
