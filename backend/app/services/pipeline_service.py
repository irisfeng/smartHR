import asyncio
import logging

import httpx
from sqlalchemy.orm import Session
from app.models import Candidate, UploadBatch, JobPosition
from app.services.mineru_service import parse_pdf_batch
from app.services.ai_service import screen_resume

logger = logging.getLogger(__name__)

AI_CONCURRENCY = 5  # max concurrent DeepSeek calls


def _apply_ai_result(candidate: Candidate, result: dict):
    """Write AI screening result fields onto a Candidate."""
    candidate.ai_screening_result = result
    candidate.name = result.get("name") or ""
    candidate.gender = result.get("gender") or ""
    candidate.age = result.get("age")
    candidate.phone = result.get("phone") or ""
    candidate.id_number = result.get("id_number") or ""
    candidate.education = result.get("education") or ""
    candidate.school = result.get("school") or ""
    candidate.major = result.get("major") or ""
    candidate.match_score = result.get("match_score") or 0
    candidate.ai_recommendation = result.get("recommendation") or "待定"
    candidate.ai_summary = result.get("summary") or ""
    candidate.leader_screening = result.get("recommendation") or ""
    # Parse quality from AI assessment
    candidate.parse_quality = result.get("parse_quality") or "good"
    # Double-check: if AI said "good" but key fields are all empty/placeholder, override to "poor"
    if candidate.parse_quality != "poor":
        key_fields = [candidate.name, candidate.gender, candidate.education, candidate.school]
        empty_markers = {"", "未提供", "姓名未提供", "性别未提供", "null"}
        if all(not f or f in empty_markers for f in key_fields):
            candidate.parse_quality = "poor"


async def process_batch(batch_id: int, db: Session):
    batch = db.query(UploadBatch).filter(UploadBatch.id == batch_id).first()
    if not batch:
        return

    candidates = db.query(Candidate).filter(Candidate.upload_batch_id == batch_id).all()
    if not candidates:
        batch.status = "completed"
        db.commit()
        return

    position = db.query(JobPosition).filter(JobPosition.id == batch.job_position_id).first()
    jd = f"{position.title}\n{position.description}\n{position.requirements}" if position else ""

    # -- Phase 1: Batch parse all PDFs with MinerU --
    for c in candidates:
        c.status = "parsing"
    db.commit()

    file_paths = [c.resume_file_path for c in candidates]

    async with httpx.AsyncClient(timeout=120.0) as shared_client:
        try:
            parsed_map = await parse_pdf_batch(file_paths, shared_client)
        except Exception as e:
            # parse_pdf_batch itself now handles per-chunk failures internally
            # and returns empty strings for failed files, so this top-level
            # except only fires on truly catastrophic errors (e.g. invalid
            # config). Mark every candidate failed and bail.
            logger.error(f"MinerU batch parse crashed: {e}", exc_info=True)
            parsed_map = {fp: "" for fp in file_paths}

        # Save parsed text (strip NUL bytes — PostgreSQL rejects 0x00 in text columns).
        # Candidates with empty parsed_text after MinerU are marked failed up-front
        # so we don't waste AI calls on empty input and don't silently produce
        # "0 score / 不推荐" rows that look like real evaluations.
        candidates_for_ai: list[Candidate] = []
        parse_failed_count = 0
        for c in candidates:
            raw = parsed_map.get(c.resume_file_path, "")
            cleaned = raw.replace("\x00", "") if raw else ""
            c.parsed_text = cleaned
            if not cleaned.strip():
                c.status = "failed"
                c.error_message = "MinerU 解析失败或被限流（parsed_text 为空）"
                batch.processed_count = (batch.processed_count or 0) + 1
                parse_failed_count += 1
            else:
                c.status = "screening"
                candidates_for_ai.append(c)
        db.commit()

        if parse_failed_count:
            logger.warning(
                "Batch %s: %d/%d candidates failed PDF parsing (MinerU)",
                batch_id, parse_failed_count, len(candidates),
            )

        # -- Phase 2: Concurrent AI screening with semaphore --
        sem = asyncio.Semaphore(AI_CONCURRENCY)
        db_lock = asyncio.Lock()  # serialize DB writes to avoid session race conditions

        async def screen_one(candidate: Candidate):
            async with sem:
                try:
                    result = await screen_resume(
                        candidate.parsed_text or "",
                        jd,
                        shared_client,
                    )
                except Exception as e:
                    logger.error(f"AI screening failed for candidate {candidate.id}: {e}")
                    async with db_lock:
                        candidate.status = "failed"
                        candidate.error_message = str(e)
                        batch.processed_count = (batch.processed_count or 0) + 1
                        db.commit()
                    return

                async with db_lock:
                    _apply_ai_result(candidate, result)
                    candidate.status = "completed"
                    batch.processed_count = (batch.processed_count or 0) + 1
                    db.commit()

        await asyncio.gather(*[screen_one(c) for c in candidates_for_ai])

    # Commit any remaining results
    db.commit()

    # Update batch final status
    all_done = all(c.status in ("completed", "failed") for c in candidates)
    batch.status = "completed" if all_done else "failed"
    db.commit()
