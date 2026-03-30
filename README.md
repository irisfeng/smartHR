# SmartHR

AI 驱动的内部 HR 简历筛选系统。上传简历 ZIP/PDF，AI 自动解析、评分、筛选，结果可导出 Excel。

## 技术栈

- **后端:** FastAPI + SQLAlchemy + SQLite
- **前端:** React 19 + Ant Design 6 + TypeScript
- **AI:** MinerU (PDF 解析) + DeepSeek (简历筛选)
- **认证:** JWT (双角色: HR / 用人经理)

## 快速开始

```bash
# 1. 后端
cd backend
pip install -r requirements.txt
cp .env.example .env   # 编辑 .env 填入 API Key
python seed.py          # 创建初始用户
uvicorn app.main:app --reload --port 8000

# 2. 前端
cd frontend
npm install
npm run dev             # http://localhost:5173
```

## 环境变量

```env
SECRET_KEY=your-random-secret
MINERU_API_URL=https://your-mineru-endpoint/api
MINERU_API_KEY=your-mineru-key
AI_API_URL=https://api.deepseek.com/v1
AI_API_KEY=your-deepseek-key
AI_MODEL=deepseek-chat
```

> MinerU 未配置时 PDF 解析返回空文本；DeepSeek 未配置时 AI 筛选返回占位结果。系统可正常运行。

## 核心流程

1. **用人经理** 创建职位（含 JD）
2. **HR** 上传简历 ZIP/PDF → MinerU 解析 → DeepSeek 评分筛选
3. **HR/经理** 查看候选人表格（AI 评分、推荐等级、匹配度）
4. 导出 Excel（匹配公司模板格式）

## 用户角色

| 角色 | 权限 |
|------|------|
| HR 专员 | 上传简历、查看/编辑候选人、导出 Excel、管理用户 |
| 用人经理 | 创建/编辑职位、查看 AI 筛选结果、更新面试状态 |

## API

后端运行后访问 `http://localhost:8000/docs` 查看完整 API 文档。
