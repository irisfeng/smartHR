# SmartHR 腾讯云部署与运维手册

## 1. 服务器信息

| 项目 | 值 |
|------|------|
| 云平台 | 腾讯云轻量应用服务器 (Lighthouse) |
| 实例ID | lhins-3c13y9c6 |
| 地域 | 上海二区 (ap-shanghai) |
| 系统 | Ubuntu Server 22.04 LTS 64bit |
| 配置 | 2核 CPU / 4GB 内存 / 60GB SSD |
| 带宽 | 5Mbps，500GB/月流量包 |
| 公网IP | 124.222.82.73 |
| 内网IP | 10.0.0.12 |
| 服务端口 | 9527 (HTTP) |
| 到期时间 | 2027-04-01 |
| 项目路径 | /opt/smarthr |
| 数据目录 | /data/postgres, /data/uploads, /data/backups |

### 控制台入口

- 实例管理: https://console.cloud.tencent.com/lighthouse/instance/detail?rid=4&id=lhins-3c13y9c6
- OrcaTerm 终端: 实例详情页 → 登录（免密连接 TAT）
- 防火墙: 实例详情页 → 防火墙 tab

### Mac SSH 快速登录

当前本机 Mac 已把 SSH 公钥加入 VPS 的 `ubuntu` 用户，并在 `~/.ssh/config` 配置了别名:

```bash
ssh tencent-smarthr
```

等价直连命令:

```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@124.222.82.73
```

如果换一台 Mac，需要先把新机器的公钥追加到 VPS:

```bash
# 本机生成/查看公钥
cat ~/.ssh/id_ed25519.pub

# 通过腾讯云 OrcaTerm 登录 VPS 后，在 ubuntu 用户下执行
mkdir -p ~/.ssh
chmod 700 ~/.ssh
touch ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
# 将新 Mac 的公钥追加到 ~/.ssh/authorized_keys
```

---

## 2. 架构概览

```
用户浏览器
    │
    ▼ (HTTP:9527)
┌─────────────────────────────────────────┐
│            腾讯云轻量 VPS               │
│                                         │
│  ┌─────────┐  ┌─────────┐  ┌────────┐  │
│  │  nginx   │→│   api   │→│   db   │  │
│  │ (alpine) │  │(Python  │  │(PG 16) │  │
│  │ port 80  │  │ 3.12)   │  │        │  │
│  └─────────┘  └─────────┘  └────────┘  │
│    :9527→:80    :8000        :5432      │
│                                         │
│  /data/postgres  (数据库持久化)          │
│  /data/uploads   (简历PDF文件)          │
│  /data/backups   (数据库备份)           │
└─────────────────────────────────────────┘
```

Docker Compose 管理三个服务:
- **nginx:alpine** — 反向代理 + 前端静态文件托管
- **api** (自建镜像) — FastAPI + Gunicorn，2 workers，900s 超时
- **postgres:16-alpine** — 数据库，带 healthcheck

---

## 3. 首次部署步骤

### 3.1 服务器基础环境

```bash
# SSH 登录（或通过 OrcaTerm 免密登录）
ssh root@124.222.82.73

# 安装 Docker、Git
apt update && apt install -y docker.io docker-compose-v2 git

# 启用 Docker 开机自启
systemctl enable docker && systemctl start docker

# 配置 Docker 镜像加速（腾讯云内网源）
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": ["https://mirror.ccs.tencentyun.com"]
}
EOF
systemctl restart docker

# 安装 Node.js 22（用于构建前端）
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt install -y nodejs
```

### 3.2 克隆代码

```bash
git clone https://github.com/irisfeng/smartHR.git /opt/smarthr
cd /opt/smarthr
```

### 3.3 创建数据目录

```bash
mkdir -p /data/postgres /data/uploads /data/backups
```

### 3.4 配置环境变量

