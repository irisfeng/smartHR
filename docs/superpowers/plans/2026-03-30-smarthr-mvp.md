# SmartHR MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an internal HR web app where HR uploads resume ZIPs/PDFs, AI screens them against job descriptions, and results are tracked in a table matching the company's Excel template.

**Architecture:** FastAPI backend handles auth, file upload, AI pipeline (MinerU + DeepSeek/Qwen), and Excel export. React + Ant Design frontend provides the UI. SQLite database via SQLAlchemy. JWT auth with two roles (HR, Manager).

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, SQLite, React 18, Vite, TypeScript, Ant Design 5, openpyxl, MinerU API, DeepSeek API

---

## File Structure

```
smartHR/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app, CORS, router mounting
│   │   ├── config.py                # Settings (env vars, secrets)
│   │   ├── database.py              # SQLAlchemy engine, session, Base
│   │   ├── models.py                # All SQLAlchemy models
│   │   ├── schemas.py               # Pydantic request/response schemas
│   │   ├── auth.py                  # JWT creation, password hashing, dependencies
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── auth_router.py       # Login, refresh, me
│   │   │   ├── positions_router.py  # CRUD for job positions
│   │   │   ├── candidates_router.py # List, detail, update, resume serve
│   │   │   ├── upload_router.py     # Upload ZIP/PDF, batch status
│   │   │   ├── export_router.py     # Excel export
│   │   │   └── users_router.py      # User management
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── file_service.py      # ZIP extraction, file validation
│   │       ├── mineru_service.py    # MinerU API client
│   │       ├── ai_service.py        # DeepSeek/Qwen screening
│   │       ├── pipeline_service.py  # Orchestrates parse → screen → save
│   │       └── export_service.py    # Excel generation with openpyxl
│   ├── seed.py                      # Create initial admin user
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── main.tsx                 # App entry
│   │   ├── App.tsx                  # Router setup
│   │   ├── api.ts                   # Axios instance with JWT interceptor
│   │   ├── store/
│   │   │   └── authStore.ts         # Zustand auth state
│   │   ├── components/
│   │   │   ├── AppLayout.tsx        # Sidebar + header layout
│   │   │   └── ProtectedRoute.tsx   # Auth guard
│   │   └── pages/
│   │       ├── LoginPage.tsx
│   │       ├── PositionsPage.tsx
│   │       ├── UploadPage.tsx
│   │       ├── CandidatesPage.tsx
│   │       ├── CandidateDetail.tsx
│   │       └── UsersPage.tsx
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
├── uploads/                         # Uploaded PDFs (gitignored)
├── template.xlsx                    # Copy of the provided Excel template
└── .gitignore
```

---

### Task 1: Project Scaffolding & Database

**Files:**
- Create: `backend/app/__init__.py`, `backend/app/main.py`, `backend/app/config.py`, `backend/app/database.py`, `backend/app/models.py`, `backend/requirements.txt`, `backend/.env.example`, `.gitignore`, `template.xlsx`

- [ ] **Step 1: Create .gitignore**

```gitignore
# Python
__pycache__/
*.pyc
.env
*.db

# Node
node_modules/
dist/

# Uploads
uploads/

# IDE
.vscode/
.idea/

# Superpowers
.superpowers/
```

- [ ] **Step 2: Copy template Excel to project root**

```bash
cp /Users/tony/Documents/模板.xlsx /Users/tony/Documents/GitHub/smartHR/template.xlsx
```

- [ ] **Step 3: Create backend requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
sqlalchemy==2.0.35
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
pydantic-settings==2.5.0
httpx==0.27.0
openpyxl==3.1.5
python-dotenv==1.0.1
```

- [ ] **Step 4: Create backend/.env.example**

```
SECRET_KEY=change-me-to-a-random-string
MINERU_API_URL=https://your-mineru-endpoint/api
MINERU_API_KEY=your-mineru-key
AI_API_URL=https://api.deepseek.com/v1
AI_API_KEY=your-deepseek-key
AI_MODEL=deepseek-chat
```

- [ ] **Step 5: Create config.py**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    mineru_api_url: str = ""
    mineru_api_key: str = ""

    ai_api_url: str = "https://api.deepseek.com/v1"
    ai_api_key: str = ""
    ai_model: str = "deepseek-chat"

    upload_dir: str = "uploads"
    max_upload_size_mb: int = 100

    class Config:
        env_file = ".env"

settings = Settings()
```

- [ ] **Step 6: Create database.py**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

