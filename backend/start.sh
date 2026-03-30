#!/bin/bash
set -e

cd "$(dirname "$0")"

# 1. 检查 .env
if [ ! -f .env ]; then
    echo "❌ 未找到 .env 文件"
    echo "   cp .env.example .env"
    echo "   然后编辑 .env 填入 API Key"
    exit 1
fi

# 2. 自动生成 SECRET_KEY（如果是默认值）
if grep -q '^SECRET_KEY=change-me' .env; then
    NEW_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    sed -i '' "s|^SECRET_KEY=change-me.*|SECRET_KEY=${NEW_KEY}|" .env
    echo "✅ 已自动生成 SECRET_KEY"
fi

# 3. 安装依赖
if [ ! -d ".venv" ]; then
    echo "📦 安装依赖..."
    pip install -r requirements.txt -q
else
    source .venv/bin/activate 2>/dev/null || true
fi

# 4. 初始化数据库
echo "🗄️  初始化数据库..."
python3 seed.py

# 5. 启动服务
echo "🚀 启动后端服务 http://localhost:8000"
echo "   API 文档 http://localhost:8000/docs"
echo ""
uvicorn app.main:app --reload --port 8000
