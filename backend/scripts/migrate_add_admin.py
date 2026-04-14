"""Idempotent migration: ensure `must_change_password` column exists and seed a default admin account.

Run via:
    docker-compose exec backend python -m scripts.migrate_add_admin
or:
    cd backend && python -m scripts.migrate_add_admin
"""
from sqlalchemy import inspect, text
from app.database import engine, SessionLocal
from app.models import User
from app.auth import hash_password


DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "Admin@2026"
DEFAULT_ADMIN_DISPLAY = "系统管理员"


def ensure_column():
    insp = inspect(engine)
    existing = {c["name"] for c in insp.get_columns("users")}
    if "must_change_password" in existing:
        print("[OK] column users.must_change_password already present")
        return
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT 0 NOT NULL"))
        conn.commit()
    print("[ADDED] column users.must_change_password")


def ensure_admin():
    db = SessionLocal()
    try:
        admins = db.query(User).filter(User.role == "admin").count()
        if admins > 0:
            print(f"[OK] {admins} admin account(s) already exist")
            return
        user = User(
            username=DEFAULT_ADMIN_USERNAME,
            password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
            role="admin",
            display_name=DEFAULT_ADMIN_DISPLAY,
            must_change_password=True,
        )
        db.add(user)
        db.commit()
        print(
            f"[ADDED] default admin account  username={DEFAULT_ADMIN_USERNAME}  "
            f"password={DEFAULT_ADMIN_PASSWORD}  (flagged for forced change)"
        )
    finally:
        db.close()


if __name__ == "__main__":
    ensure_column()
    ensure_admin()
    print("Migration complete.")
