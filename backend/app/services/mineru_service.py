import asyncio
import io
import zipfile
from pathlib import Path
from typing import Optional

import httpx
from app.config import settings

MINERU_BASE = "https://mineru.net"
POLL_INTERVAL = 3  # seconds
POLL_TIMEOUT = 600  # 10 minutes for large batches
MAX_RETRIES = 3
UPLOAD_CONCURRENCY = 10


async def parse_pdf(file_path: str, client: Optional[httpx.AsyncClient] = None) -> str:
    """Parse a single PDF. Thin wrapper for backward compatibility."""
    if not settings.mineru_api_key:
        return ""
    results = await parse_pdf_batch([file_path], client)
    return results.get(file_path, "")


async def parse_pdf_batch(
    file_paths: list[str],
    client: Optional[httpx.AsyncClient] = None,
) -> dict[str, str]:
    """Parse multiple PDFs in a single MinerU batch.

    Returns dict mapping file_path -> extracted markdown text.
    """
    if not settings.mineru_api_key or not file_paths:
        return {fp: "" for fp in file_paths}

    # Filter to existing files
    valid = [(fp, Path(fp)) for fp in file_paths if Path(fp).exists()]
    if not valid:
        return {fp: "" for fp in file_paths}

    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(timeout=120.0)

    try:
        result_map = await _batch_parse(valid, client)
    finally:
        if owns_client:
            await client.aclose()

    # Fill in empty strings for any paths that weren't in valid set
    return {fp: result_map.get(fp, "") for fp in file_paths}


async def _batch_parse(
    valid: list[tuple[str, Path]],
    client: httpx.AsyncClient,
) -> dict[str, str]:
    """Core batch logic: request URLs -> upload files -> poll -> download results."""
    headers = {
        "Authorization": f"Bearer {settings.mineru_api_key}",
        "Content-Type": "application/json",
    }

    # Build file list with data_id for tracking
    files_payload = []
    path_by_index: dict[int, str] = {}
    for i, (fp, path) in enumerate(valid):
        files_payload.append({"name": path.name, "data_id": str(i)})
        path_by_index[i] = fp

    # Step 1: Request batch upload URLs (max 200 per batch)
    resp = await _request_with_retry(
        client, "POST",
        f"{MINERU_BASE}/api/v4/file-urls/batch",
        headers=headers,
        json={"files": files_payload, "model_version": "vlm"},
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"MinerU batch request failed: {data.get('msg')}")

    batch_id = data["data"]["batch_id"]
    file_urls = data["data"]["file_urls"]

    # Step 2: Concurrent file uploads with semaphore
    sem = asyncio.Semaphore(UPLOAD_CONCURRENCY)

    async def upload_one(idx: int, url: str):
        fp, path = valid[idx]
        content = path.read_bytes()
        async with sem:
            for attempt in range(MAX_RETRIES):
                try:
                    put_resp = await client.put(url, content=content)
                    if put_resp.status_code in (200, 201):
                        return
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(2 ** attempt)
                except httpx.HTTPError:
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(2 ** attempt)
            raise RuntimeError(f"Failed to upload {path.name} after {MAX_RETRIES} retries")

    await asyncio.gather(*[upload_one(i, url) for i, url in enumerate(file_urls)])

    # Step 3: Poll for all results
    elapsed = 0
    result_map: dict[str, str] = {}
    done_indices: set[int] = set()

    while elapsed < POLL_TIMEOUT and len(done_indices) < len(valid):
        await asyncio.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

        poll_resp = await _request_with_retry(
            client, "GET",
            f"{MINERU_BASE}/api/v4/extract-results/batch/{batch_id}",
            headers={"Authorization": f"Bearer {settings.mineru_api_key}"},
        )
        poll_data = poll_resp.json()
        if poll_data.get("code") != 0:
            raise RuntimeError(f"MinerU poll failed: {poll_data.get('msg')}")

        results = poll_data["data"].get("extract_result", [])
        for item in results:
            data_id = item.get("data_id")
            if data_id is None:
                continue
            idx = int(data_id)
            if idx in done_indices:
                continue

            state = item.get("state", "pending")
            if state == "done":
                zip_url = item.get("full_zip_url", "")
                if zip_url:
                    md = await _download_and_extract_markdown(client, zip_url)
                    result_map[path_by_index[idx]] = md
                done_indices.add(idx)
            elif state == "failed":
                err = item.get("err_msg", "Unknown error")
                result_map[path_by_index[idx]] = ""
                done_indices.add(idx)

    # Mark timed-out files as empty
    for i in range(len(valid)):
        fp = path_by_index[i]
        if fp not in result_map:
            result_map[fp] = ""

    return result_map


async def _request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs,
) -> httpx.Response:
    """HTTP request with retry on 503/429/network errors."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = await client.request(method, url, **kwargs)
            if resp.status_code in (503, 429) and attempt < MAX_RETRIES - 1:
                await asyncio.sleep(2 ** attempt + 1)
                continue
            resp.raise_for_status()
            return resp
        except httpx.HTTPError:
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(2 ** attempt + 1)
            else:
                raise
    raise RuntimeError("Unreachable")


async def _download_and_extract_markdown(client: httpx.AsyncClient, zip_url: str) -> str:
    """Download the result zip and extract the full.md content."""
    zip_resp = await _request_with_retry(client, "GET", zip_url)

    with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as zf:
        for name in zf.namelist():
            if name.endswith("full.md"):
                return zf.read(name).decode("utf-8")
        for name in zf.namelist():
            if name.endswith(".md"):
                return zf.read(name).decode("utf-8")

    return ""