```bash
cp .env.production .env

# 自动生成 SECRET_KEY 和 POSTGRES_PASSWORD
python3 -c "
import secrets
sk = secrets.token_urlsafe(48)
pg = secrets.token_urlsafe(24)
print(f'SECRET_KEY={sk}')
print(f'POSTGRES_PASSWORD={pg}')
"

# 编辑 .env 填入上面生成的值，以及 API Key
nano .env
chmod 600 .env
```

`.env` 文件内容模板:
```
ENV=prod
SECRET_KEY=<生成的密钥>
POSTGRES_USER=smarthr
POSTGRES_PASSWORD=<生成的密码>
POSTGRES_DB=smarthr
DATA_DIR=/data
ALLOWED_ORIGINS=http://124.222.82.73:9527
MINERU_API_KEY=<你的MinerU API Key>
AI_API_URL=https://api.deepseek.com/v1
AI_API_KEY=<你的DeepSeek API Key>
AI_MODEL=deepseek-chat
```

### 3.5 构建前端

```bash
cd /opt/smarthr/frontend
npm install
npm run build
cd ..
```

### 3.6 启动服务

```bash
docker compose up -d --build
```

### 3.7 初始化用户数据

```bash
docker compose exec api python seed.py
```

### 3.8 配置防火墙

腾讯云控制台 → 防火墙 → 添加规则:
- TCP 端口 9527，允许所有 IPv4，备注 SmartHR

---

## 4. 日常更新部署

```bash
cd /opt/smarthr

# 拉取最新代码
git pull origin main

# 重新构建前端
cd frontend && npm run build && cd ..

# 重新构建并重启服务（仅变更的容器会重建）
docker compose up -d --build
```

如果只改了后端代码（不涉及前端），可跳过 npm build:
```bash
git pull origin main && docker compose up -d --build
```

---

## 5. 运维命令速查

### 5.1 服务管理

```bash
cd /opt/smarthr

# 查看所有容器状态
docker compose ps

# 查看 API 日志（最近 100 行）
docker compose logs api --tail 100

# 查看 API 日志（实时跟踪）
docker compose logs api -f

# 查看 nginx 日志
docker compose logs nginx --tail 50

# 查看数据库日志
docker compose logs db --tail 50

# 重启单个服务
docker compose restart api
docker compose restart nginx

# 停止所有服务
docker compose down

# 停止并删除数据卷（危险！会丢失数据）
docker compose down -v
```

### 5.1.1 开机自启检查

SmartHR 依赖 Docker Compose 容器的 restart 策略自启。当前确认状态:

- `docker.service` 和 `containerd.service` 均为 `enabled`
- `smarthr-db-1`、`smarthr-api-1`、`smarthr-nginx-1` 均为 `restart=unless-stopped`
- 因此正常重启 VPS 后，SmartHR 会随 Docker 自动拉起

检查命令:

```bash
ssh tencent-smarthr

systemctl is-enabled docker
systemctl is-active docker

cd /opt/smarthr
sudo docker compose ps
sudo docker inspect smarthr-db-1 smarthr-api-1 smarthr-nginx-1 \
  --format '{{.Name}} restart={{.HostConfig.RestartPolicy.Name}} status={{.State.Status}}'
```

同机还有一个 `team-wiki` 项目，路径 `/opt/team-wiki`，对外端口 `8080`。当前只是参考服务，尚无人正式使用；它的容器当前 `restart=no`，重启 VPS 后不保证自动拉起。需要手动启动时:

```bash
cd /opt/team-wiki
sudo docker compose up -d
sudo docker compose ps
```

已知小问题: `team-wiki` 的 Postgres healthcheck 默认用用户 `wiki` 连接同名数据库，但实际数据库名是 `teamwiki`，所以日志里会持续出现 `database "wiki" does not exist`。业务连接配置指向 `teamwiki`，页面当前可访问。

### 5.2 数据库操作

