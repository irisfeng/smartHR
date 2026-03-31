"""Tests for the candidates API endpoints."""

import pytest
from app.models import JobPosition, Candidate


def _create_position_with_candidates(db, manager_user, count=3):
    """Helper: create a job position with `count` candidates."""
    pos = JobPosition(
        title="Test", department="Dev", description="JD", created_by=manager_user.id
    )
    db.add(pos)
    db.commit()
    db.refresh(pos)
    candidates = []
    for i in range(count):
        c = Candidate(
            job_position_id=pos.id,
            resume_file_path=f"uploads/{pos.id}/test_{i}.pdf",
            name=f"Candidate {i}",
            age=25 + i,
            education=["本科", "硕士", "博士"][i % 3],
            match_score=80 - i * 10,
            ai_recommendation=["推荐", "待定", "不推荐"][i % 3],
            sequence_no=i + 1,
            status="completed",
        )
        db.add(c)
        candidates.append(c)
    db.commit()
    for c in candidates:
        db.refresh(c)
    return pos, candidates


# ── List candidates ──────────────────────────────────────────────


def test_list_candidates_empty(client, db, manager_user, manager_headers):
    """GET returns an empty list when the position has no candidates."""
    pos = JobPosition(
        title="Empty", department="Dev", description="JD", created_by=manager_user.id
    )
    db.add(pos)
    db.commit()
    db.refresh(pos)

    resp = client.get(
        f"/api/positions/{pos.id}/candidates", headers=manager_headers
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_candidates(client, db, manager_user, manager_headers):
    """GET returns all candidates belonging to the position."""
    pos, candidates = _create_position_with_candidates(db, manager_user, count=3)

    resp = client.get(
        f"/api/positions/{pos.id}/candidates", headers=manager_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    returned_ids = {c["id"] for c in data}
    expected_ids = {c.id for c in candidates}
    assert returned_ids == expected_ids


def test_list_candidates_filter_by_recommendation(
    client, db, manager_user, manager_headers
):
    """Filtering by ai_recommendation returns only matching candidates."""
    pos, candidates = _create_position_with_candidates(db, manager_user, count=3)

    resp = client.get(
        f"/api/positions/{pos.id}/candidates",
        params={"recommendation": "推荐"},
        headers=manager_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["ai_recommendation"] == "推荐"
    assert data[0]["id"] == candidates[0].id


def test_list_candidates_filter_by_education(
    client, db, manager_user, manager_headers
):
    """Filtering by education returns only matching candidates."""
    pos, candidates = _create_position_with_candidates(db, manager_user, count=3)

    resp = client.get(
        f"/api/positions/{pos.id}/candidates",
        params={"education": "硕士"},
        headers=manager_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["education"] == "硕士"
    assert data[0]["id"] == candidates[1].id


def test_list_candidates_sort_by_age_asc(client, db, manager_user, manager_headers):
    """Sorting by age ascending returns youngest first."""
    pos, candidates = _create_position_with_candidates(db, manager_user, count=3)

    resp = client.get(
        f"/api/positions/{pos.id}/candidates",
        params={"sort_by": "age", "sort_order": "asc"},
        headers=manager_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    ages = [c["age"] for c in data]
    assert ages == sorted(ages)


def test_list_candidates_sort_by_match_score_desc(
    client, db, manager_user, manager_headers
):
    """Default sort (match_score desc) returns highest score first."""
    pos, candidates = _create_position_with_candidates(db, manager_user, count=3)

    resp = client.get(
        f"/api/positions/{pos.id}/candidates", headers=manager_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    scores = [c["match_score"] for c in data]
    assert scores == sorted(scores, reverse=True)


# ── Candidate detail ─────────────────────────────────────────────


def test_get_candidate_detail(client, db, manager_user, manager_headers):
    """GET /api/candidates/{id} returns the full detail response."""
    pos, candidates = _create_position_with_candidates(db, manager_user, count=1)
    cid = candidates[0].id

    resp = client.get(f"/api/candidates/{cid}", headers=manager_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == cid
    assert data["name"] == "Candidate 0"
    assert data["age"] == 25
    assert data["education"] == "本科"
    assert data["match_score"] == 80
    # Detail-specific field should be present
    assert "parsed_text" in data
    assert "resume_file_path" in data


def test_get_candidate_not_found(client, manager_headers):
    """GET /api/candidates/{id} returns 404 for non-existent candidate."""
    resp = client.get("/api/candidates/99999", headers=manager_headers)
    assert resp.status_code == 404


# ── Update candidate ─────────────────────────────────────────────


def test_update_candidate(client, db, manager_user, manager_headers):
    """PATCH /api/candidates/{id} updates provided fields."""
    pos, candidates = _create_position_with_candidates(db, manager_user, count=1)
    cid = candidates[0].id

    patch_body = {
        "name": "Updated Name",
        "age": 30,
        "phone": "13800138000",
        "screening_result": "通过",
    }
    resp = client.patch(
        f"/api/candidates/{cid}", json=patch_body, headers=manager_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated Name"
    assert data["age"] == 30
    assert data["phone"] == "13800138000"
    assert data["screening_result"] == "通过"
    # Unchanged field should remain the same
    assert data["education"] == "本科"


def test_update_candidate_not_found(client, manager_headers):
    """PATCH /api/candidates/{id} returns 404 for non-existent candidate."""
    resp = client.patch(
        "/api/candidates/99999",
        json={"name": "Ghost"},
        headers=manager_headers,
    )
    assert resp.status_code == 404


# ── Authentication ───────────────────────────────────────────────


def test_list_candidates_unauthenticated(client, db, manager_user):
    """Requests without auth credentials are rejected with 403."""
    pos, _ = _create_position_with_candidates(db, manager_user, count=1)

    resp = client.get(f"/api/positions/{pos.id}/candidates")
    assert resp.status_code == 403
