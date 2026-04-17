"""Dedup tests for upload flow (Layer 1: SHA-256 file-hash dedup)."""
import io
import zipfile
from unittest.mock import patch

import pytest

from app.models import Candidate, JobPosition
from app.services.file_service import extract_zip, sha256_bytes


@pytest.fixture
def temp_upload_dir(tmp_path, monkeypatch):
    upload_dir = str(tmp_path / "uploads")
    monkeypatch.setattr("app.config.settings.upload_dir", upload_dir)
    return upload_dir


def _zip_bytes(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()


def _make_position(db, hr_user, title: str = "Dev") -> JobPosition:
    pos = JobPosition(
        title=title,
        department="eng",
        description="d",
        requirements="r",
        created_by=hr_user.id,
    )
    db.add(pos)
    db.commit()
    db.refresh(pos)
    return pos


def _upload(client, headers, position_id: int, filename: str, content: bytes):
    """Post a single file to the upload endpoint. Skips the background pipeline."""
    with patch("app.routers.upload_router.run_pipeline_background"):
        return client.post(
            f"/api/positions/{position_id}/upload",
            files={"file": (filename, content, "application/pdf")},
            headers=headers,
        )


# ---------- extract_zip intra-zip dedup ----------


def test_extract_zip_dedups_identical_pdfs(temp_upload_dir, tmp_path):
    """Same byte content twice in one zip -> only one entry kept."""
    pdf = b"%PDF-1.4 same content"
    zip_bytes = _zip_bytes({"a.pdf": pdf, "dir/b.pdf": pdf})
    zp = str(tmp_path / "dup.zip")
    with open(zp, "wb") as f:
        f.write(zip_bytes)

    entries = extract_zip(zp, position_id=42)
    assert len(entries) == 1
    _, h = entries[0]
    assert h == sha256_bytes(pdf)


def test_extract_zip_keeps_distinct_pdfs(temp_upload_dir, tmp_path):
    zip_bytes = _zip_bytes({"a.pdf": b"%PDF one", "b.pdf": b"%PDF two"})
    zp = str(tmp_path / "two.zip")
    with open(zp, "wb") as f:
        f.write(zip_bytes)

    entries = extract_zip(zp, position_id=43)
    assert len(entries) == 2
    assert len({h for _, h in entries}) == 2


# ---------- upload endpoint dedup ----------


def test_upload_same_file_twice_skips_second(client, hr_headers, hr_user, db, temp_upload_dir):
    pos = _make_position(db, hr_user)
    pdf = b"%PDF-1.4 one candidate"

    r1 = _upload(client, hr_headers, pos.id, "resume.pdf", pdf)
    assert r1.status_code == 200, r1.text
    assert r1.json()["imported_count"] == 1
    assert r1.json()["skipped_count"] == 0

    r2 = _upload(client, hr_headers, pos.id, "resume.pdf", pdf)
    assert r2.status_code == 200, r2.text
    assert r2.json()["imported_count"] == 0
    assert r2.json()["skipped_count"] == 1
    assert r2.json()["skipped_reason"]

    # Only one candidate row should exist for this position
    assert db.query(Candidate).filter(Candidate.job_position_id == pos.id).count() == 1


def test_upload_same_file_different_positions_both_imported(
    client, hr_headers, hr_user, db, temp_upload_dir
):
    pos_a = _make_position(db, hr_user, "A")
    pos_b = _make_position(db, hr_user, "B")
    pdf = b"%PDF-1.4 cross-position"

    r1 = _upload(client, hr_headers, pos_a.id, "r.pdf", pdf)
    r2 = _upload(client, hr_headers, pos_b.id, "r.pdf", pdf)
    assert r1.json()["imported_count"] == 1
    assert r2.json()["imported_count"] == 1
    assert db.query(Candidate).count() == 2


def test_upload_zip_with_intra_and_db_duplicates(
    client, hr_headers, hr_user, db, temp_upload_dir
):
    pos = _make_position(db, hr_user)
    pdf_a = b"%PDF-1.4 A"
    pdf_b = b"%PDF-1.4 B"

    # First, upload A standalone -> in DB
    _upload(client, hr_headers, pos.id, "a.pdf", pdf_a)

    # Now upload a zip containing: A (dup in DB), B (new), B again (intra-zip dup)
    zip_bytes = _zip_bytes({"a.pdf": pdf_a, "b.pdf": pdf_b, "copy/b.pdf": pdf_b})
    r = _upload(client, hr_headers, pos.id, "bundle.zip", zip_bytes)

    data = r.json()
    # Only B should be imported; A skipped (DB) and second B skipped (intra-zip)
    assert data["imported_count"] == 1
    assert data["skipped_count"] == 1  # A skipped by DB dedup; intra-zip B vanishes before DB check
    assert db.query(Candidate).filter(Candidate.job_position_id == pos.id).count() == 2