```bash
# 进入 PostgreSQL 交互终端
docker compose exec db psql -U smarthr -d smarthr

# 常用 SQL 查询
# 查看所有用户
SELECT id, username, role, display_name FROM users;

# 查看上传批次状态
SELECT id, job_position_id, file_count, processed_count, status FROM upload_batches;

# 查看候选人解析状态
SELECT id, name, status, error_message FROM candidates WHERE upload_batch_id = <batch_id>;

# 查看候选人是否有 parsed_text
SELECT id, name, length(parsed_text) as text_len, status FROM candidates LIMIT 20;

# 清空某个职位的所有候选人（谨慎操作）
DELETE FROM candidates WHERE job_position_id = <position_id>;
DELETE FROM upload_batches WHERE job_position_id = <position_id>;
```

### 5.3 磁盘与资源

```bash
# 查看磁盘使用
df -h

# 查看 Docker 占用空间
docker system df

# 清理未使用的 Docker 镜像（释放空间）
docker image prune -f

# 查看数据目录大小
du -sh /data/*

# 查看上传文件
ls -la /data/uploads/
```

### 5.4 备份与恢复

```bash
# 手动备份数据库
docker compose exec db pg_dump -U smarthr smarthr | gzip > /data/backups/smarthr_$(date +%Y%m%d_%H%M%S).sql.gz

# 恢复数据库（危险操作，会覆盖现有数据）
gunzip < /data/backups/smarthr_20260401.sql.gz | docker compose exec -T db psql -U smarthr -d smarthr

# 设置每日自动备份（3:00 AM）
(crontab -l 2>/dev/null; echo "0 3 * * * cd /opt/smarthr && docker compose exec -T db pg_dump -U smarthr smarthr | gzip > /data/backups/smarthr_\$(date +\%Y\%m\%d).sql.gz && find /data/backups -name '*.gz' -mtime +7 -delete") | crontab -
```

---

## 6. 故障排查指南

### 6.1 网站打不开

```bash
# 1. 检查容器是否运行
docker compose ps

# 2. 如果容器挂了，查看原因
docker compose logs api --tail 50
docker compose logs nginx --tail 50

# 3. 检查端口监听
ss -tlnp | grep 9527

# 4. 检查防火墙规则（腾讯云控制台）
# 确保 9527 TCP 已放行

# 5. 重启所有服务
docker compose down && docker compose up -d
```

### 6.2 上传简历后全是空行

**已知问题（2026-04-02 已修复）：** MinerU 返回的 PDF 解析文本包含 NUL 空字节 (0x00)，PostgreSQL 拒绝存储。

排查步骤:
```bash
# 1. 查看 API 日志，搜索错误
docker compose logs api --tail 200 | grep -i "error\|failed\|NUL"

# 2. 检查候选人解析状态
docker compose exec db psql -U smarthr -d smarthr -c \
  "SELECT id, name, status, error_message, length(parsed_text) FROM candidates ORDER BY id DESC LIMIT 20;"

# 3. 检查上传批次状态
docker compose exec db psql -U smarthr -d smarthr -c \
  "SELECT * FROM upload_batches ORDER BY id DESC LIMIT 5;"

# 4. 检查 .env 中 API Key 是否配置
grep -E 'MINERU_API_KEY|AI_API_KEY' /opt/smarthr/.env
# 确认值非空
```

### 6.3 MinerU PDF 解析失败

```bash
# 检查 API 日志中 MinerU 相关错误
docker compose logs api | grep -i "mineru\|parse"

# 常见原因:
# - MINERU_API_KEY 为空或过期
# - PDF 文件损坏或加密
# - MinerU API 服务暂时不可用（可重试）
# - 解析超时（默认 10 分钟）

# 测试 MinerU API 连通性（从容器内）
docker compose exec api python -c "
import httpx, os
key = os.environ.get('MINERU_API_KEY', '')
print(f'Key length: {len(key)}')
print(f'Key prefix: {key[:20]}...' if key else 'KEY IS EMPTY!')
"
```

