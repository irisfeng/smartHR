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
    candidate.name = result.get("name", "")
    candidate.gender = result.get("gender", "")
    candidate.age = result.get("age")
    candidate.phone = result.get("phone", "")
    candidate.id_number = result.get("id_number", "")
    candidate.education = result.get("education", "")
    candidate.school = result.get("school", "")
    candidate.major = result.get("major", "")
    candidate.match_score = result.get("match_score", 0)
    candidate.ai_recommendation = result.get("recommendation", "待定")
    candidate.ai_summary = result.get("summary", "")
    candidate.leader_screening = result.get("recommendation", "")


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
            logger.error(f"MinerU batch parse failed: {e}")
            parsed_map = {fp: "" for fp in file_paths}

        # Save parsed text
        for c in candidates:
            c.parsed_text = parsed_map.get(c.resume_file_path, "")
            c.status = "screening"
        db.commit()

        # -- Phase 2: Concurrent AI screening with semaphore --
        sem = asyncio.Semaphore(AI_CONCURRENCY)

        async def screen_one(candidate: Candidate):
            async with sem:
                try:
                    result = await screen_resume(
                        candidate.parsed_text or "",
                        jd,
                        shared_client,
                    )
                    _apply_ai_result(candidate, result)
                    candidate.status = "completed"
                except Exception as e:
                    logger.error(f"AI screening failed for candidate {candidate.id}: {e}")
                    candidate.status = "failed"
                    candidate.error_message = str(e)

        await asyncio.gather(*[screen_one(c) for c in candidates])

    # Commit all results
    db.commit()

    # Update batch progress and status
    batch.processed_count = len(candidates)
    all_done = all(c.status in ("completed", "failed") for c in candidates)
    batch.status = "completed" if all_done else "failed"
    db.commit()
