"""Tests for admin role, reset password, and must_change_password flag."""
from app.models import User
import pytest
from pydantic import ValidationError
from app.schemas import UserCreate, UserUpdate, AdminResetPasswordRequest


def test_user_model_has_must_change_password_default_false(db):
    user = User(
        username="u1",
        password_hash="x",
        role="hr",
        display_name="U",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    assert user.must_change_password is False


def test_user_create_accepts_admin_role():
    u = UserCreate(username="admin_user", password="Aa1!aaaa", role="admin", display_name="A")
    assert u.role == "admin"


def test_user_create_rejects_unknown_role():
    with pytest.raises(ValidationError):
        UserCreate(username="testuser", password="Aa1!aaaa", role="root", display_name="A")


def test_user_update_all_fields_optional():
    u = UserUpdate()
    assert u.display_name is None
    assert u.role is None


def test_admin_reset_password_enforces_complexity():
    with pytest.raises(ValidationError):
        AdminResetPasswordRequest(new_password="short")
    ok = AdminResetPasswordRequest(new_password="Aa1!aaaa")
    assert ok.new_password == "Aa1!aaaa"
