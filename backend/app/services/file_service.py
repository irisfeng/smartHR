import os
import hashlib
import zipfile
import uuid
from pathlib import Path
from app.config import settings


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def ensure_upload_dir() -> Path:
    path = Path(settings.upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path

def save_uploaded_file(content: bytes, original_name: str, position_id: int) -> str:
    upload_dir = ensure_upload_dir() / str(position_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}_{original_name}"
    file_path = upload_dir / unique_name
    file_path.write_bytes(content)
    return str(file_path)

def extract_zip(zip_path: str, position_id: int) -> list[tuple[str, str]]:
    """Extract PDFs from a zip. Returns list of (file_path, sha256_hash).
    Intra-zip duplicates (same hash) are skipped.
    """
    pdf_entries: list[tuple[str, str]] = []
    seen_hashes: set[str] = set()
    upload_dir = ensure_upload_dir() / str(position_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    max_single_file_mb = 50
    max_total_files = 200
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            if not info.filename.lower().endswith(".pdf"):
                continue
            if info.filename.startswith("__MACOSX"):
                continue
            base_name = os.path.basename(info.filename)
            if not base_name:
                continue
            if info.file_size > max_single_file_mb * 1024 * 1024:
                continue
            content = zf.read(info.filename)
            h = sha256_bytes(content)
            if h in seen_hashes:
                continue
            seen_hashes.add(h)
            unique_name = f"{uuid.uuid4().hex}_{base_name}"
            file_path = upload_dir / unique_name
            file_path.write_bytes(content)
            pdf_entries.append((str(file_path), h))
            if len(pdf_entries) >= max_total_files:
                break
    return pdf_entries

def validate_file(filename: str, size: int) -> str | None:
    lower = filename.lower()
    if not (lower.endswith(".pdf") or lower.endswith(".zip")):
        return "Only PDF and ZIP files are allowed"
    if size > settings.max_upload_size_mb * 1024 * 1024:
        return f"File too large (max {settings.max_upload_size_mb}MB)"
    return None

def validate_resume_path(file_path: str) -> bool:
    """Ensure the file path is within the upload directory."""
    upload_root = Path(settings.upload_dir).resolve()
    resolved = Path(file_path).resolve()
    try:
        resolved.relative_to(upload_root)
    except ValueError:
        return False
    return resolved.exists() and resolved.is_file()
