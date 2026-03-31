"""Tests for the /api/auth endpoints (login, refresh, me)."""


def test_login_success(client, manager_user):
    resp = client.post("/api/auth/login", json={
        "username": "test_manager",
        "password": "password123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, manager_user):
    resp = client.post("/api/auth/login", json={
        "username": "test_manager",
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


def test_login_nonexistent_user(client):
    resp = client.post("/api/auth/login", json={
        "username": "no_such_user",
        "password": "password123",
    })
    assert resp.status_code == 401


def test_me_with_valid_token(client, manager_user, manager_headers):
    resp = client.get("/api/auth/me", headers=manager_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "test_manager"
    assert data["role"] == "manager"
    assert data["display_name"] == "Test Manager"
    assert data["id"] == manager_user.id
    assert "created_at" in data


def test_me_without_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code in (401, 403)


def test_me_with_invalid_token(client):
    headers = {"Authorization": "Bearer totally.garbage.token"}
    resp = client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 401


def test_refresh_token_success(client, manager_user):
    # First login to obtain a refresh token
    login_resp = client.post("/api/auth/login", json={
        "username": "test_manager",
        "password": "password123",
    })
    refresh_token = login_resp.json()["refresh_token"]

    # Use the refresh token to get new tokens
    resp = client.post("/api/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_refresh_with_invalid_token(client):
    resp = client.post("/api/auth/refresh", json={
        "refresh_token": "not.a.valid.token",
    })
    assert resp.status_code == 401


def test_refresh_with_access_token(client, manager_user, manager_token):
    """Access tokens must be rejected by the refresh endpoint."""
    resp = client.post("/api/auth/refresh", json={
        "refresh_token": manager_token,
    })
    assert resp.status_code == 401