engine = create_engine("sqlite:///smarthr.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 7: Create models.py**

```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # "hr" or "manager"
    display_name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class JobPosition(Base):
    __tablename__ = "job_positions"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    department = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    requirements = Column(Text, default="")
    status = Column(String(20), default="open")  # "open" or "closed"
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    candidates = relationship("Candidate", back_populates="position")

class Candidate(Base):
    __tablename__ = "candidates"
    id = Column(Integer, primary_key=True, index=True)
    job_position_id = Column(Integer, ForeignKey("job_positions.id"), nullable=False)
    upload_batch_id = Column(Integer, ForeignKey("upload_batches.id"), nullable=True)
    resume_file_path = Column(String(500), nullable=False)
    parsed_text = Column(Text, default="")
    # Template fields
    sequence_no = Column(Integer, nullable=True)
    recommend_date = Column(String(20), default="")
    recommend_channel = Column(String(50), default="")
    name = Column(String(50), default="")
    id_number = Column(String(20), default="")
    age = Column(Integer, nullable=True)
    gender = Column(String(10), default="")
    phone = Column(String(20), default="")
    education = Column(String(20), default="")
    school = Column(String(100), default="")
    major = Column(String(100), default="")
    screening_date = Column(String(20), default="")
    leader_screening = Column(String(50), default="")
    screening_result = Column(String(50), default="")
    interview_date = Column(String(20), default="")
    interview_time = Column(String(20), default="")
    interview_note = Column(Text, default="")
    first_interview_result = Column(String(50), default="")
    first_interview_note = Column(Text, default="")
    second_interview_invite = Column(String(50), default="")
    second_interview_result = Column(String(50), default="")
    second_interview_note = Column(Text, default="")
    project_transfer = Column(String(100), default="")
    # AI fields
    match_score = Column(Float, nullable=True)
    ai_recommendation = Column(String(20), default="")
    ai_summary = Column(Text, default="")
    ai_screening_result = Column(JSON, nullable=True)
    # Processing status
    status = Column(String(20), default="pending")  # pending, parsing, screening, completed, failed
    error_message = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    position = relationship("JobPosition", back_populates="candidates")

class UploadBatch(Base):
    __tablename__ = "upload_batches"
    id = Column(Integer, primary_key=True, index=True)
    job_position_id = Column(Integer, ForeignKey("job_positions.id"), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_count = Column(Integer, default=0)
    processed_count = Column(Integer, default=0)
    status = Column(String(20), default="processing")  # processing, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 8: Create main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SmartHR API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 9: Create empty __init__.py files**

Create empty files: `backend/app/__init__.py`, `backend/app/routers/__init__.py`, `backend/app/services/__init__.py`

- [ ] **Step 10: Install dependencies and verify server starts**

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/api/health` — expect `{"status": "ok"}`

- [ ] **Step 11: Commit**

```bash
git init
git add .gitignore template.xlsx backend/
git commit -m "feat: project scaffolding with FastAPI, SQLAlchemy models, and config"
```

---

### Task 2: Authentication (Backend)

**Files:**
- Create: `backend/app/auth.py`, `backend/app/schemas.py`, `backend/app/routers/auth_router.py`, `backend/seed.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create schemas.py**

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# Auth
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    refresh_token: str

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    display_name: str
    created_at: datetime
    class Config:
        from_attributes = True

# Job Positions
class PositionCreate(BaseModel):
    title: str
    department: str
    description: str
    requirements: str = ""

class PositionUpdate(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    status: Optional[str] = None

class PositionResponse(BaseModel):
    id: int
    title: str
    department: str
    description: str
    requirements: str
    status: str
    created_by: int
    created_at: datetime
    updated_at: datetime
    candidate_count: int = 0
    class Config:
        from_attributes = True

# Candidates
class CandidateUpdate(BaseModel):
    recommend_date: Optional[str] = None
    recommend_channel: Optional[str] = None
    screening_date: Optional[str] = None
    leader_screening: Optional[str] = None
    screening_result: Optional[str] = None
    interview_date: Optional[str] = None
    interview_time: Optional[str] = None
    interview_note: Optional[str] = None
    first_interview_result: Optional[str] = None
    first_interview_note: Optional[str] = None
    second_interview_invite: Optional[str] = None
    second_interview_result: Optional[str] = None
    second_interview_note: Optional[str] = None
    project_transfer: Optional[str] = None

class CandidateResponse(BaseModel):
    id: int
    job_position_id: int
    sequence_no: Optional[int]
    name: str
    gender: str
    age: Optional[int]
    phone: str
    education: str
    school: str
    major: str
    match_score: Optional[float]
    ai_recommendation: str
    ai_summary: str
    screening_result: str
    first_interview_result: str
    second_interview_result: str
    status: str
    recommend_date: str
    recommend_channel: str
    screening_date: str
    leader_screening: str
    interview_date: str
    interview_time: str
    interview_note: str
    first_interview_note: str
    second_interview_invite: str
    second_interview_note: str
    project_transfer: str
    created_at: datetime
    class Config:
        from_attributes = True

class CandidateDetailResponse(CandidateResponse):
    id_number: str
    parsed_text: str
    ai_screening_result: Optional[dict]
    resume_file_path: str
    error_message: str

# Upload
class UploadBatchResponse(BaseModel):
    id: int
    job_position_id: int
    file_name: str
    file_count: int
    processed_count: int
    status: str
    created_at: datetime
    class Config:
        from_attributes = True

# Users
class UserCreate(BaseModel):
    username: str
    password: str
    role: str
    display_name: str
```

- [ ] **Step 2: Create auth.py**

```python
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

def create_access_token(user_id: int, role: str) -> str:
    return create_token(
        {"sub": str(user_id), "role": role, "type": "access"},
        timedelta(minutes=settings.access_token_expire_minutes),
    )

def create_refresh_token(user_id: int) -> str:
    return create_token(
        {"sub": str(user_id), "type": "refresh"},
        timedelta(days=settings.refresh_token_expire_days),
    )

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def require_role(*roles: str):
    def dependency(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return dependency
```

- [ ] **Step 3: Create auth_router.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, TokenResponse, RefreshRequest, UserResponse
from app.auth import (
    verify_password, create_access_token, create_refresh_token, get_current_user,
)
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id),
    )

@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(body.refresh_token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id),
    )

@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user
```

- [ ] **Step 4: Create seed.py**

```python
from app.database import engine, SessionLocal, Base
from app.models import User
from app.auth import hash_password

Base.metadata.create_all(bind=engine)
db = SessionLocal()

if not db.query(User).filter(User.username == "admin").first():
    admin = User(
        username="admin",
        password_hash=hash_password("admin123"),
        role="manager",
        display_name="管理员",
    )
    db.add(admin)

    hr = User(
        username="hr",
        password_hash=hash_password("hr123"),
        role="hr",
        display_name="HR专员",
    )
    db.add(hr)
    db.commit()
    print("Seeded admin and hr users")
else:
    print("Users already exist")

db.close()
```

- [ ] **Step 5: Register auth router in main.py**

Add to `backend/app/main.py` after the CORS middleware:

```python
from app.routers import auth_router

app.include_router(auth_router.router)
```

- [ ] **Step 6: Run seed and test login**

```bash
cd backend
python -m app.seed
# Test login:
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

Expect a JSON response with `access_token` and `refresh_token`.

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat: auth system with JWT login, refresh, seed users"
```

---

### Task 3: Job Positions API

**Files:**
- Create: `backend/app/routers/positions_router.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create positions_router.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User, JobPosition, Candidate
from app.schemas import PositionCreate, PositionUpdate, PositionResponse
from app.auth import get_current_user, require_role

router = APIRouter(prefix="/api/positions", tags=["positions"])

@router.get("", response_model=List[PositionResponse])
def list_positions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    positions = db.query(JobPosition).order_by(JobPosition.created_at.desc()).all()
    result = []
    for p in positions:
        count = db.query(Candidate).filter(Candidate.job_position_id == p.id).count()
        resp = PositionResponse.model_validate(p)
        resp.candidate_count = count
        result.append(resp)
    return result

@router.post("", response_model=PositionResponse)
def create_position(
    body: PositionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager")),
):
    position = JobPosition(**body.model_dump(), created_by=user.id)
    db.add(position)
    db.commit()
    db.refresh(position)
    resp = PositionResponse.model_validate(position)
    resp.candidate_count = 0
    return resp

