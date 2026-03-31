"""Tests for the positions API (/api/positions)."""

import pytest


POSITIONS_URL = "/api/positions"


def _make_position_payload(**overrides) -> dict:
    defaults = {
        "title": "Software Engineer",
        "department": "Engineering",
        "description": "Build and maintain backend services.",
        "requirements": "3+ years Python experience",
    }
    defaults.update(overrides)
    return defaults


# ── helpers ────────────────────────────────────────────────────────────


def _create_position(client, headers, **overrides):
    """Create a position via the API and return the response."""
    payload = _make_position_payload(**overrides)
    return client.post(POSITIONS_URL, json=payload, headers=headers)


# ── tests ──────────────────────────────────────────────────────────────


def test_list_positions_empty(client, manager_headers):
    """GET /api/positions returns an empty list when no positions exist."""
    resp = client.get(POSITIONS_URL, headers=manager_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_position_as_manager(client, manager_headers, manager_user):
    """POST /api/positions as manager returns 200 with the created position."""
    payload = _make_position_payload()
    resp = client.post(POSITIONS_URL, json=payload, headers=manager_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == payload["title"]
    assert data["department"] == payload["department"]
    assert data["description"] == payload["description"]
    assert data["requirements"] == payload["requirements"]
    assert data["status"] == "open"
    assert data["created_by"] == manager_user.id
    assert data["candidate_count"] == 0
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_position_as_hr_forbidden(client, hr_headers):
    """POST /api/positions as HR user returns 403."""
    payload = _make_position_payload()
    resp = client.post(POSITIONS_URL, json=payload, headers=hr_headers)

    assert resp.status_code == 403


def test_list_positions_after_create(client, manager_headers):
    """GET /api/positions returns created positions."""
    _create_position(client, manager_headers, title="Backend Engineer")
    _create_position(client, manager_headers, title="Frontend Engineer")

    resp = client.get(POSITIONS_URL, headers=manager_headers)
    assert resp.status_code == 200

    data = resp.json()
    assert len(data) == 2
    titles = {p["title"] for p in data}
    assert titles == {"Backend Engineer", "Frontend Engineer"}


def test_get_position_detail(client, manager_headers):
    """GET /api/positions/{id} returns the position with candidate_count=0."""
    create_resp = _create_position(client, manager_headers)
    position_id = create_resp.json()["id"]

    resp = client.get(f"{POSITIONS_URL}/{position_id}", headers=manager_headers)
    assert resp.status_code == 200

    data = resp.json()
    assert data["id"] == position_id
    assert data["title"] == "Software Engineer"
    assert data["candidate_count"] == 0


def test_get_position_not_found(client, manager_headers):
    """GET /api/positions/99999 returns 404."""
    resp = client.get(f"{POSITIONS_URL}/99999", headers=manager_headers)
    assert resp.status_code == 404


def test_update_position_as_manager(client, manager_headers):
    """PUT /api/positions/{id} as manager updates fields correctly."""
    create_resp = _create_position(client, manager_headers)
    position_id = create_resp.json()["id"]

    update_payload = {
        "title": "Senior Software Engineer",
        "department": "Platform",
        "description": "Lead backend architecture.",
        "requirements": "5+ years experience",
    }
    resp = client.put(
        f"{POSITIONS_URL}/{position_id}",
        json=update_payload,
        headers=manager_headers,
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["title"] == "Senior Software Engineer"
    assert data["department"] == "Platform"
    assert data["description"] == "Lead backend architecture."
    assert data["requirements"] == "5+ years experience"
    assert data["id"] == position_id


def test_update_position_as_hr_forbidden(client, hr_headers, manager_headers):
    """PUT /api/positions/{id} as HR user returns 403."""
    create_resp = _create_position(client, manager_headers)
    position_id = create_resp.json()["id"]

    resp = client.put(
        f"{POSITIONS_URL}/{position_id}",
        json={"title": "Nope"},
        headers=hr_headers,
    )
    assert resp.status_code == 403


def test_update_position_status(client, manager_headers):
    """PUT /api/positions/{id} can change status from open to closed."""
    create_resp = _create_position(client, manager_headers)
    position_id = create_resp.json()["id"]
    assert create_resp.json()["status"] == "open"

    resp = client.put(
        f"{POSITIONS_URL}/{position_id}",
        json={"status": "closed"},
        headers=manager_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"


def test_create_position_unauthenticated(client):
    """POST /api/positions without a token returns 403."""
    payload = _make_position_payload()
    resp = client.post(POSITIONS_URL, json=payload)

    assert resp.status_code == 403
