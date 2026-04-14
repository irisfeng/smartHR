"""Tests for the HTTP 428 must-change-password interception."""
from app.models import User
from app.auth import hash_password, create_access_token


def _make_user(db, *, role="hr", must_change=False):
    u = User(
        username=f"flagged_{role}_{int(must_change)}",
        password_hash=hash_password("password123"),
        role=role,
        display_name="Flagged",
        must_change_password=must_change,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def test_flagged_user_blocked_from_business_endpoint(client, db):
    u = _make_user(db, must_change=True)
    token = create_access_token(u.id, u.role)
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/positions", headers=headers)
    assert resp.status_code == 428
    body = resp.json()
    assert body["detail"] == "Password change required"


def test_flagged_user_can_still_change_password(client, db):
    u = _make_user(db, must_change=True)
    token = create_access_token(u.id, u.role)
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"old_password": "password123", "new_password": "Aa1!aaaa"},
    )
    assert resp.status_code == 200


def test_unflagged_user_is_not_blocked(client, db):
    u = _make_user(db, must_change=False)
    token = create_access_token(u.id, u.role)
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/positions", headers=headers)
    assert resp.status_code == 200
