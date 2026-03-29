from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, JobPosition
from app.auth import get_current_user
from app.services.export_service import generate_excel

router = APIRouter(prefix="/api/positions", tags=["export"])

@router.get("/{position_id}/export")
def export_excel(
    position_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    position = db.query(JobPosition).filter(JobPosition.id == position_id).first()
    filename = f"{position.title}_候选人.xlsx" if position else "candidates.xlsx"
    path = generate_excel(position_id, db)
    return FileResponse(path, filename=filename, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
