import os
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, JobPosition
from app.auth import get_current_user, require_role
from app.services.export_service import generate_excel

# Users allowed to export in addition to HR
EXPORT_ALLOWED_MANAGERS = {"mgr_delivery"}

router = APIRouter(prefix="/api/positions", tags=["export"])

@router.get("/{position_id}/export")
def export_excel(
    position_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from fastapi import HTTPException
    if user.role != "hr" and user.username not in EXPORT_ALLOWED_MANAGERS:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    position = db.query(JobPosition).filter(JobPosition.id == position_id).first()
    filename = f"{position.title}_候选人.xlsx" if position else "candidates.xlsx"
    path = generate_excel(position_id, db)
    return FileResponse(
        path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        background=BackgroundTask(os.unlink, path),
    )
