from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserUpdate, UserResponse, AdminResetPasswordRequest
from app.auth import get_current_user, require_role, hash_password

router = APIRouter(prefix="/api/users", tags=["users"])


def _admin_count(db: Session) -> int:
    return db.query(User).filter(User.role == "admin").count()


@router.get("", response_model=List[UserResponse])
def list_users(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(User).order_by(User.created_at).all()


@router.post("", response_model=UserResponse)
def create_user(body: UserCreate, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    new_user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        role=body.role,
        display_name=body.display_name,
        must_change_password=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    body: UserUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    # Guard: don't let the last admin be demoted
    if body.role is not None and target.role == "admin" and body.role != "admin":
        if _admin_count(db) <= 1:
            raise HTTPException(status_code=400, detail="Cannot demote the last admin")
    if body.display_name is not None:
        target.display_name = body.display_name
    if body.role is not None:
        target.role = body.role
    db.commit()
    db.refresh(target)
    return target


@router.post("/{user_id}/reset-password")
def reset_password(
    user_id: int,
    body: AdminResetPasswordRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="Use change-password for your own account")
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    target.password_hash = hash_password(body.new_password)
    target.must_change_password = True
    db.commit()
    return {"detail": "Password reset"}


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    # Defensive: guard against deleting the last admin. Unreachable via HTTP today
    # since the self-delete guard above fires first when actor==target; the guard
    # stays here in case future code relaxes that invariant.
    if target.role == "admin" and _admin_count(db) <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last admin")
    db.delete(target)
    db.commit()
    return {"detail": "Deleted"}
