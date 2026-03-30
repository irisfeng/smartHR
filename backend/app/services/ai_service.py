import json
from typing import Optional

import httpx
from app.config import settings

SCREENING_PROMPT = """你是一个专业的HR简历筛选助手。请根据以下职位描述(JD)和候选人简历内容，进行简历分析和初筛。

## 职位描述
{jd}

## 简历内容
{resume_text}

## 要求
请以JSON格式返回分析结果，包含以下字段：
- name: 姓名（字符串）
- gender: 性别（字符串）
- age: 年龄（整数或null）
- phone: 电话（字符串）
- id_number: 身份证号（字符串或null）
- education: 最高学历（字符串）
- school: 毕业学校（字符串）
- major: 专业（字符串）
- match_score: 与JD的匹配度（0-100整数）
- recommendation: 推荐等级（"推荐"/"待定"/"不推荐"）
- summary: 筛选评语（简述匹配原因，100字以内）
- strengths: 优势（字符串数组）
- concerns: 顾虑（字符串数组）

请只返回JSON，不要添加其他内容。"""

EMPTY_RESULT = {
    "name": "", "gender": "", "age": None, "phone": "",
    "id_number": None, "education": "", "school": "", "major": "",
    "match_score": 0, "recommendation": "待定",
    "summary": "AI服务未配置", "strengths": [], "concerns": [],
}


async def screen_resume(
    resume_text: str,
    jd: str,
    client: Optional[httpx.AsyncClient] = None,
) -> dict:
    if not settings.ai_api_key:
        return dict(EMPTY_RESULT)

    prompt = SCREENING_PROMPT.format(jd=jd, resume_text=resume_text)

    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(timeout=60.0)

    try:
        response = await client.post(
            f"{settings.ai_api_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.ai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.ai_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    finally:
        if owns_client:
            await client.aclose()
