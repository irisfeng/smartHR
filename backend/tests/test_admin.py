"""Tests for admin role, reset password, and must_change_password flag."""
from app.models import User


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
