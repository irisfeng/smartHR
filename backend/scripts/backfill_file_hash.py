"""Idempotent backfill: compute SHA-256 for every Candidate missing a file_hash.

Run via:
    docker compose exec api python -m scripts.backfill_file_hash
or:
    cd backend && python -m scripts.backfill_file_hash

- Skips candidates whose resume_file_path is missing on disk.
- Does not delete or merge anything; only writes file_hash.
- Safe to re-run.
"""
import os
from app.database import SessionLocal
from app.models import Candidate
from app.services.file_service import sha256_file


def main() -> None:
    db = SessionLocal()
    try:
        rows = (
            db.query(Candidate)
            .filter(Candidate.file_hash.is_(None))
            .all()
        )
        total = len(rows)
        filled = 0
        missing = 0
        errors = 0
        for c in rows:
            path = c.resume_file_path or ""
            if not path or not os.path.exists(path):
                missing += 1
                continue
            try:
                c.file_hash = sha256_file(path)
                filled += 1
            except Exception as e:  # noqa: BLE001
                errors += 1
                print(f"[error] id={c.id} path={path}: {e}")
        db.commit()
        print(
            f"Backfill done: scanned={total} filled={filled} "
            f"missing_file={missing} errors={errors}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
