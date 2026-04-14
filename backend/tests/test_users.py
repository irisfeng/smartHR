"""Tests for the /api/users endpoints (list, create, delete)."""


def test_list_users(client, manager_user, hr_user, manager_headers):
    resp = client.get("/api/users", headers=manager_headers)
    assert resp.status_code == 200
    data = resp.json()
    usernames = [u["username"] for u in data]
    assert "test_manager" in usernames
    assert "test_hr" in usernames
    # Verify shape of returned objects
    for u in data:
        assert "id" in u
        assert "username" in u
        assert "role" in u
        assert "display_name" in u
        assert "created_at" in u


def test_create_user_success(client, admin_headers):
    resp = client.post("/api/users", headers=admin_headers, json={
        "username": "new_hr_user",
        "password": "securepass",
        "role": "hr",
        "display_name": "New HR",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "new_hr_user"
    assert data["role"] == "hr"
    assert data["display_name"] == "New HR"
    assert "id" in data
    assert "created_at" in data
    # password must not be in the response
    assert "password" not in data
    assert "password_hash" not in data


def test_create_user_duplicate_username(client, manager_user, admin_headers):
    resp = client.post("/api/users", headers=admin_headers, json={
        "username": "test_manager",
        "password": "securepass",
        "role": "hr",
        "display_name": "Duplicate",
    })
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Username already exists"


def test_create_user_invalid_role(client, admin_headers):
    resp = client.post("/api/users", headers=admin_headers, json={
        "username": "bad_role_user",
        "password": "securepass",
        "role": "root",
        "display_name": "Bad Role",
    })
    assert resp.status_code == 422


def test_create_user_short_password(client, admin_headers):
    resp = client.post("/api/users", headers=admin_headers, json={
        "username": "short_pw_user",
        "password": "12345",
        "role": "hr",
        "display_name": "Short PW",
    })
    assert resp.status_code == 422


def test_create_user_short_username(client, admin_headers):
    resp = client.post("/api/users", headers=admin_headers, json={
        "username": "a",
        "password": "securepass",
        "role": "hr",
        "display_name": "Short Name",
    })
    assert resp.status_code == 422


def test_delete_user_success(client, manager_user, hr_user, admin_user, admin_headers):
    resp = client.delete(f"/api/users/{hr_user.id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["detail"] == "Deleted"
    # Confirm user is actually gone
    list_resp = client.get("/api/users", headers=admin_headers)
    remaining_ids = [u["id"] for u in list_resp.json()]
    assert hr_user.id not in remaining_ids


def test_delete_user_not_found(client, admin_headers):
    resp = client.delete("/api/users/99999", headers=admin_headers)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "User not found"


def test_delete_self(client, admin_user, admin_headers):
    resp = client.delete(f"/api/users/{admin_user.id}", headers=admin_headers)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Cannot delete yourself"


def test_list_users_unauthenticated(client):
    resp = client.get("/api/users")
    assert resp.status_code == 403


def test_create_user_as_hr_forbidden(client, hr_headers):
    """HR users cannot create new users — only admins can."""
    resp = client.post("/api/users", headers=hr_headers, json={
        "username": "sneaky_admin",
        "password": "securepass",
        "role": "manager",
        "display_name": "Privilege Escalation",
    })
    assert resp.status_code == 403


def test_delete_user_as_hr_forbidden(client, hr_user, manager_user, hr_headers):
    """HR users cannot delete users — only admins can."""
    resp = client.delete(f"/api/users/{manager_user.id}", headers=hr_headers)
    assert resp.status_code == 403
