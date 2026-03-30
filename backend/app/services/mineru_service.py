import asyncio
import io
import zipfile
from pathlib import Path

import httpx
from app.config import settings

MINERU_BASE = "https://mineru.net"
POLL_INTERVAL = 3  # seconds
POLL_TIMEOUT = 300  # 5 minutes


async def parse_pdf(file_path: str) -> str:
    """Parse a PDF using MinerU v4 Precision Parsing API.

    Flow: request upload URL → PUT file → poll for result → download zip → extract markdown.
    Returns empty string if MinerU is not configured.
    """
    if not settings.mineru_api_key:
        return ""

    path = Path(file_path)
    if not path.exists():
        return ""

    async with httpx.AsyncClient(timeout=120.0) as client:
        # Step 1: Request batch upload URL
        filename = path.name
        resp = await client.post(
            f"{MINERU_BASE}/api/v4/file-urls/batch",
            headers={
                "Authorization": f"Bearer {settings.mineru_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "files": [{"name": filename}],
                "model_version": "vlm",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"MinerU batch request failed: {data.get('msg')}")

        batch_id = data["data"]["batch_id"]
        file_urls = data["data"]["file_urls"]

        # Step 2: Upload file to signed URL
        file_content = path.read_bytes()
        put_resp = await client.put(file_urls[0], content=file_content)
        if put_resp.status_code not in (200, 201):
            raise RuntimeError(f"MinerU file upload failed: HTTP {put_resp.status_code}")

        # Step 3: Poll for result
        elapsed = 0
        while elapsed < POLL_TIMEOUT:
            await asyncio.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL

            poll_resp = await client.get(
                f"{MINERU_BASE}/api/v4/extract-results/batch/{batch_id}",
                headers={"Authorization": f"Bearer {settings.mineru_api_key}"},
            )
            poll_resp.raise_for_status()
            poll_data = poll_resp.json()

            if poll_data.get("code") != 0:
                raise RuntimeError(f"MinerU poll failed: {poll_data.get('msg')}")

            results = poll_data["data"].get("extract_result", [])
            if not results:
                continue

            state = results[0].get("state", "pending")
            if state == "done":
                zip_url = results[0].get("full_zip_url", "")
                if not zip_url:
                    raise RuntimeError("MinerU completed but no zip URL returned")
                # Step 4: Download zip and extract markdown
                return await _download_and_extract_markdown(client, zip_url)
            elif state == "failed":
                err = results[0].get("err_msg", "Unknown error")
                raise RuntimeError(f"MinerU parsing failed: {err}")

        raise RuntimeError(f"MinerU parsing timed out after {POLL_TIMEOUT}s")


async def _download_and_extract_markdown(client: httpx.AsyncClient, zip_url: str) -> str:
    """Download the result zip and extract the full.md content."""
    zip_resp = await client.get(zip_url)
    zip_resp.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as zf:
        # Look for full.md in the zip
        for name in zf.namelist():
            if name.endswith("full.md"):
                return zf.read(name).decode("utf-8")
        # Fallback: try any .md file
        for name in zf.namelist():
            if name.endswith(".md"):
                return zf.read(name).decode("utf-8")

    raise RuntimeError("No markdown file found in MinerU result zip")
