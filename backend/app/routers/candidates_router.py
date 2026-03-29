from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import User, Candidate
from app.schemas import CandidateResponse, CandidateDetailResponse, CandidateUpdate
from app.auth import get_current_user

router = APIRouter(tags=["candidates"])

@router.get("/api/positions/{position_id}/candidates", response_model=List[CandidateResponse])
def list_candidates(
    position_id: int,
    recommendation: Optional[str] = Query(None),
    education: Optional[str] = Query(None),
    sort_by: str = Query("match_score"),
    sort_order: str = Query("desc"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Candidate).filter(Candidate.job_position_id == position_id)
    if recommendation:
        query = query.filter(Candidate.ai_recommendation == recommendation)
    if education:
        query = query.filter(Candidate.education == education)
    sort_col = getattr(Candidate, sort_by, Candidate.match_score)
    if sort_order == "desc":
        query = query.order_by(sort_col.desc().nulls_last())
    else:
        query = query.order_by(sort_col.asc().nulls_last())
    return query.all()

@router.get("/api/candidates/{candidate_id}", response_model=CandidateDetailResponse)
def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate

@router.patch("/api/candidates/{candidate_id}", response_model=CandidateResponse)
def update_candidate(
    candidate_id: int,
    body: CandidateUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(candidate, key, value)
    db.commit()
    db.refresh(candidate)
    return candidate

@router.get("/api/candidates/{candidate_id}/resume")
def get_resume(
    candidate_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return FileResponse(candidate.resume_file_path, media_type="application/pdf")
