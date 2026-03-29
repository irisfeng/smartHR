from sqlalchemy.orm import Session
from app.models import Candidate, UploadBatch, JobPosition
from app.services.mineru_service import parse_pdf
from app.services.ai_service import screen_resume

async def process_candidate(candidate_id: int, db: Session):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        return
    position = db.query(JobPosition).filter(JobPosition.id == candidate.job_position_id).first()
    jd = f"{position.title}\n{position.description}\n{position.requirements}" if position else ""
    try:
        candidate.status = "parsing"
        db.commit()
        parsed_text = await parse_pdf(candidate.resume_file_path)
        candidate.parsed_text = parsed_text
        candidate.status = "screening"
        db.commit()
        result = await screen_resume(parsed_text, jd)
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
        candidate.status = "completed"
        db.commit()
    except Exception as e:
        candidate.status = "failed"
        candidate.error_message = str(e)
        db.commit()

async def process_batch(batch_id: int, db: Session):
    batch = db.query(UploadBatch).filter(UploadBatch.id == batch_id).first()
    if not batch:
        return
    candidates = db.query(Candidate).filter(Candidate.upload_batch_id == batch_id).all()
    for candidate in candidates:
        await process_candidate(candidate.id, db)
        batch.processed_count += 1
        db.commit()
    all_done = all(c.status in ("completed", "failed") for c in candidates)
    batch.status = "completed" if all_done else "failed"
    db.commit()
