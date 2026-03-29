import httpx
from app.config import settings

async def parse_pdf(file_path: str) -> str:
    if not settings.mineru_api_url or not settings.mineru_api_key:
        return ""
    async with httpx.AsyncClient(timeout=120.0) as client:
        with open(file_path, "rb") as f:
            response = await client.post(
                f"{settings.mineru_api_url}/parse",
                headers={"Authorization": f"Bearer {settings.mineru_api_key}"},
                files={"file": (file_path.split("/")[-1], f, "application/pdf")},
            )
        response.raise_for_status()
        data = response.json()
        return data.get("text", data.get("content", str(data)))
