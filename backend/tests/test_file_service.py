import io
import os
import zipfile

import pytest

from app.services.file_service import (
    extract_zip,
    save_uploaded_file,
    validate_file,
    validate_resume_path,
)


@pytest.fixture
def temp_upload_dir(tmp_path, monkeypatch):
    upload_dir = str(tmp_path / "uploads")
    monkeypatch.setattr("app.config.settings.upload_dir", upload_dir)
    return upload_dir


# ---------- validate_file ----------


def test_validate_file_pdf_valid():
    result = validate_file("resume.pdf", 1024)
    assert result is None


def test_validate_file_zip_valid():
    result = validate_file("resumes.zip", 1024)
    assert result is None


def test_validate_file_invalid_extension():
    result = validate_file("resume.docx", 1024)
    assert result is not None
    assert "Only PDF and ZIP" in result


def test_validate_file_too_large():
    over_limit = 100 * 1024 * 1024 + 1  # 100 MB + 1 byte
    result = validate_file("resume.pdf", over_limit)
    assert result is not None
    assert "too large" in result.lower()


def test_validate_file_case_insensitive():
    assert validate_file("RESUME.PDF", 1024) is None
    assert validate_file("archive.ZIP", 1024) is None
    assert validate_file("file.Pdf", 1024) is None


# ---------- validate_resume_path ----------


def test_validate_resume_path_outside_uploads(temp_upload_dir):
    os.makedirs(temp_upload_dir, exist_ok=True)
    result = validate_resume_path("/etc/passwd")
    assert result is False


def test_validate_resume_path_traversal(temp_upload_dir, tmp_path):
    os.makedirs(temp_upload_dir, exist_ok=True)
    # Create a file outside uploads but try to reach it via traversal
    outside_file = tmp_path / "secret.txt"
    outside_file.write_text("secret")
    traversal_path = os.path.join(temp_upload_dir, "..", "secret.txt")
    result = validate_resume_path(traversal_path)
    assert result is False


def test_validate_resume_path_nonexistent_file(temp_upload_dir):
    os.makedirs(temp_upload_dir, exist_ok=True)
    result = validate_resume_path(os.path.join(temp_upload_dir, "nonexistent.pdf"))
    assert result is False


def test_validate_resume_path_valid(temp_upload_dir):
    os.makedirs(temp_upload_dir, exist_ok=True)
    valid_file = os.path.join(temp_upload_dir, "resume.pdf")
    with open(valid_file, "wb") as f:
        f.write(b"%PDF-1.4 fake content")
    result = validate_resume_path(valid_file)
    assert result is True


# ---------- save_uploaded_file ----------


def test_save_uploaded_file(temp_upload_dir):
    content = b"%PDF-1.4 test content"
    original_name = "my_resume.pdf"
    position_id = 42

    path = save_uploaded_file(content, original_name, position_id)

    assert os.path.isfile(path)
    assert path.startswith(temp_upload_dir)
    assert str(position_id) in path
    assert original_name in os.path.basename(path)

    with open(path, "rb") as f:
        assert f.read() == content


# ---------- extract_zip ----------


def _make_zip(files: dict[str, bytes]) -> bytes:
    """Create an in-memory ZIP file from a dict of {name: content}."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()


def test_extract_zip_basic(temp_upload_dir, tmp_path):
    pdf_content = b"%PDF-1.4 fake pdf"
    zip_bytes = _make_zip({"candidate.pdf": pdf_content})
    zip_path = str(tmp_path / "test.zip")
    with open(zip_path, "wb") as f:
        f.write(zip_bytes)

    entries = extract_zip(zip_path, position_id=1)

    assert len(entries) == 1
    path, h = entries[0]
    assert path.endswith(".pdf")
    assert len(h) == 64
    with open(path, "rb") as f:
        assert f.read() == pdf_content


def test_extract_zip_skips_non_pdf(temp_upload_dir, tmp_path):
    zip_bytes = _make_zip({
        "resume.pdf": b"%PDF-1.4 content",
        "notes.txt": b"some notes",
        "image.png": b"\x89PNG fake",
    })
    zip_path = str(tmp_path / "mixed.zip")
    with open(zip_path, "wb") as f:
        f.write(zip_bytes)

    entries = extract_zip(zip_path, position_id=2)

    assert len(entries) == 1
    assert all(p.endswith(".pdf") for p, _ in entries)


def test_extract_zip_skips_macosx(temp_upload_dir, tmp_path):
    zip_bytes = _make_zip({
        "resume.pdf": b"%PDF-1.4 content",
        "__MACOSX/._resume.pdf": b"mac metadata",
        "__MACOSX/hidden.pdf": b"more mac junk",
    })
    zip_path = str(tmp_path / "macosx.zip")
    with open(zip_path, "wb") as f:
        f.write(zip_bytes)

    entries = extract_zip(zip_path, position_id=3)

    assert len(entries) == 1
    assert "MACOSX" not in entries[0][0]