### 6.4 DeepSeek AI 筛选失败

```bash
# 检查 API 日志中 AI 相关错误
docker compose logs api | grep -i "ai\|deepseek\|screen"

# 常见原因:
# - AI_API_KEY 为空或余额不足
# - DeepSeek API 限流或服务故障
# - parsed_text 为空（MinerU 解析先失败了）

# 测试 DeepSeek API 连通性
docker compose exec api python -c "
import httpx, os
key = os.environ.get('AI_API_KEY', '')
url = os.environ.get('AI_API_URL', '')
print(f'URL: {url}')
print(f'Key: {key[:10]}...' if key else 'KEY IS EMPTY!')
resp = httpx.get(url.replace('/v1', ''), timeout=5)
print(f'Status: {resp.status_code}')
"
```

### 6.5 Docker 构建缓慢或失败

```bash
# 检查 Docker 镜像加速是否生效
docker info | grep -A5 "Registry Mirrors"
# 应显示: https://mirror.ccs.tencentyun.com

# 如果没有，重新配置
cat /etc/docker/daemon.json
systemctl restart docker

# Dockerfile 内 apt-get 和 pip 已配置腾讯云源
# 如果仍然慢，检查 DNS
nslookup mirrors.cloud.tencent.com
```

### 6.6 数据库连接失败

```bash
# 检查 db 容器是否健康
docker compose ps db
# STATUS 应该显示 "healthy"

# 手动测试连接
docker compose exec db pg_isready -U smarthr

# 如果数据库损坏，从备份恢复
ls -la /data/backups/
# 选择最近的备份恢复（见 5.4 节）
```

### 6.7 内存不足 (OOM)

```bash
# 查看内存使用
free -h

# 查看各容器内存占用
docker stats --no-stream

# 如果 API 容器占内存过大（Gunicorn workers）
# 可以临时重启
docker compose restart api
```

---

## 7. 安全注意事项

1. **`.env` 文件** — 权限 600，包含所有密钥，切勿提交到 Git
2. **默认密码** — 所有账户初始密码 `Smart2026!`，首次登录强制修改
3. **防火墙** — SmartHR 需要开放 22 (SSH) 和 9527 (HTTP)；同机 `team-wiki` 当前使用 8080；不要开放 5432 (PostgreSQL)
4. **出站流量** — 默认全部放行（调用 MinerU、DeepSeek API 需要）
5. **SSH 登录** — 已为当前 Mac 配置 `ubuntu` 密钥登录；已关闭 SSH 密码登录和 root 直登
6. **HTTPS** — 当前 HTTP 明文，备案域名后应尽快启用 Let's Encrypt SSL

---

## 8. 默认账户

| 用户名 | 角色 | 说明 |
|--------|------|------|
| hr | HR | 人事专员，可上传简历、管理候选人 |
| mgr_delivery | 经理 | 交付经理 |
| mgr_rd | 经理 | 研发经理 |
| mgr_marketing | 经理 | 市场经理 |
| mgr_ops1 | 经理 | 运营经理1 |
| mgr_ops2 | 经理 | 运营经理2 |
| mgr_sales1 | 经理 | 销售经理1 |
| mgr_sales2 | 经理 | 销售经理2 |
| mgr_finance | 经理 | 财务经理 |
| mgr_hr | 经理 | 人事经理 |

初始密码: `Smart2026!`（首次登录强制修改）
密码要求: 至少8位，包含大小写字母、数字、特殊字符

---

## 9. 待办事项

- [ ] 域名备案 (ICP) 后绑定域名
- [ ] 启用 HTTPS (Let's Encrypt)
- [ ] 配置每日自动备份 cron
- [x] 当前 Mac 到 VPS 的 SSH 密钥登录
- [x] 关闭 SSH 密码登录和 root 直登
- [ ] 监控告警（磁盘、内存、服务状态）
- [ ] CI/CD 自动化部署
