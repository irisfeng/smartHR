# SmartHR

AI 驱动的内部 HR 简历筛选系统。上传简历 ZIP/PDF， MinerU 自动解析，DeepSeek AI 评分筛选，结果可导出 Excel。

## 技术栈

- **后端:** FastAPI + SQLAlchemy + SQLite
- **前端:** React 19 + Ant Design 6 + TypeScript
- **AI:** MinerU v4 (PDF 解析) + DeepSeek (简历筛选)
- **认证:** JWT (双角色: HR / 用人经理)

## 快速开始

### 1. 配置环境变量

```bash
cd backend
cp .env.example .env
# 编辑 .env 填入你的 API Key
```

`.env` 内容：

```env
SECRET_KEY=（自动生成，无需手动填写）
MINERU_API_KEY=你的MinerU Token
AI_API_URL=https://api.deepseek.com/v1
AI_API_KEY=你的DeepSeek Key
AI_MODEL=deepseek-chat
```

### 2. 启动后端

```bash
cd backend
./start.sh
```

一键命令完成：自动生成 SECRET_KEY、安装依赖、初始化数据库、启动服务。

### 3. 启动前端

```bash
cd frontend
npm install   # 首次运行
npm run dev
```

### 4. 访问

- 前端：http://localhost:5173
- 后端 API 文档：http://localhost:8000/docs

## 用户角色

| 角色 | 权限 |
|------|------|
| HR 专员 | 上传简历、查看/编辑候选人、导出 Excel、管理用户 |
| 用人经理 | 创建/编辑职位、查看 AI 筛选结果、更新面试状态 |

## 核心流程

1. 用人经理创建职位（含 JD）
2. HR 上传简历 ZIP/PDF → MinerU 解析 → DeepSeek 评分筛选
3. HR/经理查看候选人表格（AI 评分、推荐等级、匹配度）
4. 导出 Excel（匹配公司模板格式）

## 项目结构

```
backend/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py             # 环境变量配置
│   ├── auth.py               # JWT 认证
│   ├── models.py             # 数据模型
│   ├── schemas.py            # Pydantic schemas
│   ├── routers/              # API 路由
│   └── services/             # 业务逻辑（MinerU、AI、文件处理、导出）
├── seed.py                   # 初始用户
├── start.sh                 # 一键启动脚本
└── .env.example

frontend/
├── src/
│   ├── pages/               # 页面组件
│   ├── components/           # 布局、路由守卫、ErrorBoundary
│   ├── store/                # Zustand 状态管理
│   └── api.ts                # Axios 客户端（含 token 刷新）
```
