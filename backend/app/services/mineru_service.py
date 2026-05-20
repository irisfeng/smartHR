import asyncio
import io
import logging
import zipfile
from pathlib import Path
from typing import Optional

import httpx
from app.config import settings

logger = logging.getLogger(__name__)

MINERU_BASE = "https://mineru.net"
POLL_INTERVAL = 3  # seconds
POLL_TIMEOUT = 600  # 10 minutes for large batches
MAX_RETRIES = 3
UPLOAD_CONCURRENCY = 10

# Rate-limit handling
# MinerU's free tier rate-limits the /file-urls/batch endpoint when 75+ files
# are submitted in quick succession. Split large batches into chunks and
# sleep between chunks to stay under the per-minute window.
CHUNK_SIZE = 20            # files per MinerU batch submission
INTER_CHUNK_SLEEP = 30     # seconds to wait between chunks
# Long backoff schedule (seconds) for 429 / 503 retries on rate-limited endpoints.
# Total wall-clock budget ~16 min before giving up — enough to ride out a hard
# per-hour quota window on MinerU's side.
RATE_LIMIT_BACKOFF = [60, 180, 300, 600]


class MineruRateLimitError(RuntimeError):
    """Raised when MinerU keeps returning 429 after all retries."""


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
        # Chunk large batches to stay under MinerU's per-minute rate limit.
        result_map: dict[str, str] = {}
        chunks = [valid[i:i + CHUNK_SIZE] for i in range(0, len(valid), CHUNK_SIZE)]
        for chunk_idx, chunk in enumerate(chunks):
            logger.info(
                "MinerU chunk %d/%d (%d files)",
                chunk_idx + 1, len(chunks), len(chunk),
            )
            try:
                chunk_result = await _batch_parse(chunk, client)
            except MineruRateLimitError as e:
                # Rate-limited even after long retries: surface as empty for
                # this chunk's files so the caller can mark them failed.
                # Do NOT abort remaining chunks — later ones might succeed
                # once the rate window resets.
                logger.error("MinerU chunk %d rate-limited, marking empty: %s", chunk_idx + 1, e)
                chunk_result = {}
            except Exception as e:
                # Any other error (bad payload, network, MinerU server-side
                # code != 0): isolate to this chunk so other chunks can still
                # succeed. Caller distinguishes empty result -> mark failed.
                logger.error("MinerU chunk %d failed: %s", chunk_idx + 1, e, exc_info=True)
                chunk_result = {}
            result_map.update(chunk_result)
            if chunk_idx < len(chunks) - 1:
                await asyncio.sleep(INTER_CHUNK_SLEEP)
    finally:
        if owns_client:
            await client.aclose()

    # Fill in empty strings for any paths that weren't in valid set or that failed
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
    """HTTP request with retry on 503/429/network errors.

    429/503 (rate-limit) use a long backoff schedule (RATE_LIMIT_BACKOFF)
    because MinerU's rate window appears to be per-minute or longer; sub-second
    retries don't help. Other network errors use a short exponential backoff
    (MAX_RETRIES attempts).
    """
    rate_limit_attempts = 0
    network_attempts = 0
    while True:
        try:
            resp = await client.request(method, url, **kwargs)
            if resp.status_code in (503, 429):
                if rate_limit_attempts >= len(RATE_LIMIT_BACKOFF):
                    raise MineruRateLimitError(
                        f"MinerU {url} returned HTTP {resp.status_code} "
                        f"after {rate_limit_attempts} long-backoff retries"
                    )
                sleep_s = RATE_LIMIT_BACKOFF[rate_limit_attempts]
                rate_limit_attempts += 1
                logger.warning(
                    "MinerU %s -> HTTP %d, backing off %ds (rate-limit retry %d/%d)",
                    url, resp.status_code, sleep_s,
                    rate_limit_attempts, len(RATE_LIMIT_BACKOFF),
                )
                await asyncio.sleep(sleep_s)
                continue
            resp.raise_for_status()
            return resp
        except httpx.HTTPError:
            network_attempts += 1
            if network_attempts >= MAX_RETRIES:
                raise
            await asyncio.sleep(2 ** network_attempts + 1)


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
