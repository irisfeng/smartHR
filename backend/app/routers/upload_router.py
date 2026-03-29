from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db, SessionLocal
from app.models import User, JobPosition, Candidate, UploadBatch
from app.schemas import UploadBatchResponse
from app.auth import get_current_user, require_role
from app.services.file_service import save_uploaded_file, extract_zip, validate_file
from app.services.pipeline_service import process_batch

router = APIRouter(prefix="/api", tags=["upload"])

async def run_pipeline_background(batch_id: int):
    db = SessionLocal()
    try:
        await process_batch(batch_id, db)
    finally:
        db.close()

@router.post("/positions/{position_id}/upload", response_model=UploadBatchResponse)
async def upload_resumes(
    position_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("hr")),
):
    position = db.query(JobPosition).filter(JobPosition.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    content = await file.read()
    error = validate_file(file.filename, len(content))
    if error:
        raise HTTPException(status_code=400, detail=error)
    saved_path = save_uploaded_file(content, file.filename, position_id)
    if file.filename.lower().endswith(".zip"):
        pdf_paths = extract_zip(saved_path, position_id)
    else:
        pdf_paths = [saved_path]
    batch = UploadBatch(
        job_position_id=position_id,
        uploaded_by=user.id,
        file_name=file.filename,
        file_count=len(pdf_paths),
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    existing_count = db.query(Candidate).filter(Candidate.job_position_id == position_id).count()
    for i, pdf_path in enumerate(pdf_paths):
        candidate = Candidate(
            job_position_id=position_id,
            upload_batch_id=batch.id,
            resume_file_path=pdf_path,
            sequence_no=existing_count + i + 1,
            recommend_date=datetime.now().strftime("%Y-%m-%d"),
            recommend_channel="系统上传",
            status="pending",
        )
        db.add(candidate)
    db.commit()
    background_tasks.add_task(run_pipeline_background, batch.id)
    return batch

@router.get("/upload-batches/{batch_id}/status", response_model=UploadBatchResponse)
def get_batch_status(
    batch_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    batch = db.query(UploadBatch).filter(UploadBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return batch
