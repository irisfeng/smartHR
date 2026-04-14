from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User, JobPosition, Candidate
from app.schemas import PositionCreate, PositionUpdate, PositionResponse
from app.auth import get_current_active_user, require_role

router = APIRouter(prefix="/api/positions", tags=["positions"])

@router.get("", response_model=List[PositionResponse])
def list_positions(db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    positions = db.query(JobPosition).order_by(JobPosition.created_at.desc()).all()
    result = []
    for p in positions:
        count = db.query(Candidate).filter(Candidate.job_position_id == p.id).count()
        resp = PositionResponse.model_validate(p)
        resp.candidate_count = count
        result.append(resp)
    return result

@router.post("", response_model=PositionResponse)
def create_position(
    body: PositionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager")),
):
    position = JobPosition(**body.model_dump(), created_by=user.id)
    db.add(position)
    db.commit()
    db.refresh(position)
    resp = PositionResponse.model_validate(position)
    resp.candidate_count = 0
    return resp

@router.get("/{position_id}", response_model=PositionResponse)
def get_position(position_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    position = db.query(JobPosition).filter(JobPosition.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    count = db.query(Candidate).filter(Candidate.job_position_id == position.id).count()
    resp = PositionResponse.model_validate(position)
    resp.candidate_count = count
    return resp

@router.put("/{position_id}", response_model=PositionResponse)
def update_position(
    position_id: int,
    body: PositionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager")),
):
    position = db.query(JobPosition).filter(JobPosition.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(position, key, value)
    db.commit()
    db.refresh(position)
    count = db.query(Candidate).filter(Candidate.job_position_id == position.id).count()
    resp = PositionResponse.model_validate(position)
    resp.candidate_count = count
    return resp
