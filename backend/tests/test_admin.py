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


# ---------------------------------------------------------------------------
# Task 6: Admin-only CRUD, reset-password, and last-admin safeguards
# ---------------------------------------------------------------------------
from app.auth import hash_password, create_access_token


def _make_admin(db):
    u = User(
        username="admin1",
        password_hash=hash_password("password123"),
        role="admin",
        display_name="Admin1",
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


def _make_hr(db, username="hr1"):
    u = User(
        username=username,
        password_hash=hash_password("password123"),
        role="hr",
        display_name="HR1",
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


def _headers_for(user):
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}


def test_admin_can_create_user(client, db):
    admin = _make_admin(db)
    resp = client.post(
        "/api/users",
        headers=_headers_for(admin),
        json={"username": "newguy", "password": "pwd1234", "role": "hr", "display_name": "NG"},
    )
    assert resp.status_code == 200
    assert resp.json()["must_change_password"] is True


def test_manager_cannot_create_user(client, manager_headers):
    resp = client.post(
        "/api/users",
        headers=manager_headers,
        json={"username": "nope", "password": "pwd1234", "role": "hr", "display_name": "NP"},
    )
    assert resp.status_code == 403


def test_admin_can_update_user(client, db):
    admin = _make_admin(db)
    target = _make_hr(db)
    resp = client.put(
        f"/api/users/{target.id}",
        headers=_headers_for(admin),
        json={"display_name": "Renamed", "role": "manager"},
    )
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Renamed"
    assert resp.json()["role"] == "manager"


def test_admin_reset_password_sets_flag(client, db):
    admin = _make_admin(db)
    target = _make_hr(db)
    resp = client.post(
        f"/api/users/{target.id}/reset-password",
        headers=_headers_for(admin),
        json={"new_password": "Aa1!aaaa"},
    )
    assert resp.status_code == 200
    db.refresh(target)
    assert target.must_change_password is True


def test_admin_cannot_reset_own_password(client, db):
    admin = _make_admin(db)
    resp = client.post(
        f"/api/users/{admin.id}/reset-password",
        headers=_headers_for(admin),
        json={"new_password": "Aa1!aaaa"},
    )
    assert resp.status_code == 400


def test_admin_cannot_delete_self(client, db):
    admin = _make_admin(db)
    resp = client.delete(f"/api/users/{admin.id}", headers=_headers_for(admin))
    assert resp.status_code == 400


def test_cannot_demote_last_admin(client, db):
    """With a single admin, attempting to demote its role must fail with 400."""
    admin = _make_admin(db)
    # Bring up a second admin so we can use it to attempt the demotion
    admin2 = User(
        username="admin2",
        password_hash=hash_password("password123"),
        role="admin",
        display_name="Admin2",
    )
    db.add(admin2); db.commit(); db.refresh(admin2)
    # admin2 demotes the original admin -> allowed (2 admins -> 1 admin)
    resp = client.put(
        f"/api/users/{admin.id}",
        headers=_headers_for(admin2),
        json={"role": "hr"},
    )
    assert resp.status_code == 200
    # Now only admin2 remains. Trying to demote admin2 via admin2 -> must hit last-admin guard.
    resp2 = client.put(
        f"/api/users/{admin2.id}",
        headers=_headers_for(admin2),
        json={"role": "hr"},
    )
    assert resp2.status_code == 400
    assert "last admin" in resp2.json()["detail"].lower()