@router.get("/{position_id}", response_model=PositionResponse)
def get_position(position_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    position = db.query(JobPosition).filter(JobPosition.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    count = db.query(Candidate).filter(Candidate.job_position_id == position.id).count()
    resp = PositionResponse.model_validate(position)
    resp.candidate_count = count
    return resp

@router.put("/{position_id}", response_model=PositionResponse)
def update_position(
    position_id: int,
    body: PositionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager")),
):
    position = db.query(JobPosition).filter(JobPosition.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(position, key, value)
    db.commit()
    db.refresh(position)
    count = db.query(Candidate).filter(Candidate.job_position_id == position.id).count()
    resp = PositionResponse.model_validate(position)
    resp.candidate_count = count
    return resp
```

- [ ] **Step 2: Register router in main.py**

Add to `backend/app/main.py`:

```python
from app.routers import auth_router, positions_router

app.include_router(auth_router.router)
app.include_router(positions_router.router)
```

- [ ] **Step 3: Test positions API**

```bash
# Get token first
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Create position
curl -X POST http://localhost:8000/api/positions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"高级Java开发","department":"技术部","description":"需要5年Java经验","requirements":"本科以上，Java/Spring"}'

# List positions
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/positions
```

Expect: position created and listed with `candidate_count: 0`.

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/positions_router.py backend/app/main.py
git commit -m "feat: job positions CRUD API"
```

---

### Task 4: File Upload & AI Pipeline (Backend)

**Files:**
- Create: `backend/app/services/file_service.py`, `backend/app/services/mineru_service.py`, `backend/app/services/ai_service.py`, `backend/app/services/pipeline_service.py`, `backend/app/routers/upload_router.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create file_service.py**

```python
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
```

- [ ] **Step 2: Create mineru_service.py**

```python
import httpx
from app.config import settings

async def parse_pdf(file_path: str) -> str:
    if not settings.mineru_api_url or not settings.mineru_api_key:
        # Fallback: return empty string so pipeline can still test without MinerU
        return ""

    async with httpx.AsyncClient(timeout=120.0) as client:
        with open(file_path, "rb") as f:
            response = await client.post(
                f"{settings.mineru_api_url}/parse",
                headers={"Authorization": f"Bearer {settings.mineru_api_key}"},
                files={"file": (file_path.split("/")[-1], f, "application/pdf")},
            )
        response.raise_for_status()
        data = response.json()
        # MinerU returns parsed text in various formats; extract the main text content
        return data.get("text", data.get("content", str(data)))
```

- [ ] **Step 3: Create ai_service.py**

```python
import json
import httpx
from app.config import settings

SCREENING_PROMPT = """你是一个专业的HR简历筛选助手。请根据以下职位描述(JD)和候选人简历内容，进行简历分析和初筛。

## 职位描述
{jd}

## 简历内容
{resume_text}

## 要求
请以JSON格式返回分析结果，包含以下字段：
- name: 姓名（字符串）
- gender: 性别（字符串）
- age: 年龄（整数或null）
- phone: 电话（字符串）
- id_number: 身份证号（字符串或null）
- education: 最高学历（字符串）
- school: 毕业学校（字符串）
- major: 专业（字符串）
- match_score: 与JD的匹配度（0-100整数）
- recommendation: 推荐等级（"推荐"/"待定"/"不推荐"）
- summary: 筛选评语（简述匹配原因，100字以内）
- strengths: 优势（字符串数组）
- concerns: 顾虑（字符串数组）

请只返回JSON，不要添加其他内容。"""

async def screen_resume(resume_text: str, jd: str) -> dict:
    if not settings.ai_api_key:
        return {
            "name": "", "gender": "", "age": None, "phone": "",
            "id_number": None, "education": "", "school": "", "major": "",
            "match_score": 0, "recommendation": "待定",
            "summary": "AI服务未配置", "strengths": [], "concerns": [],
        }

    prompt = SCREENING_PROMPT.format(jd=jd, resume_text=resume_text)

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.ai_api_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.ai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.ai_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)
```

- [ ] **Step 4: Create pipeline_service.py**

```python
from sqlalchemy.orm import Session
from app.models import Candidate, UploadBatch, JobPosition
from app.services.mineru_service import parse_pdf
from app.services.ai_service import screen_resume

async def process_candidate(candidate_id: int, db: Session):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        return

    position = db.query(JobPosition).filter(JobPosition.id == candidate.job_position_id).first()
    jd = f"{position.title}\n{position.description}\n{position.requirements}" if position else ""

    try:
        # Step 1: Parse PDF
        candidate.status = "parsing"
        db.commit()
        parsed_text = await parse_pdf(candidate.resume_file_path)
        candidate.parsed_text = parsed_text

        # Step 2: AI Screening
        candidate.status = "screening"
        db.commit()
        result = await screen_resume(parsed_text, jd)
        candidate.ai_screening_result = result

        # Step 3: Fill fields from AI result
        candidate.name = result.get("name", "")
        candidate.gender = result.get("gender", "")
        candidate.age = result.get("age")
        candidate.phone = result.get("phone", "")
        candidate.id_number = result.get("id_number", "")
        candidate.education = result.get("education", "")
        candidate.school = result.get("school", "")
        candidate.major = result.get("major", "")
        candidate.match_score = result.get("match_score", 0)
        candidate.ai_recommendation = result.get("recommendation", "待定")
        candidate.ai_summary = result.get("summary", "")
        candidate.leader_screening = result.get("recommendation", "")
        candidate.status = "completed"
        db.commit()

    except Exception as e:
        candidate.status = "failed"
        candidate.error_message = str(e)
        db.commit()

async def process_batch(batch_id: int, db: Session):
    batch = db.query(UploadBatch).filter(UploadBatch.id == batch_id).first()
    if not batch:
        return

    candidates = db.query(Candidate).filter(Candidate.upload_batch_id == batch_id).all()
    for candidate in candidates:
        await process_candidate(candidate.id, db)
        batch.processed_count += 1
        db.commit()

    all_done = all(c.status in ("completed", "failed") for c in candidates)
    batch.status = "completed" if all_done else "failed"
    db.commit()
```

- [ ] **Step 5: Create upload_router.py**

```python
import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db, SessionLocal
from app.models import User, JobPosition, Candidate, UploadBatch
from app.schemas import UploadBatchResponse
from app.auth import get_current_user, require_role
from app.services.file_service import save_uploaded_file, extract_zip, validate_file
from app.services.pipeline_service import process_batch

router = APIRouter(prefix="/api", tags=["upload"])

async def run_pipeline_background(batch_id: int):
    db = SessionLocal()
    try:
        await process_batch(batch_id, db)
    finally:
        db.close()

@router.post("/positions/{position_id}/upload", response_model=UploadBatchResponse)
async def upload_resumes(
    position_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("hr")),
):
    position = db.query(JobPosition).filter(JobPosition.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    content = await file.read()
    error = validate_file(file.filename, len(content))
    if error:
        raise HTTPException(status_code=400, detail=error)

    saved_path = save_uploaded_file(content, file.filename, position_id)

    # Determine PDF paths
    if file.filename.lower().endswith(".zip"):
        pdf_paths = extract_zip(saved_path, position_id)
    else:
        pdf_paths = [saved_path]

    # Create batch
    batch = UploadBatch(
        job_position_id=position_id,
        uploaded_by=user.id,
        file_name=file.filename,
        file_count=len(pdf_paths),
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    # Create candidate records
    existing_count = db.query(Candidate).filter(Candidate.job_position_id == position_id).count()
    for i, pdf_path in enumerate(pdf_paths):
        candidate = Candidate(
            job_position_id=position_id,
            upload_batch_id=batch.id,
            resume_file_path=pdf_path,
            sequence_no=existing_count + i + 1,
            recommend_date=datetime.now().strftime("%Y-%m-%d"),
            recommend_channel="系统上传",
            status="pending",
        )
        db.add(candidate)
    db.commit()

    # Run AI pipeline in background
    background_tasks.add_task(run_pipeline_background, batch.id)

    return batch

@router.get("/upload-batches/{batch_id}/status", response_model=UploadBatchResponse)
def get_batch_status(
    batch_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    batch = db.query(UploadBatch).filter(UploadBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return batch
```

- [ ] **Step 6: Register upload router in main.py**

Add to `backend/app/main.py`:

```python
from app.routers import auth_router, positions_router, upload_router

app.include_router(auth_router.router)
app.include_router(positions_router.router)
app.include_router(upload_router.router)
```

- [ ] **Step 7: Create uploads directory and test**

```bash
mkdir -p uploads
# Test with a PDF upload (need a real PDF to test properly)
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/ backend/app/routers/upload_router.py backend/app/main.py
git commit -m "feat: file upload, MinerU parsing, AI screening pipeline"
```

---

### Task 5: Candidates & Export API

**Files:**
- Create: `backend/app/routers/candidates_router.py`, `backend/app/routers/export_router.py`, `backend/app/routers/users_router.py`, `backend/app/services/export_service.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create candidates_router.py**

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import User, Candidate
from app.schemas import CandidateResponse, CandidateDetailResponse, CandidateUpdate
from app.auth import get_current_user

router = APIRouter(tags=["candidates"])

@router.get("/api/positions/{position_id}/candidates", response_model=List[CandidateResponse])
def list_candidates(
    position_id: int,
    recommendation: Optional[str] = Query(None),
    education: Optional[str] = Query(None),
    sort_by: str = Query("match_score"),
    sort_order: str = Query("desc"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Candidate).filter(Candidate.job_position_id == position_id)
    if recommendation:
        query = query.filter(Candidate.ai_recommendation == recommendation)
    if education:
        query = query.filter(Candidate.education == education)

    sort_col = getattr(Candidate, sort_by, Candidate.match_score)
    if sort_order == "desc":
        query = query.order_by(sort_col.desc().nulls_last())
    else:
        query = query.order_by(sort_col.asc().nulls_last())

    return query.all()

@router.get("/api/candidates/{candidate_id}", response_model=CandidateDetailResponse)
def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate

@router.patch("/api/candidates/{candidate_id}", response_model=CandidateResponse)
def update_candidate(
    candidate_id: int,
    body: CandidateUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(candidate, key, value)
    db.commit()
    db.refresh(candidate)
    return candidate

@router.get("/api/candidates/{candidate_id}/resume")
def get_resume(
    candidate_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return FileResponse(candidate.resume_file_path, media_type="application/pdf")
```

- [ ] **Step 2: Create export_service.py**

```python
from openpyxl import load_workbook
from openpyxl.styles import Alignment
from sqlalchemy.orm import Session
from app.models import Candidate
import tempfile
import os

TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "template.xlsx")

COLUMN_MAP = [
    ("sequence_no", "序号"),
    ("recommend_date", "推荐日期"),
    ("recommend_channel", "推荐渠道"),
    ("name", "姓名"),
    ("id_number", "身份证"),
    ("age", "年龄"),
    ("gender", "性别"),
    ("phone", "电话"),
    ("education", "学历"),
    ("school", "毕业学校"),
    ("major", "专业"),
    ("screening_date", "筛选日期"),
    ("leader_screening", "领导初筛"),
    ("screening_result", "筛选邀约结果"),
    ("interview_date", "面试日期"),
    ("interview_time", "面试时间"),
    ("interview_note", "备注"),
    ("first_interview_result", "一面结果"),
    ("first_interview_note", "备注"),
    ("second_interview_invite", "二面邀约"),
    ("second_interview_result", "二面结果"),
    ("second_interview_note", "备注"),
    ("project_transfer", "转项目"),
]

def generate_excel(position_id: int, db: Session) -> str:
    candidates = (
        db.query(Candidate)
        .filter(Candidate.job_position_id == position_id)
        .order_by(Candidate.sequence_no)
        .all()
    )

    if os.path.exists(TEMPLATE_PATH):
        wb = load_workbook(TEMPLATE_PATH)
        ws = wb.active
    else:
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        for col_idx, (_, header) in enumerate(COLUMN_MAP, 1):
            ws.cell(row=1, column=col_idx, value=header)

    for row_idx, candidate in enumerate(candidates, 2):
        for col_idx, (field, _) in enumerate(COLUMN_MAP, 1):
            value = getattr(candidate, field, "")
            ws.cell(row=row_idx, column=col_idx, value=value if value else "")

    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    wb.save(tmp.name)
    tmp.close()
    return tmp.name
```

- [ ] **Step 3: Create export_router.py**

```python
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, JobPosition
from app.auth import get_current_user
from app.services.export_service import generate_excel

router = APIRouter(prefix="/api/positions", tags=["export"])

@router.get("/{position_id}/export")
def export_excel(
    position_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    position = db.query(JobPosition).filter(JobPosition.id == position_id).first()
    filename = f"{position.title}_候选人.xlsx" if position else "candidates.xlsx"
    path = generate_excel(position_id, db)
    return FileResponse(path, filename=filename, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
```

- [ ] **Step 4: Create users_router.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserResponse
from app.auth import get_current_user, hash_password

router = APIRouter(prefix="/api/users", tags=["users"])

@router.get("", response_model=List[UserResponse])
def list_users(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(User).order_by(User.created_at).all()

@router.post("", response_model=UserResponse)
def create_user(body: UserCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    new_user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        role=body.role,
        display_name=body.display_name,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    db.delete(target)
    db.commit()
    return {"detail": "Deleted"}
```

- [ ] **Step 5: Register all routers in main.py**

Replace router imports in `backend/app/main.py`:

```python
from app.routers import auth_router, positions_router, upload_router, candidates_router, export_router, users_router

app.include_router(auth_router.router)
app.include_router(positions_router.router)
app.include_router(upload_router.router)
app.include_router(candidates_router.router)
app.include_router(export_router.router)
app.include_router(users_router.router)
```

- [ ] **Step 6: Verify all endpoints**

```bash
# Start server and check docs
uvicorn app.main:app --reload --port 8000
# Visit http://localhost:8000/docs — all endpoints should be listed
```

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat: candidates, export, users APIs — backend complete"
```

---

### Task 6: Frontend Scaffolding & Auth

**Files:**
- Create: `frontend/` (entire React app scaffolding), `frontend/src/api.ts`, `frontend/src/store/authStore.ts`, `frontend/src/components/ProtectedRoute.tsx`, `frontend/src/pages/LoginPage.tsx`, `frontend/src/App.tsx`

- [ ] **Step 1: Scaffold Vite React TypeScript project**

```bash
cd /Users/tony/Documents/GitHub/smartHR
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install antd @ant-design/icons axios zustand
```

- [ ] **Step 2: Configure Vite proxy**

Replace `frontend/vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 3: Create api.ts**

```typescript
import axios from 'axios';

const api = axios.create({ baseURL: '' });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const res = await axios.post('/api/auth/refresh', { refresh_token: refreshToken });
          localStorage.setItem('access_token', res.data.access_token);
          localStorage.setItem('refresh_token', res.data.refresh_token);
          original.headers.Authorization = `Bearer ${res.data.access_token}`;
          return api(original);
        } catch {
          localStorage.clear();
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

export default api;
```

- [ ] **Step 4: Create authStore.ts**

```typescript
import { create } from 'zustand';

interface User {
  id: number;
  username: string;
  role: string;
  display_name: string;
}

interface AuthState {
  user: User | null;
  setUser: (user: User | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  setUser: (user) => set({ user }),
  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    set({ user: null });
  },
}));
```

- [ ] **Step 5: Create ProtectedRoute.tsx**

```typescript
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  const token = localStorage.getItem('access_token');

  if (!token && !user) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}
```

- [ ] **Step 6: Create LoginPage.tsx**

```typescript
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Form, Input, Button, message } from 'antd';
import api from '../api';
import { useAuthStore } from '../store/authStore';

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const setUser = useAuthStore((s) => s.setUser);

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const res = await api.post('/api/auth/login', values);
      localStorage.setItem('access_token', res.data.access_token);
      localStorage.setItem('refresh_token', res.data.refresh_token);
      const me = await api.get('/api/auth/me');
      setUser(me.data);
      navigate('/');
    } catch {
      message.error('用户名或密码错误');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%)',
    }}>
      <Card style={{ width: 380, borderRadius: 16, boxShadow: '0 4px 24px rgba(0,0,0,0.06)' }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <h1 style={{ color: '#6366f1', fontSize: 26, letterSpacing: 2, margin: 0 }}>SmartHR</h1>
          <p style={{ color: '#a1a1aa', fontSize: 13, marginTop: 6 }}>智能简历筛选系统</p>
        </div>
        <Form onFinish={onFinish} layout="vertical">
          <Form.Item name="username" label="用户名" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input size="large" style={{ borderRadius: 10 }} />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password size="large" style={{ borderRadius: 10 }} />
          </Form.Item>
          <Button
            type="primary"
            htmlType="submit"
            block
            size="large"
            loading={loading}
            style={{ borderRadius: 10, background: '#6366f1', borderColor: '#6366f1', letterSpacing: 2 }}
          >
            登 录
          </Button>
        </Form>
      </Card>
    </div>
  );
}
```

- [ ] **Step 7: Create App.tsx with routing**

```typescript
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import LoginPage from './pages/LoginPage';
import ProtectedRoute from './components/ProtectedRoute';
import AppLayout from './components/AppLayout';
import PositionsPage from './pages/PositionsPage';
import UploadPage from './pages/UploadPage';
import CandidatesPage from './pages/CandidatesPage';
import UsersPage from './pages/UsersPage';

const theme = {
  token: {
    colorPrimary: '#6366f1',
    borderRadius: 8,
    colorBgLayout: '#f8fafc',
  },
};

export default function App() {
  return (
    <ConfigProvider locale={zhCN} theme={theme}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
            <Route index element={<Navigate to="/positions" replace />} />
            <Route path="positions" element={<PositionsPage />} />
            <Route path="positions/:id/upload" element={<UploadPage />} />
            <Route path="positions/:id/candidates" element={<CandidatesPage />} />
            <Route path="users" element={<UsersPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}
```

- [ ] **Step 8: Install react-router-dom**

```bash
cd frontend
npm install react-router-dom
```

- [ ] **Step 9: Update main.tsx**

Replace `frontend/src/main.tsx`:

```typescript
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

- [ ] **Step 10: Remove default CSS**

Delete `frontend/src/App.css` and `frontend/src/index.css`. Update `frontend/index.html` — remove the CSS link if present.

- [ ] **Step 11: Create placeholder pages**

Create these files with minimal content so the app compiles:

`frontend/src/pages/PositionsPage.tsx`:
```typescript
export default function PositionsPage() {
  return <div>Positions — coming in Task 7</div>;
}
```

`frontend/src/pages/UploadPage.tsx`:
```typescript
export default function UploadPage() {
  return <div>Upload — coming in Task 8</div>;
}
```

`frontend/src/pages/CandidatesPage.tsx`:
```typescript
export default function CandidatesPage() {
  return <div>Candidates — coming in Task 9</div>;
}
```

`frontend/src/pages/UsersPage.tsx`:
```typescript
export default function UsersPage() {
  return <div>Users — coming in Task 10</div>;
}
```

- [ ] **Step 12: Create AppLayout.tsx**

```typescript
import { useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import {
  FileTextOutlined,
  UploadOutlined,
  TeamOutlined,
  DownloadOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { useAuthStore } from '../store/authStore';
import api from '../api';

const { Sider, Content, Header } = Layout;

const menuItems = [
  { key: '/positions', icon: <FileTextOutlined />, label: '职位管理' },
  { key: '/users', icon: <SettingOutlined />, label: '用户管理' },
];

export default function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, setUser, logout } = useAuthStore();

  useEffect(() => {
    if (!user) {
      api.get('/api/auth/me').then((res) => setUser(res.data)).catch(() => {
        logout();
        navigate('/login');
      });
    }
  }, []);

  const selectedKey = '/' + location.pathname.split('/')[1];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        width={210}
        style={{
          background: '#fff',
          borderRight: '1px solid #f0f0f5',
        }}
      >
        <div style={{
          padding: '20px 24px',
          fontSize: 20,
          fontWeight: 600,
          color: '#6366f1',
          letterSpacing: 1,
        }}>
          SmartHR
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ border: 'none' }}
        />
      </Sider>
      <Layout>
        <Header style={{
          background: '#fff',
          padding: '0 24px',
          display: 'flex',
          justifyContent: 'flex-end',
          alignItems: 'center',
          borderBottom: '1px solid #f0f0f5',
          height: 56,
        }}>
          <span style={{ color: '#71717a', fontSize: 13 }}>
            {user?.display_name}
            <a onClick={() => { logout(); navigate('/login'); }} style={{ marginLeft: 12, color: '#6366f1' }}>退出</a>
          </span>
        </Header>
        <Content style={{ padding: 28, background: '#f8fafc' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
```

- [ ] **Step 13: Verify frontend starts and login works**

```bash
cd frontend
npm run dev
```

Visit `http://localhost:5173` — should redirect to `/login`. Login with `admin/admin123` — should redirect to positions page.

- [ ] **Step 14: Commit**

```bash
git add frontend/
git commit -m "feat: frontend scaffolding with React, Ant Design, auth, and layout"
```

---

### Task 7: Positions Page (Frontend)

**Files:**
- Modify: `frontend/src/pages/PositionsPage.tsx`

- [ ] **Step 1: Implement PositionsPage**

```typescript
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Table, Button, Tag, Input, Modal, Form, Space, message } from 'antd';
import { PlusOutlined, SearchOutlined, UploadOutlined, TeamOutlined } from '@ant-design/icons';
import api from '../api';
import { useAuthStore } from '../store/authStore';

interface Position {
  id: number;
  title: string;
  department: string;
  description: string;
  requirements: string;
  status: string;
  candidate_count: number;
  created_at: string;
}

export default function PositionsPage() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);

  const fetchPositions = async () => {
    setLoading(true);
    try {
      const res = await api.get('/api/positions');
      setPositions(res.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchPositions(); }, []);

  const filtered = positions.filter(
    (p) => p.title.includes(search) || p.department.includes(search)
  );

  const handleSave = async () => {
    const values = await form.validateFields();
    if (editingId) {
      await api.put(`/api/positions/${editingId}`, values);
    } else {
      await api.post('/api/positions', values);
    }
    message.success(editingId ? '已更新' : '已创建');
    setModalOpen(false);
    setEditingId(null);
    form.resetFields();
    fetchPositions();
  };

  const openEdit = (record: Position) => {
    setEditingId(record.id);
    form.setFieldsValue(record);
    setModalOpen(true);
  };

  const columns = [
    { title: '职位名称', dataIndex: 'title', key: 'title', render: (t: string) => <span style={{ fontWeight: 500 }}>{t}</span> },
    { title: '部门', dataIndex: 'department', key: 'department' },
    {
      title: '候选人',
      dataIndex: 'candidate_count',
      key: 'candidate_count',
      render: (n: number) => <span style={{ color: n > 0 ? '#6366f1' : '#a1a1aa', fontWeight: 500 }}>{n}</span>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (s: string) => (
        <Tag color={s === 'open' ? 'purple' : 'default'} style={{ borderRadius: 20 }}>
          {s === 'open' ? '招聘中' : '已关闭'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: Position) => (
        <Space size="small">
          <a onClick={() => navigate(`/positions/${record.id}/candidates`)}>
            <TeamOutlined /> 候选人
          </a>
          <a onClick={() => navigate(`/positions/${record.id}/upload`)}>
            <UploadOutlined /> 上传
          </a>
          {user?.role === 'manager' && <a onClick={() => openEdit(record)}>编辑</a>}
        </Space>
      ),
    },
  ];

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20 }}>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600, color: '#18181b' }}>职位管理</h2>
        {user?.role === 'manager' && (
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => { setEditingId(null); form.resetFields(); setModalOpen(true); }}
            style={{ borderRadius: 8 }}
          >
            新建职位
          </Button>
        )}
      </div>
      <Card style={{ borderRadius: 12, boxShadow: '0 1px 8px rgba(0,0,0,0.04)' }}>
        <Input
          prefix={<SearchOutlined />}
          placeholder="搜索职位..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ width: 260, marginBottom: 16, borderRadius: 8 }}
        />
        <Table
          dataSource={filtered}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={false}
        />
      </Card>

      <Modal
        title={editingId ? '编辑职位' : '新建职位'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => { setModalOpen(false); setEditingId(null); }}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="title" label="职位名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="department" label="部门" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="职位描述 (JD)" rules={[{ required: true }]}>
            <Input.TextArea rows={6} placeholder="请输入完整的职位描述..." />
          </Form.Item>
          <Form.Item name="requirements" label="关键要求">
            <Input.TextArea rows={3} placeholder="如：本科以上，3年Java经验..." />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
```

- [ ] **Step 2: Verify positions page works**

Visit `http://localhost:5173/positions` — should show the table. Login as `admin` (manager role) and create a position.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/PositionsPage.tsx
git commit -m "feat: positions page with CRUD and search"
```

---

### Task 8: Upload Page (Frontend)

**Files:**
- Modify: `frontend/src/pages/UploadPage.tsx`

- [ ] **Step 1: Implement UploadPage**

```typescript
import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Upload, Button, Progress, Tag, message } from 'antd';
import { InboxOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import api from '../api';

interface BatchStatus {
  id: number;
  file_name: string;
  file_count: number;
  processed_count: number;
  status: string;
}

export default function UploadPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [positionTitle, setPositionTitle] = useState('');
  const [batches, setBatches] = useState<BatchStatus[]>([]);
  const [uploading, setUploading] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    api.get(`/api/positions/${id}`).then((res) => setPositionTitle(res.data.title));
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [id]);

  const pollBatch = (batchId: number) => {
    const interval = setInterval(async () => {
      try {
        const res = await api.get(`/api/upload-batches/${batchId}/status`);
        setBatches((prev) => prev.map((b) => (b.id === batchId ? res.data : b)));
        if (res.data.status !== 'processing') {
          clearInterval(interval);
          if (res.data.status === 'completed') {
            message.success(`${res.data.file_name} 处理完成`);
          }
        }
      } catch {
        clearInterval(interval);
      }
    }, 2000);
    pollRef.current = interval;
  };

  const handleUpload = async (file: File) => {
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await api.post(`/api/positions/${id}/upload`, formData);
      setBatches((prev) => [res.data, ...prev]);
      pollBatch(res.data.id);
      message.info('上传成功，开始处理...');
    } catch (e: any) {
      message.error(e.response?.data?.detail || '上传失败');
    } finally {
      setUploading(false);
    }
    return false;
  };

  return (
    <>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/positions')} type="text" />
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>
          上传简历 <span style={{ fontWeight: 400, color: '#a1a1aa', fontSize: 14 }}>— {positionTitle}</span>
        </h2>
      </div>

      <Card style={{ borderRadius: 12, boxShadow: '0 1px 8px rgba(0,0,0,0.04)', marginBottom: 20 }}>
        <Upload.Dragger
          accept=".pdf,.zip"
          showUploadList={false}
          beforeUpload={handleUpload}
          disabled={uploading}
          style={{ borderRadius: 12, background: '#fafaff' }}
        >
          <p style={{ fontSize: 36, opacity: 0.4, margin: '12px 0' }}>📄</p>
          <p style={{ color: '#71717a', margin: '0 0 4px' }}>点击或拖拽文件至此处</p>
          <p style={{ color: '#a1a1aa', fontSize: 12 }}>支持 .zip .pdf，ZIP 内自动解析所有 PDF</p>
        </Upload.Dragger>
      </Card>

      {batches.length > 0 && (
        <Card title="处理进度" style={{ borderRadius: 12, boxShadow: '0 1px 8px rgba(0,0,0,0.04)' }}>
          {batches.map((batch) => (
            <div key={batch.id} style={{
              padding: '12px 16px',
              background: batch.status === 'completed' ? '#f0fdf4'
                : batch.status === 'failed' ? '#fef2f2'
                : '#eef2ff',
              borderRadius: 8,
              marginBottom: 12,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 13 }}>
                <span>{batch.file_name} ({batch.file_count} 份)</span>
                <Tag color={
                  batch.status === 'completed' ? 'success'
                  : batch.status === 'failed' ? 'error'
                  : 'processing'
                }>
                  {batch.status === 'completed' ? '完成' : batch.status === 'failed' ? '失败' : `${batch.processed_count}/${batch.file_count}`}
                </Tag>
              </div>
              <Progress
                percent={batch.file_count > 0 ? Math.round((batch.processed_count / batch.file_count) * 100) : 0}
                size="small"
                strokeColor={batch.status === 'completed' ? '#22c55e' : batch.status === 'failed' ? '#ef4444' : '#6366f1'}
                showInfo={false}
              />
            </div>
          ))}
          <Button
            type="link"
            onClick={() => navigate(`/positions/${id}/candidates`)}
            style={{ padding: 0, color: '#6366f1' }}
          >
            查看候选人列表 →
          </Button>
        </Card>
      )}
    </>
  );
}
```

- [ ] **Step 2: Verify upload page**

Navigate to a position's upload page. Try uploading a PDF (if available). Confirm the progress UI appears.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/UploadPage.tsx
git commit -m "feat: upload page with drag-drop, progress polling"
```

---

### Task 9: Candidates Page (Frontend)

**Files:**
- Modify: `frontend/src/pages/CandidatesPage.tsx`
- Create: `frontend/src/pages/CandidateDetail.tsx`

- [ ] **Step 1: Implement CandidatesPage**

```typescript
import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Table, Tag, Select, Button, Space, Progress, Drawer, Descriptions, message } from 'antd';
import { ArrowLeftOutlined, DownloadOutlined, UploadOutlined } from '@ant-design/icons';
import api from '../api';

interface Candidate {
  id: number;
  sequence_no: number;
  name: string;
  gender: string;
  age: number | null;
  phone: string;
  education: string;
  school: string;
  major: string;
  match_score: number | null;
  ai_recommendation: string;
  ai_summary: string;
  screening_result: string;
  first_interview_result: string;
  second_interview_result: string;
  status: string;
  recommend_date: string;
  recommend_channel: string;
  screening_date: string;
  leader_screening: string;
  interview_date: string;
  interview_time: string;
  interview_note: string;
  first_interview_note: string;
  second_interview_invite: string;
  second_interview_note: string;
  project_transfer: string;
}

interface CandidateDetail extends Candidate {
  id_number: string;
  parsed_text: string;
  ai_screening_result: Record<string, unknown> | null;
  resume_file_path: string;
  error_message: string;
}

const recColors: Record<string, string> = { '推荐': '#22c55e', '待定': '#f59e0b', '不推荐': '#ef4444' };

export default function CandidatesPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(false);
  const [positionTitle, setPositionTitle] = useState('');
  const [filterRec, setFilterRec] = useState<string | undefined>();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [detail, setDetail] = useState<CandidateDetail | null>(null);

  const fetchCandidates = async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (filterRec) params.recommendation = filterRec;
      const res = await api.get(`/api/positions/${id}/candidates`, { params });
      setCandidates(res.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    api.get(`/api/positions/${id}`).then((res) => setPositionTitle(res.data.title));
    fetchCandidates();
  }, [id, filterRec]);

  const updateField = async (candidateId: number, field: string, value: string) => {
    await api.patch(`/api/candidates/${candidateId}`, { [field]: value });
    setCandidates((prev) =>
      prev.map((c) => (c.id === candidateId ? { ...c, [field]: value } : c))
    );
  };

  const openDetail = async (candidateId: number) => {
    const res = await api.get(`/api/candidates/${candidateId}`);
    setDetail(res.data);
    setDrawerOpen(true);
  };

  const exportExcel = async () => {
    const res = await api.get(`/api/positions/${id}/export`, { responseType: 'blob' });
    const url = URL.createObjectURL(res.data);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${positionTitle}_候选人.xlsx`;
    a.click();
    URL.revokeObjectURL(url);
    message.success('导出成功');
  };

  const stats = {
    total: candidates.length,
    recommended: candidates.filter((c) => c.ai_recommendation === '推荐').length,
    pending: candidates.filter((c) => c.ai_recommendation === '待定').length,
    rejected: candidates.filter((c) => c.ai_recommendation === '不推荐').length,
  };

  const statusOptions = ['', '待邀约', '已邀约', '已拒绝'];
  const interviewOptions = ['', '通过', '未通过', '待定'];

  const columns = [
    { title: '#', dataIndex: 'sequence_no', width: 50 },
    { title: '姓名', dataIndex: 'name', width: 80, render: (t: string) => <span style={{ fontWeight: 500 }}>{t}</span> },
    { title: '学历', dataIndex: 'education', width: 60 },
    { title: '学校', dataIndex: 'school', width: 140, ellipsis: true },
    { title: '专业', dataIndex: 'major', width: 120, ellipsis: true },
    { title: '年龄', dataIndex: 'age', width: 50 },
    {
      title: 'AI 评估',
      dataIndex: 'ai_recommendation',
      width: 80,
      render: (r: string) => <span style={{ color: recColors[r] || '#999', fontWeight: 500 }}>{r || '—'}</span>,
    },
    {
      title: '匹配度',
      dataIndex: 'match_score',
      width: 100,
      sorter: (a: Candidate, b: Candidate) => (a.match_score || 0) - (b.match_score || 0),
      defaultSortOrder: 'descend' as const,
      render: (s: number | null) => s != null ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Progress
            percent={s}
            size="small"
            showInfo={false}
            strokeColor={s >= 70 ? '#22c55e' : s >= 40 ? '#f59e0b' : '#ef4444'}
            style={{ width: 50, margin: 0 }}
          />
          <span style={{ fontSize: 12, color: s >= 70 ? '#22c55e' : s >= 40 ? '#f59e0b' : '#ef4444' }}>{s}</span>
        </div>
      ) : '—',
    },
    {
      title: '邀约状态',
      dataIndex: 'screening_result',
      width: 110,
      render: (v: string, record: Candidate) => (
        <Select
          size="small"
          value={v || undefined}
          placeholder="—"
          style={{ width: 90 }}
          onChange={(val) => updateField(record.id, 'screening_result', val)}
          options={statusOptions.map((o) => ({ label: o || '—', value: o }))}
        />
      ),
    },
    {
      title: '一面',
      dataIndex: 'first_interview_result',
      width: 100,
      render: (v: string, record: Candidate) => (
        <Select
          size="small"
          value={v || undefined}
          placeholder="—"
          style={{ width: 80 }}
          onChange={(val) => updateField(record.id, 'first_interview_result', val)}
          options={interviewOptions.map((o) => ({ label: o || '—', value: o }))}
        />
      ),
    },
    {
      title: '',
      key: 'actions',
      width: 60,
      render: (_: unknown, record: Candidate) => (
        <a onClick={() => openDetail(record.id)} style={{ color: '#6366f1', fontSize: 12 }}>详情</a>
      ),
    },
  ];

  return (
    <>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/positions')} type="text" />
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>{positionTitle}</h2>
        <Tag style={{ borderRadius: 20 }}>{stats.total}人</Tag>
        <Tag color="success" style={{ borderRadius: 20 }}>推荐 {stats.recommended}</Tag>
        <Tag color="warning" style={{ borderRadius: 20 }}>待定 {stats.pending}</Tag>
        <Tag color="error" style={{ borderRadius: 20 }}>不推荐 {stats.rejected}</Tag>
      </div>

      <Card style={{ borderRadius: 12, boxShadow: '0 1px 8px rgba(0,0,0,0.04)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <Space>
            <Select
              placeholder="AI推荐筛选"
              allowClear
              value={filterRec}
              onChange={setFilterRec}
              style={{ width: 140 }}
              options={[
                { label: '推荐', value: '推荐' },
                { label: '待定', value: '待定' },
                { label: '不推荐', value: '不推荐' },
              ]}
            />
          </Space>
          <Space>
            <Button icon={<UploadOutlined />} onClick={() => navigate(`/positions/${id}/upload`)}>上传简历</Button>
            <Button type="primary" icon={<DownloadOutlined />} onClick={exportExcel} style={{ background: '#6366f1' }}>
              导出 Excel
            </Button>
          </Space>
        </div>
        <Table
          dataSource={candidates}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 50 }}
          scroll={{ x: 1000 }}
          size="middle"
        />
      </Card>

      <Drawer
        title={detail?.name || '候选人详情'}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={560}
      >
        {detail && (
          <>
            <Descriptions column={2} size="small" bordered style={{ marginBottom: 20 }}>
              <Descriptions.Item label="姓名">{detail.name}</Descriptions.Item>
              <Descriptions.Item label="性别">{detail.gender}</Descriptions.Item>
              <Descriptions.Item label="年龄">{detail.age}</Descriptions.Item>
              <Descriptions.Item label="电话">{detail.phone}</Descriptions.Item>
              <Descriptions.Item label="学历">{detail.education}</Descriptions.Item>
              <Descriptions.Item label="学校">{detail.school}</Descriptions.Item>
              <Descriptions.Item label="专业" span={2}>{detail.major}</Descriptions.Item>
            </Descriptions>

            <Card size="small" title="AI 筛选分析" style={{ marginBottom: 16, borderRadius: 8 }}>
              <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
                <Tag color={recColors[detail.ai_recommendation] === '#22c55e' ? 'success' : recColors[detail.ai_recommendation] === '#ef4444' ? 'error' : 'warning'}>
                  {detail.ai_recommendation}
                </Tag>
                <span>匹配度: <strong>{detail.match_score}</strong>/100</span>
              </div>
              <p style={{ color: '#555', fontSize: 13 }}>{detail.ai_summary}</p>
              {detail.ai_screening_result && (
                <>
                  {(detail.ai_screening_result as any).strengths?.length > 0 && (
                    <div style={{ marginBottom: 8 }}>
                      <strong style={{ fontSize: 12, color: '#22c55e' }}>优势：</strong>
                      {(detail.ai_screening_result as any).strengths.map((s: string, i: number) => (
                        <Tag key={i} color="success" style={{ margin: 2 }}>{s}</Tag>
                      ))}
                    </div>
                  )}
                  {(detail.ai_screening_result as any).concerns?.length > 0 && (
                    <div>
                      <strong style={{ fontSize: 12, color: '#f59e0b' }}>顾虑：</strong>
                      {(detail.ai_screening_result as any).concerns.map((s: string, i: number) => (
                        <Tag key={i} color="warning" style={{ margin: 2 }}>{s}</Tag>
                      ))}
                    </div>
                  )}
                </>
              )}
            </Card>

            <Button
              type="link"
              onClick={() => window.open(`/api/candidates/${detail.id}/resume`, '_blank')}
              style={{ padding: 0, color: '#6366f1' }}
            >
              查看原始简历 PDF →
            </Button>
          </>
        )}
      </Drawer>
    </>
  );
}
```

- [ ] **Step 2: Verify candidates page**

Navigate to a position's candidates page. If test data exists, confirm table renders, inline dropdowns work, detail drawer opens, Excel export downloads.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/CandidatesPage.tsx
git commit -m "feat: candidates table with inline editing, AI scores, detail drawer, export"
```

---

### Task 10: Users Page (Frontend)

**Files:**
- Modify: `frontend/src/pages/UsersPage.tsx`

- [ ] **Step 1: Implement UsersPage**

```typescript
import { useEffect, useState } from 'react';
import { Card, Table, Button, Modal, Form, Input, Select, Tag, Popconfirm, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import api from '../api';

interface UserRecord {
  id: number;
  username: string;
  role: string;
  display_name: string;
  created_at: string;
}

export default function UsersPage() {
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await api.get('/api/users');
      setUsers(res.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchUsers(); }, []);

  const handleCreate = async () => {
    const values = await form.validateFields();
    await api.post('/api/users', values);
    message.success('用户已创建');
    setModalOpen(false);
    form.resetFields();
    fetchUsers();
  };

  const handleDelete = async (userId: number) => {
    await api.delete(`/api/users/${userId}`);
    message.success('已删除');
    fetchUsers();
  };

  const columns = [
    { title: '用户名', dataIndex: 'username' },
    { title: '显示名', dataIndex: 'display_name' },
    {
      title: '角色',
      dataIndex: 'role',
      render: (r: string) => (
        <Tag color={r === 'manager' ? 'purple' : 'blue'} style={{ borderRadius: 20 }}>
          {r === 'manager' ? '用人经理' : 'HR专员'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: UserRecord) => (
        <Popconfirm title="确认删除？" onConfirm={() => handleDelete(record.id)}>
          <a style={{ color: '#ef4444' }}>删除</a>
        </Popconfirm>
      ),
    },
  ];

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20 }}>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>用户管理</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)} style={{ borderRadius: 8 }}>
          新建用户
        </Button>
      </div>

      <Card style={{ borderRadius: 12, boxShadow: '0 1px 8px rgba(0,0,0,0.04)' }}>
        <Table dataSource={users} columns={columns} rowKey="id" loading={loading} pagination={false} />
      </Card>

      <Modal
        title="新建用户"
        open={modalOpen}
        onOk={handleCreate}
        onCancel={() => setModalOpen(false)}
        okText="创建"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true, min: 4 }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item name="display_name" label="显示名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="role" label="角色" rules={[{ required: true }]}>
            <Select options={[{ label: 'HR专员', value: 'hr' }, { label: '用人经理', value: 'manager' }]} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
```

- [ ] **Step 2: Verify users page**

Navigate to `/users`. Create a new user, verify it appears. Delete a user.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/UsersPage.tsx
git commit -m "feat: user management page"
```

---

### Task 11: Final Integration & Polish

**Files:**
- Modify: `frontend/src/components/AppLayout.tsx` (add upload/candidates nav items dynamically)
- Create: `backend/.env` (from .env.example with actual keys)

- [ ] **Step 1: Create .env with your API keys**

```bash
cd backend
cp .env.example .env
# Edit .env and fill in your actual MinerU and DeepSeek API keys
```

- [ ] **Step 2: Delete unused files from Vite scaffold**

```bash
cd frontend
rm -f src/App.css src/index.css src/assets/react.svg public/vite.svg
```

- [ ] **Step 3: End-to-end test**

1. Start backend: `cd backend && uvicorn app.main:app --reload --port 8000`
2. Start frontend: `cd frontend && npm run dev`
3. Login as `admin/admin123`
4. Create a job position with a JD
5. Navigate to upload, upload a ZIP of PDFs
6. Watch processing progress
7. View candidates table with AI scores
8. Update a candidate's status via dropdown
9. Export Excel and verify it matches the template
10. Create a new user, login as that user

- [ ] **Step 4: Commit final state**

```bash
git add -A
git commit -m "feat: SmartHR MVP complete — upload, AI screening, candidate table, Excel export"
```
