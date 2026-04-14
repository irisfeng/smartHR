from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, TokenResponse, RefreshRequest, UserResponse, ChangePasswordRequest
from app.auth import (
    verify_password, hash_password, create_access_token, create_refresh_token, get_current_user,
)
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {
        "access_token": create_access_token(user.id, user.role),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer",
        "must_change_password": user.must_change_password,
    }

@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(body.refresh_token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id),
    )

@router.post("/change-password")
def change_password(body: ChangePasswordRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Old password is incorrect")
    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False
    db.commit()
    return {"detail": "Password changed"}

@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user
