import json
from typing import Optional

import httpx
from app.config import settings

SCREENING_PROMPT = """你是一个专业的HR简历筛选助手。请根据以下职位描述(JD)和候选人简历解析文本，进行简历分析和初筛。

## 职位描述
{jd}

## 简历内容
{resume_text}

## 评估方法论

### 第一步：信息提取
从简历文本中提取候选人的基本信息。如果文本中找不到某项信息，对应字段填null，不要猜测或编造。

### 第二步：分析评估
按以下四个维度逐一分析候选人与JD的匹配情况，并给出每个维度的得分(0-100)：

1. **核心技能匹配度(权重40%)**：JD明确要求的技术技能、工具、平台经验
2. **经验相关度(权重30%)**：工作年限、项目经验、行业背景与JD的相关性
3. **学历与资质(权重15%)**：学历层次、专业相关性、专业证书
4. **软技能(权重15%)**：沟通能力、文档能力、团队协作、客户对接等

### 第三步：综合评分
综合得分 = 核心技能×0.4 + 经验相关度×0.3 + 学历资质×0.15 + 软技能×0.15
四舍五入取整。

推荐等级阈值：
- 综合得分≥75 → "推荐"：核心要求基本满足
- 综合得分50-74 → "待定"：部分核心要求满足但有明显短板
- 综合得分<50 → "不推荐"：核心要求大面积不满足

### 解析质量评估
判断简历文本的解析质量：
- "good"：文本完整、格式正常、信息可正常提取
- "poor"：文本大量乱码/图片标签残留/关键信息大面积缺失/格式极度混乱

## 输出要求
请以JSON格式返回分析结果，包含以下字段：
- name: 姓名（字符串，无法提取则为null）
- gender: 性别（字符串，无法提取则为null）
- age: 年龄（整数，无法提取则为null）
- phone: 电话（字符串，无法提取则为null）
- id_number: 身份证号（字符串，无法提取则为null）
- education: 最高学历（字符串，无法提取则为null）
- school: 毕业学校（字符串，无法提取则为null）
- major: 专业（字符串，无法提取则为null）
- analysis: 简要分析思路（2-3句话，说明各维度评分依据）
- match_score: 综合得分（0-100整数，按上述公式计算）
- recommendation: 推荐等级（"推荐"/"待定"/"不推荐"，严格按阈值）
- summary: 筛选评语（100字以内）
- strengths: 优势（字符串数组，2-5条）
- concerns: 顾虑（字符串数组，2-5条）
- parse_quality: 解析质量（"good"或"poor"）

请只返回JSON，不要添加其他内容。"""

EMPTY_RESULT = {
    "name": "", "gender": "", "age": None, "phone": "",
    "id_number": None, "education": "", "school": "", "major": "",
    "analysis": "", "match_score": 0, "recommendation": "待定",
    "summary": "AI服务未配置", "strengths": [], "concerns": [],
    "parse_quality": "good",
}


class AIServiceNotConfiguredError(Exception):
    pass


async def screen_resume(
    resume_text: str,
    jd: str,
    client: Optional[httpx.AsyncClient] = None,
) -> dict:
    if not settings.ai_api_key:
        raise AIServiceNotConfiguredError("AI_API_KEY is not configured")

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
