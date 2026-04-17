from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from app.config import settings
from app.database import engine, Base
from app.routers import auth_router, positions_router, upload_router, candidates_router, export_router, users_router

Base.metadata.create_all(bind=engine)

# Lightweight migration: add columns that don't exist yet
_NEW_COLUMNS = [
    ("candidates", "evaluation_result", "VARCHAR(50) DEFAULT ''"),
    ("users", "must_change_password", "BOOLEAN DEFAULT FALSE NOT NULL"),
    ("candidates", "file_hash", "VARCHAR(64)"),
]
_NEW_INDEXES = [
    ("ix_candidates_file_hash", "candidates", "file_hash"),
    ("ix_candidates_pos_hash", "candidates", "job_position_id, file_hash"),
]
with engine.connect() as conn:
    insp = inspect(engine)
    for table, col, col_type in _NEW_COLUMNS:
        existing = {c["name"] for c in insp.get_columns(table)}
        if col not in existing:
            conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {col} {col_type}'))
            conn.commit()
    insp = inspect(engine)
    for idx_name, table, cols in _NEW_INDEXES:
        existing_idx = {i["name"] for i in insp.get_indexes(table)}
        if idx_name not in existing_idx:
            conn.execute(text(f'CREATE INDEX {idx_name} ON {table} ({cols})'))
            conn.commit()

docs_url = "/docs" if settings.env != "prod" else None
redoc_url = "/redoc" if settings.env != "prod" else None

app = FastAPI(title="SmartHR API", docs_url=docs_url, redoc_url=redoc_url)

origins = [o.strip() for o in settings.allowed_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(positions_router.router)
app.include_router(upload_router.router)
app.include_router(candidates_router.router)
app.include_router(export_router.router)
app.include_router(users_router.router)

@app.get("/api/health")
def health():
    return {"status": "ok"}
