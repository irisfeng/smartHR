import os
import zipfile
import uuid
from pathlib import Path
from app.config import settings

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

def extract_zip(zip_path: str, position_id: int) -> list[str]:
    pdf_paths = []
    upload_dir = ensure_upload_dir() / str(position_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            if name.lower().endswith(".pdf") and not name.startswith("__MACOSX"):
                content = zf.read(name)
                base_name = os.path.basename(name)
                unique_name = f"{uuid.uuid4().hex}_{base_name}"
                file_path = upload_dir / unique_name
                file_path.write_bytes(content)
                pdf_paths.append(str(file_path))
    return pdf_paths

def validate_file(filename: str, size: int) -> str | None:
    lower = filename.lower()
    if not (lower.endswith(".pdf") or lower.endswith(".zip")):
        return "Only PDF and ZIP files are allowed"
    if size > settings.max_upload_size_mb * 1024 * 1024:
        return f"File too large (max {settings.max_upload_size_mb}MB)"
    return None
