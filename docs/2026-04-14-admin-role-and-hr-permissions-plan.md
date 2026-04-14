# Admin Role & HR Permissions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `admin` role for account-only management, give `hr` position CRUD, support password reset + forced first-login change, and deploy to VPS.

**Architecture:** Extend the existing FastAPI + SQLAlchemy + React stack. New DB column `must_change_password`; new FastAPI dependency intercepts business routes when flag is set (HTTP 428); frontend adds `ForceChangePasswordPage` + route guard; `admin` role gets exclusive access to `/api/users/*`. Existing users and data stay intact.

**Tech Stack:** FastAPI, SQLAlchemy 2.x, Pydantic v2, bcrypt/passlib, SQLite, React 18, Ant Design 5, Zustand, Axios.

**Design spec:** `docs/2026-04-14-admin-role-and-hr-permissions-design.md`

---

## File Structure

**Backend — create:**
- `backend/scripts/migrate_add_admin.py` — idempotent migration runner
- `backend/tests/test_admin.py` — admin role & reset-password tests
- `backend/tests/test_must_change_password.py` — 428 interception tests

**Backend — modify:**
- `backend/app/models.py` — add `must_change_password` column
- `backend/app/schemas.py` — role pattern, add `UserUpdate`, `AdminResetPasswordRequest`, add field to `UserResponse`
- `backend/app/auth.py` — add `get_current_active_user` dependency
- `backend/app/main.py` — register new column in startup auto-migration list
- `backend/app/routers/auth_router.py` — replace heuristic-based must-change with column-based; clear flag on self change-password
- `backend/app/routers/positions_router.py` — allow `hr` for POST/PUT
- `backend/app/routers/users_router.py` — switch to `admin`, add PUT + reset-password + last-admin guard; use `get_current_user` (not active) so admin can always touch accounts
- `backend/app/routers/candidates_router.py`, `upload_router.py`, `export_router.py` — swap `get_current_user` → `get_current_active_user` on all routes
- `backend/seed.py` — add default `admin` account

**Frontend — create:**
- `frontend/src/pages/ForceChangePasswordPage.tsx`

**Frontend — modify:**
- `frontend/src/store/authStore.ts` — add `must_change_password` to `User`
- `frontend/src/App.tsx` — add `/force-change-password` route
- `frontend/src/components/AppLayout.tsx` — role-aware menu + guard redirect
- `frontend/src/components/ProtectedRoute.tsx` — forward-check must_change_password
- `frontend/src/pages/LoginPage.tsx` — react to `must_change_password` on login response
- `frontend/src/pages/PositionsPage.tsx` — allow `hr` on create/edit buttons
- `frontend/src/pages/UsersPage.tsx` — admin-only writes, add edit dialog, add reset-password action

---

## Task 1: Add `must_change_password` column to User model

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/schemas.py`
- Test: `backend/tests/test_admin.py`

- [ ] **Step 1: Write failing test for column existence**

Create `backend/tests/test_admin.py`:

```python
"""Tests for admin role, reset password, and must_change_password flag."""
from app.models import User


def test_user_model_has_must_change_password_default_false(db):
    user = User(
        username="u1",
        password_hash="x",
        role="hr",
        display_name="U",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    assert user.must_change_password is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_admin.py -v`
Expected: FAIL — `AttributeError: 'User' object has no attribute 'must_change_password'`

- [ ] **Step 3: Add column to `User` model**

In `backend/app/models.py`, inside `class User`, after the `created_at` line add:

```python
    must_change_password = Column(Boolean, default=False, nullable=False)
```

Update the imports at the top of the file:

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float, Boolean
```

- [ ] **Step 4: Register column in startup auto-migration**

In `backend/app/main.py`, update `_NEW_COLUMNS`:

```python
_NEW_COLUMNS = [
    ("candidates", "evaluation_result", "VARCHAR(50) DEFAULT ''"),
    ("users", "must_change_password", "BOOLEAN DEFAULT 0 NOT NULL"),
]
```

- [ ] **Step 5: Add `must_change_password` to `UserResponse`**

In `backend/app/schemas.py`, in `class UserResponse`:

```python
class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    display_name: str
    created_at: datetime
    must_change_password: bool = False
    class Config:
        from_attributes = True
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && pytest tests/test_admin.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/models.py backend/app/main.py backend/app/schemas.py backend/tests/test_admin.py
git commit -m "feat(db): add must_change_password to users"
```

---

## Task 2: Allow `admin` role in schemas; add UserUpdate & AdminResetPasswordRequest

**Files:**
- Modify: `backend/app/schemas.py`
- Test: `backend/tests/test_admin.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/test_admin.py`:

```python
import pytest
from pydantic import ValidationError
from app.schemas import UserCreate, UserUpdate, AdminResetPasswordRequest


def test_user_create_accepts_admin_role():
    u = UserCreate(username="a", password="xyz123", role="admin", display_name="A")
    assert u.role == "admin"


def test_user_create_rejects_unknown_role():
    with pytest.raises(ValidationError):
        UserCreate(username="a", password="xyz123", role="root", display_name="A")


def test_user_update_all_fields_optional():
    u = UserUpdate()
    assert u.display_name is None
    assert u.role is None


def test_admin_reset_password_enforces_complexity():
    with pytest.raises(ValidationError):
        AdminResetPasswordRequest(new_password="short")
    ok = AdminResetPasswordRequest(new_password="Aa1!aaaa")
    assert ok.new_password == "Aa1!aaaa"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_admin.py -v`
Expected: FAIL — `ImportError: cannot import name 'UserUpdate'` etc.

- [ ] **Step 3: Update schemas**

In `backend/app/schemas.py`, replace the `UserCreate` block with:

```python
# Users
class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=32)
    password: str = Field(..., min_length=6, max_length=128)
    role: str = Field(..., pattern="^(hr|manager|admin)$")
    display_name: str = Field(..., min_length=1, max_length=32)


class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=32)
    role: Optional[str] = Field(None, pattern="^(hr|manager|admin)$")


class AdminResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator('new_password')
    @classmethod
    def check_complexity(cls, v: str) -> str:
        return validate_password_complexity(v)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_admin.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas.py backend/tests/test_admin.py
git commit -m "feat(schemas): allow admin role and add UserUpdate/AdminResetPasswordRequest"
```

---

## Task 3: Add `get_current_active_user` dependency (428 interception)

**Files:**
- Modify: `backend/app/auth.py`
- Test: `backend/tests/test_must_change_password.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_must_change_password.py`:

```python
"""Tests for the HTTP 428 must-change-password interception."""
from app.models import User
from app.auth import hash_password, create_access_token


def _make_user(db, *, role="hr", must_change=False):
    u = User(
        username=f"flagged_{role}_{int(must_change)}",
        password_hash=hash_password("password123"),
        role=role,
        display_name="Flagged",
        must_change_password=must_change,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def test_flagged_user_blocked_from_business_endpoint(client, db):
    u = _make_user(db, must_change=True)
    token = create_access_token(u.id, u.role)
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/positions", headers=headers)
    assert resp.status_code == 428
    body = resp.json()
    assert body["detail"] == "Password change required"


def test_flagged_user_can_still_change_password(client, db):
    u = _make_user(db, must_change=True)
    token = create_access_token(u.id, u.role)
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"old_password": "password123", "new_password": "Aa1!aaaa"},
    )
    assert resp.status_code == 200


def test_unflagged_user_is_not_blocked(client, db):
    u = _make_user(db, must_change=False)
    token = create_access_token(u.id, u.role)
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/positions", headers=headers)
    assert resp.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_must_change_password.py -v`
Expected: FAIL — first test gets 200 instead of 428 (flag isn't enforced yet).

- [ ] **Step 3: Add dependency**

Append to `backend/app/auth.py`:

```python
def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    """Same as get_current_user but blocks users flagged for forced password change.

    Apply to all business routes. Auth routes (/api/auth/*) and the users
    router keep get_current_user / require_role so admins can manage accounts
    even while their own flag is set.
    """
    if user.must_change_password:
        raise HTTPException(
            status_code=428,
            detail="Password change required",
        )
    return user
```

- [ ] **Step 4: Wire dependency into business routers**

In every file below, replace `get_current_user` imports with `get_current_active_user` and swap every `Depends(get_current_user)` to `Depends(get_current_active_user)`:
- `backend/app/routers/positions_router.py`
- `backend/app/routers/candidates_router.py`
- `backend/app/routers/upload_router.py`
- `backend/app/routers/export_router.py`

Also replace `require_role(...)` callsites' underlying dependency: update `require_role` in `auth.py` to depend on `get_current_active_user`:

```python
def require_role(*roles: str):
    def dependency(user: User = Depends(get_current_active_user)):
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return dependency
```

**Do NOT** change `users_router.py` or `auth_router.py` here — admins must be able to CRUD accounts and anyone must be able to change their own password while flagged. They keep the plain `get_current_user`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_must_change_password.py -v`
Expected: 3 PASS

- [ ] **Step 6: Run full backend test suite to confirm no regressions**

Run: `cd backend && pytest -v`
Expected: all existing tests still pass.

- [ ] **Step 7: Commit**

```bash
git add backend/app/auth.py backend/app/routers/positions_router.py backend/app/routers/candidates_router.py backend/app/routers/upload_router.py backend/app/routers/export_router.py backend/tests/test_must_change_password.py
git commit -m "feat(auth): enforce must_change_password via 428 on business routes"
```

---

## Task 4: Wire flag into login/refresh and clear on self change-password

**Files:**
- Modify: `backend/app/routers/auth_router.py`
- Test: `backend/tests/test_auth.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/test_auth.py`:

```python
def test_login_returns_must_change_password_from_column(client, db):
    from app.models import User
    from app.auth import hash_password
    u = User(
        username="flagger",
        password_hash=hash_password("Aa1!aaaa"),
        role="hr",
        display_name="F",
        must_change_password=True,
    )
    db.add(u)
    db.commit()
    resp = client.post("/api/auth/login", json={"username": "flagger", "password": "Aa1!aaaa"})
    assert resp.status_code == 200
    assert resp.json()["must_change_password"] is True


def test_change_password_clears_flag(client, db):
    from app.models import User
    from app.auth import hash_password, create_access_token
    u = User(
        username="clearer",
        password_hash=hash_password("password123"),
        role="hr",
        display_name="C",
        must_change_password=True,
    )
    db.add(u); db.commit(); db.refresh(u)
    token = create_access_token(u.id, u.role)
    resp = client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"old_password": "password123", "new_password": "Aa1!aaaa"},
    )
    assert resp.status_code == 200
    db.refresh(u)
    assert u.must_change_password is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_auth.py::test_login_returns_must_change_password_from_column tests/test_auth.py::test_change_password_clears_flag -v`
Expected: FAIL — login returns old heuristic value; change-password doesn't touch the column.

- [ ] **Step 3: Replace heuristic with column read + clear flag on success**

In `backend/app/routers/auth_router.py`, replace the `login` body and the `change_password` body:

```python
@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {
        "access_token": create_access_token(user.id, user.role),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer",
        "must_change_password": user.must_change_password,
    }
```

```python
@router.post("/change-password")
def change_password(body: ChangePasswordRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Old password is incorrect")
    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False
    db.commit()
    return {"detail": "Password changed"}
```

Also delete the now-unused `DEFAULT_PASSWORD` constant at the top of the file.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_auth.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/auth_router.py backend/tests/test_auth.py
git commit -m "feat(auth): clear must_change_password on self password change"
```

---

## Task 5: Allow `hr` to create/edit positions

**Files:**
- Modify: `backend/app/routers/positions_router.py`
- Test: `backend/tests/test_positions.py`

- [ ] **Step 1: Write failing test**

Append to `backend/tests/test_positions.py`:

```python
def test_hr_can_create_position(client, hr_headers):
    resp = client.post(
        "/api/positions",
        headers=hr_headers,
        json={
            "title": "HR Created",
            "department": "产研",
            "description": "desc",
            "requirements": "req",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "HR Created"


def test_hr_can_update_position(client, db, hr_headers, hr_user):
    from app.models import JobPosition
    pos = JobPosition(title="T", department="D", description="X", created_by=hr_user.id)
    db.add(pos); db.commit(); db.refresh(pos)
    resp = client.put(
        f"/api/positions/{pos.id}",
        headers=hr_headers,
        json={"title": "Updated"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_positions.py::test_hr_can_create_position tests/test_positions.py::test_hr_can_update_position -v`
Expected: FAIL with 403.

- [ ] **Step 3: Expand role list on both routes**

In `backend/app/routers/positions_router.py`, change **both**:

```python
    user: User = Depends(require_role("manager")),
```

to:

```python
    user: User = Depends(require_role("hr", "manager")),
```

(on `create_position` line ~26 and `update_position` line ~51)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_positions.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/positions_router.py backend/tests/test_positions.py
git commit -m "feat(positions): allow hr to create and edit positions"
```

---

## Task 6: Lock users router to admin, add PUT & reset-password, add safeguards

**Files:**
- Modify: `backend/app/routers/users_router.py`
- Modify: `backend/app/schemas.py` (import-only check)
- Test: `backend/tests/test_admin.py`
- Test: `backend/tests/test_users.py` — update existing manager-based tests

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/test_admin.py`:

```python
from app.models import User
from app.auth import hash_password, create_access_token


def _make_admin(db):
    u = User(
        username="admin1",
        password_hash=hash_password("password123"),
        role="admin",
        display_name="Admin1",
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


def _make_hr(db, username="hr1"):
    u = User(
        username=username,
        password_hash=hash_password("password123"),
        role="hr",
        display_name="HR1",
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


def _headers_for(user):
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}


def test_admin_can_create_user(client, db):
    admin = _make_admin(db)
    resp = client.post(
        "/api/users",
        headers=_headers_for(admin),
        json={"username": "newguy", "password": "pwd1234", "role": "hr", "display_name": "NG"},
    )
    assert resp.status_code == 200
    assert resp.json()["must_change_password"] is True


def test_manager_cannot_create_user(client, manager_headers):
    resp = client.post(
        "/api/users",
        headers=manager_headers,
        json={"username": "nope", "password": "pwd1234", "role": "hr", "display_name": "NP"},
    )
    assert resp.status_code == 403


def test_admin_can_update_user(client, db):
    admin = _make_admin(db)
    target = _make_hr(db)
    resp = client.put(
        f"/api/users/{target.id}",
        headers=_headers_for(admin),
        json={"display_name": "Renamed", "role": "manager"},
    )
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Renamed"
    assert resp.json()["role"] == "manager"


def test_admin_reset_password_sets_flag(client, db):
    admin = _make_admin(db)
    target = _make_hr(db)
    resp = client.post(
        f"/api/users/{target.id}/reset-password",
        headers=_headers_for(admin),
        json={"new_password": "Aa1!aaaa"},
    )
    assert resp.status_code == 200
    db.refresh(target)
    assert target.must_change_password is True


def test_admin_cannot_reset_own_password(client, db):
    admin = _make_admin(db)
    resp = client.post(
        f"/api/users/{admin.id}/reset-password",
        headers=_headers_for(admin),
        json={"new_password": "Aa1!aaaa"},
    )
    assert resp.status_code == 400


def test_admin_cannot_delete_self(client, db):
    admin = _make_admin(db)
    resp = client.delete(f"/api/users/{admin.id}", headers=_headers_for(admin))
    assert resp.status_code == 400


def test_cannot_delete_last_admin(client, db):
    admin = _make_admin(db)
    target = _make_hr(db)
    # Target is hr, not admin; promote-then-delete the current admin via another admin
    other_admin = User(
        username="admin2",
        password_hash=hash_password("password123"),
        role="admin",
        display_name="Admin2",
    )
    db.add(other_admin); db.commit(); db.refresh(other_admin)
    # Delete admin2 is allowed (admin1 remains)
    resp = client.delete(f"/api/users/{other_admin.id}", headers=_headers_for(admin))
    assert resp.status_code == 200
    # But deleting the last admin must fail; use hr user's token? No — hr can't delete.
    # Use a separate admin we just deleted — recreate flow: try delete admin1 via admin1 (self) fails 400 already tested.
    # Create a fresh admin3, use it to try deleting admin1, then delete admin3, then try delete last.
    admin3 = User(
        username="admin3",
        password_hash=hash_password("password123"),
        role="admin",
        display_name="Admin3",
    )
    db.add(admin3); db.commit(); db.refresh(admin3)
    client.delete(f"/api/users/{admin.id}", headers=_headers_for(admin3))
    # Now only admin3 remains. Trying to delete admin3 via admin3 hits "cannot delete self" first (400).
    # So create admin4, then delete admin3 via admin4, then try delete admin4 via admin4 -> cannot delete self.
    # The true "last admin" guard is better hit via demoting role; we'll test via PUT:
    resp = client.put(
        f"/api/users/{admin3.id}",
        headers=_headers_for(admin3),
        json={"role": "hr"},
    )
    assert resp.status_code == 400
    assert "last admin" in resp.json()["detail"].lower()
```

Also update `backend/tests/test_users.py`: the existing tests use `manager_headers` to create/delete users. Swap them to an admin fixture. Add this fixture at the top of `backend/tests/conftest.py`:

```python
@pytest.fixture
def admin_user(db) -> User:
    user = User(
        username="test_admin",
        password_hash=hash_password("password123"),
        role="admin",
        display_name="Test Admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user) -> str:
    return create_access_token(admin_user.id, admin_user.role)


@pytest.fixture
def admin_headers(admin_token) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}
```

Then in `backend/tests/test_users.py`, replace every `manager_headers` parameter in user-write tests (`test_create_user_*`, `test_delete_user_*`) with `admin_headers`. Also update `test_create_user_invalid_role` — `admin` is now valid; change the test payload to `"role": "root"` and keep expecting 422.

- [ ] **Step 2: Run the new tests to see they fail**

Run: `cd backend && pytest tests/test_admin.py -v`
Expected: FAIL — new endpoints don't exist, manager->admin switch not done.

- [ ] **Step 3: Rewrite `users_router.py`**

Replace the entire content of `backend/app/routers/users_router.py` with:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserUpdate, UserResponse, AdminResetPasswordRequest
from app.auth import get_current_user, require_role, hash_password

router = APIRouter(prefix="/api/users", tags=["users"])


def _admin_count(db: Session) -> int:
    return db.query(User).filter(User.role == "admin").count()


@router.get("", response_model=List[UserResponse])
def list_users(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(User).order_by(User.created_at).all()


@router.post("", response_model=UserResponse)
def create_user(body: UserCreate, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    new_user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        role=body.role,
        display_name=body.display_name,
        must_change_password=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    body: UserUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    # Guard: don't let the last admin be demoted
    if body.role is not None and target.role == "admin" and body.role != "admin":
        if _admin_count(db) <= 1:
            raise HTTPException(status_code=400, detail="Cannot demote the last admin")
    if body.display_name is not None:
        target.display_name = body.display_name
    if body.role is not None:
        target.role = body.role
    db.commit()
    db.refresh(target)
    return target


@router.post("/{user_id}/reset-password")
def reset_password(
    user_id: int,
    body: AdminResetPasswordRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="Use change-password for your own account")
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    target.password_hash = hash_password(body.new_password)
    target.must_change_password = True
    db.commit()
    return {"detail": "Password reset"}


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    if target.role == "admin" and _admin_count(db) <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last admin")
    db.delete(target)
    db.commit()
    return {"detail": "Deleted"}
```

Note: `require_role` already uses `get_current_active_user` under the hood (from Task 3), which **would** block a flagged admin. This is intentional — a flagged admin must change their own password before managing others. If you need a flagged admin to still be able to manage accounts, this is out of scope (see design §10).

Actually re-check: the design flow is "admin logs in with default password → forced to change → then manages accounts". So 428 blocking admin from /api/users while flagged is fine.

- [ ] **Step 4: Run the admin tests to verify they pass**

Run: `cd backend && pytest tests/test_admin.py tests/test_users.py -v`
Expected: all pass.

- [ ] **Step 5: Run the full suite**

Run: `cd backend && pytest -v`
Expected: every test passes.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/users_router.py backend/tests/
git commit -m "feat(users): admin-only CRUD with reset-password and last-admin guard"
```

---

## Task 7: Migration script and seed update

**Files:**
- Create: `backend/scripts/migrate_add_admin.py`
- Create: `backend/scripts/__init__.py` (empty, so the dir is a package-adjacent)
- Modify: `backend/seed.py`

- [ ] **Step 1: Create `__init__.py`**

Create empty file `backend/scripts/__init__.py`.

- [ ] **Step 2: Write the migration script**

Create `backend/scripts/migrate_add_admin.py`:

```python
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
```

- [ ] **Step 3: Run the script locally**

Run: `cd backend && python -m scripts.migrate_add_admin`
Expected: prints `[OK]` for both (since the auto-migrator in `main.py` already added the column and local DB may or may not have admin).

Run it again:
Expected: prints `[OK]` both times (idempotent).

- [ ] **Step 4: Update seed.py**

In `backend/seed.py`, append to `USERS` (before the loop):

```python
USERS.append(("admin", "admin", "综合办", "系统管理员"))
```

And in the insert loop, set `must_change_password` for admin:

Replace the body of the for loop with:

```python
for username, role, _dept, display_name in USERS:
    if not db.query(User).filter(User.username == username).first():
        db.add(User(
            username=username,
            password_hash=hash_password("Admin@2026" if role == "admin" else DEFAULT_PASSWORD),
            role=role,
            display_name=display_name,
            must_change_password=(role == "admin"),
        ))
        created += 1
```

- [ ] **Step 5: Run seed in a fresh DB sanity check**

Run: `cd backend && rm -f smarthr-seed-test.db && DATABASE_URL=sqlite:///./smarthr-seed-test.db python seed.py && python -c "from sqlalchemy import create_engine, text; e=create_engine('sqlite:///./smarthr-seed-test.db'); print(list(e.connect().execute(text('select username, role, must_change_password from users'))))" && rm smarthr-seed-test.db`
Expected: sees 12 users including `admin` with `must_change_password=1`.

(If `DATABASE_URL` env is not wired through `config.py`, skip this step and trust the unit tests.)

- [ ] **Step 6: Commit**

```bash
git add backend/scripts/ backend/seed.py
git commit -m "feat(migrate): idempotent admin seed + column migration script"
```

---

## Task 8: Frontend — authStore + LoginPage

**Files:**
- Modify: `frontend/src/store/authStore.ts`
- Modify: `frontend/src/pages/LoginPage.tsx`

- [ ] **Step 1: Update the `User` interface**

In `frontend/src/store/authStore.ts`:

```typescript
import { create } from 'zustand';

interface User {
  id: number;
  username: string;
  role: string;
  display_name: string;
  must_change_password: boolean;
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

- [ ] **Step 2: Update LoginPage to honor the flag**

Read `frontend/src/pages/LoginPage.tsx` first to find the exact lines. Then:

1. After `localStorage.setItem('refresh_token', ...)`, add:

```tsx
   if (res.data.must_change_password) {
     navigate('/force-change-password', { replace: true });
     return;
   }
```

2. Keep the existing post-login navigation (to `/positions`) below that early-return.

The exact snippet to change is the success handler in the form submit. Match the surrounding code style (`navigate` from `react-router-dom`).

- [ ] **Step 3: Type-check**

Run: `cd frontend && npm run build`
Expected: build succeeds. (Or `npx tsc --noEmit` if that's faster.)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/store/authStore.ts frontend/src/pages/LoginPage.tsx
git commit -m "feat(auth): expose must_change_password in auth store and login flow"
```

---

## Task 9: Frontend — ForceChangePasswordPage + route + guard

**Files:**
- Create: `frontend/src/pages/ForceChangePasswordPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/ProtectedRoute.tsx`

- [ ] **Step 1: Create the page**

Create `frontend/src/pages/ForceChangePasswordPage.tsx`:

```tsx
import { useState } from 'react';
import { Card, Form, Input, Button, message } from 'antd';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { useAuthStore } from '../store/authStore';

export default function ForceChangePasswordPage() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const setUser = useAuthStore((s) => s.setUser);

  const onSubmit = async () => {
    const values = await form.validateFields();
    if (values.new_password !== values.confirm_password) {
      message.error('两次密码不一致');
      return;
    }
    setLoading(true);
    try {
      await api.post('/api/auth/change-password', {
        old_password: values.old_password,
        new_password: values.new_password,
      });
      const me = await api.get('/api/auth/me');
      setUser(me.data);
      message.success('密码修改成功');
      navigate('/', { replace: true });
    } catch (e: any) {
      const detail = e.response?.data?.detail;
      message.error(Array.isArray(detail) ? detail.map((d: any) => d.msg).join('; ') : (detail || '修改失败'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f8fafc' }}>
      <Card style={{ width: 420, borderRadius: 12 }}>
        <h2 style={{ marginTop: 0 }}>首次登录 · 请修改密码</h2>
        <p style={{ color: '#71717a', fontSize: 13 }}>为保护账户安全，请先修改初始密码。至少 8 位，包含大小写字母、数字和特殊字符。</p>
        <Form form={form} layout="vertical" onFinish={onSubmit}>
          <Form.Item name="old_password" label="当前密码" rules={[{ required: true }]}>
            <Input.Password autoFocus />
          </Form.Item>
          <Form.Item name="new_password" label="新密码" rules={[{ required: true }, { min: 8 }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item name="confirm_password" label="确认新密码" rules={[{ required: true }]}>
            <Input.Password />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={loading} block>提交</Button>
        </Form>
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: Register route**

In `frontend/src/App.tsx`, add inside `<Routes>` but **outside** the `<ProtectedRoute>` wrapper — the page is its own gate:

```tsx
import ForceChangePasswordPage from './pages/ForceChangePasswordPage';

// inside <Routes>
<Route path="/force-change-password" element={<ForceChangePasswordPage />} />
```

Place it next to the `/login` route.

- [ ] **Step 3: Guard ProtectedRoute**

Read the current `frontend/src/components/ProtectedRoute.tsx` first. It likely checks token presence. Add a check: after fetching `/auth/me` (or reading the store), if `user.must_change_password === true`, redirect to `/force-change-password`.

Concretely, at the top of ProtectedRoute's render:

```tsx
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

// ... inside component ...
const user = useAuthStore((s) => s.user);
if (user?.must_change_password) {
  return <Navigate to="/force-change-password" replace />;
}
```

Keep this check AFTER the auth/me load finishes — don't redirect while user is still null/loading.

Also handle a 428 coming back from any business endpoint by intercepting in `frontend/src/api.ts`. Add to the response interceptor, alongside the 401 branch:

```tsx
if (error.response?.status === 428) {
  window.location.href = '/force-change-password';
  return Promise.reject(error);
}
```

- [ ] **Step 4: Type-check / build**

Run: `cd frontend && npm run build`
Expected: success.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/ForceChangePasswordPage.tsx frontend/src/App.tsx frontend/src/components/ProtectedRoute.tsx frontend/src/api.ts
git commit -m "feat(frontend): force-change-password page, guard and 428 interceptor"
```

---

## Task 10: Frontend — AppLayout role-aware menu

**Files:**
- Modify: `frontend/src/components/AppLayout.tsx`

- [ ] **Step 1: Replace menuItems computation**

In `frontend/src/components/AppLayout.tsx`, replace the existing `menuItems` definition with role-matrix-driven logic:

```tsx
const role = user?.role;

const menuItems = (() => {
  if (role === 'admin') {
    return [{ key: '/users', icon: <SettingOutlined />, label: '用户管理' }];
  }
  const items: any[] = [
    { key: '/positions', icon: <FileTextOutlined />, label: '职位管理' },
    { key: '/candidates', icon: <TeamOutlined />, label: '候选人管理' },
  ];
  return items;
})();
```

(This removes "候选人管理" for managers? No — existing code hides it for managers. Re-check: the new spec keeps candidates for managers. So both hr and manager get the same two menu items. Only admin is different.)

Double check: design §5.1 says manager sees 职位管理 + 候选人管理 (no user management). HR sees 职位管理 + 简历上传 + 候选人管理. But the existing UI doesn't have a dedicated "简历上传" menu — upload is triggered per-position from PositionsPage. Leave that behavior intact. Net effect: hr and manager see the same two items; admin sees only "用户管理". Good.

- [ ] **Step 2: If admin lands on a non-admin page, redirect to /users**

Add to the `useEffect` after user load:

```tsx
useEffect(() => {
  if (user?.role === 'admin' && location.pathname !== '/users') {
    navigate('/users', { replace: true });
  }
}, [user, location.pathname]);
```

- [ ] **Step 3: Build to confirm**

Run: `cd frontend && npm run build`
Expected: success.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/AppLayout.tsx
git commit -m "feat(frontend): role-aware menu for admin/hr/manager"
```

---

## Task 11: Frontend — PositionsPage lets HR create & edit

**Files:**
- Modify: `frontend/src/pages/PositionsPage.tsx`

- [ ] **Step 1: Broaden the role guards**

In `frontend/src/pages/PositionsPage.tsx`, find:

```tsx
{user?.role === 'manager' && <a onClick={() => openEdit(record)}>编辑</a>}
```

Replace with:

```tsx
{(user?.role === 'hr' || user?.role === 'manager') && <a onClick={() => openEdit(record)}>编辑</a>}
```

Find:

```tsx
{user?.role === 'manager' && (
  <Button
    type="primary"
    icon={<PlusOutlined />}
```

Replace the condition with `(user?.role === 'hr' || user?.role === 'manager')`.

- [ ] **Step 2: Build**

Run: `cd frontend && npm run build`
Expected: success.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/PositionsPage.tsx
git commit -m "feat(positions-ui): allow hr to create and edit positions"
```

---

## Task 12: Frontend — UsersPage admin features

**Files:**
- Modify: `frontend/src/pages/UsersPage.tsx`

- [ ] **Step 1: Add admin option, reset-password action, edit dialog**

Open `frontend/src/pages/UsersPage.tsx`. Make these changes:

**a. Import the store to check role:**

```tsx
import { useAuthStore } from '../store/authStore';
```

At top of component:

```tsx
const currentUser = useAuthStore((s) => s.user);
const isAdmin = currentUser?.role === 'admin';
```

**b. Role dropdown options (in the create form):**

```tsx
<Select options={[
  { label: 'HR专员', value: 'hr' },
  { label: '用人经理', value: 'manager' },
  { label: '系统管理员', value: 'admin' },
]} />
```

**c. Tag color in the role column:**

```tsx
render: (r: string) => {
  const map: Record<string, { color: string; label: string }> = {
    admin: { color: 'red', label: '系统管理员' },
    manager: { color: 'purple', label: '用人经理' },
    hr: { color: 'blue', label: 'HR专员' },
  };
  const { color, label } = map[r] ?? { color: 'default', label: r };
  return <Tag color={color} style={{ borderRadius: 20 }}>{label}</Tag>;
}
```

**d. Add an "action" column with 编辑 / 重置密码 / 删除 buttons, but only when `isAdmin`:**

```tsx
{
  title: '操作',
  key: 'actions',
  render: (_: any, record: UserRecord) => {
    if (!isAdmin) return null;
    return (
      <Space size="small">
        <a onClick={() => openEdit(record)}>编辑</a>
        <a onClick={() => openResetPwd(record)}>重置密码</a>
        <Popconfirm title="确定删除该账号？" onConfirm={() => handleDelete(record.id)}>
          <a style={{ color: '#ef4444' }}>删除</a>
        </Popconfirm>
      </Space>
    );
  },
},
```

Remove the standalone delete button in the existing column if present (consolidate into the action column).

**e. Add edit modal state + handler:**

```tsx
const [editForm] = Form.useForm();
const [editingId, setEditingId] = useState<number | null>(null);
const [editOpen, setEditOpen] = useState(false);

const openEdit = (record: UserRecord) => {
  setEditingId(record.id);
  editForm.setFieldsValue({ display_name: record.display_name, role: record.role });
  setEditOpen(true);
};

const handleEdit = async () => {
  const values = await editForm.validateFields();
  try {
    await api.put(`/api/users/${editingId}`, values);
    message.success('已更新');
    setEditOpen(false);
    reload();
  } catch (e: any) {
    message.error(e.response?.data?.detail || '更新失败');
  }
};
```

And the JSX modal:

```tsx
<Modal title="编辑用户" open={editOpen} onOk={handleEdit} onCancel={() => setEditOpen(false)} okText="保存" cancelText="取消">
  <Form form={editForm} layout="vertical">
    <Form.Item name="display_name" label="显示名" rules={[{ required: true }]}>
      <Input />
    </Form.Item>
    <Form.Item name="role" label="角色" rules={[{ required: true }]}>
      <Select options={[
        { label: 'HR专员', value: 'hr' },
        { label: '用人经理', value: 'manager' },
        { label: '系统管理员', value: 'admin' },
      ]} />
    </Form.Item>
  </Form>
</Modal>
```

**f. Add reset-password modal:**

```tsx
const [resetForm] = Form.useForm();
const [resetTargetId, setResetTargetId] = useState<number | null>(null);
const [resetOpen, setResetOpen] = useState(false);

const openResetPwd = (record: UserRecord) => {
  setResetTargetId(record.id);
  resetForm.resetFields();
  setResetOpen(true);
};

const handleResetPassword = async () => {
  const values = await resetForm.validateFields();
  try {
    await api.post(`/api/users/${resetTargetId}/reset-password`, {
      new_password: values.new_password,
    });
    message.success('密码已重置，请把临时密码告知该用户，其下次登录将被要求修改');
    setResetOpen(false);
  } catch (e: any) {
    const detail = e.response?.data?.detail;
    message.error(Array.isArray(detail) ? detail.map((d: any) => d.msg).join('; ') : (detail || '重置失败'));
  }
};
```

JSX modal:

```tsx
<Modal title="重置密码" open={resetOpen} onOk={handleResetPassword} onCancel={() => setResetOpen(false)} okText="重置" cancelText="取消">
  <p style={{ color: '#71717a', fontSize: 13 }}>至少 8 位，含大小写字母、数字和特殊字符。重置后该用户下次登录必须自行修改密码。</p>
  <Form form={resetForm} layout="vertical">
    <Form.Item name="new_password" label="新密码" rules={[{ required: true }, { min: 8 }]}>
      <Input.Password />
    </Form.Item>
  </Form>
</Modal>
```

**g. Hide "新建用户" button for non-admin:**

Wrap the existing `<Button>` creating users with `{isAdmin && ...}`.

- [ ] **Step 2: Build**

Run: `cd frontend && npm run build`
Expected: success.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/UsersPage.tsx
git commit -m "feat(users-ui): admin-only create/edit/reset-password UI"
```

---

## Task 13: Manual smoke test locally

- [ ] **Step 1: Run migration + start backend**

```bash
cd backend
python -m scripts.migrate_add_admin
uvicorn app.main:app --reload --port 8000
```

- [ ] **Step 2: Start frontend**

```bash
cd frontend
npm run dev
```

- [ ] **Step 3: Walk the checklist**

Open the dev URL in browser and verify:

- [ ] Login as `admin / Admin@2026` → redirected to `/force-change-password`
- [ ] Change password to `Admin@2026New!` → redirected to `/users`
- [ ] Only "用户管理" menu visible
- [ ] Create a new user with role `hr` → appears in list with must_change flag (check DB or log)
- [ ] Reset password for an existing user → success toast
- [ ] Try to delete self → 400 error toast
- [ ] Try to demote the only admin → 400 error toast
- [ ] Logout, log in as `hr / Smart2026!` → sees 职位管理 + 候选人管理
- [ ] Click "新建职位" → modal opens, can submit
- [ ] Log in as `mgr_rd / Smart2026!` → sees 职位管理 + 候选人管理 (no 用户管理)
- [ ] A user whose password was just reset must be forced to change on next login

- [ ] **Step 4: Commit checklist results**

Nothing to commit if everything works. If issues surface, file them as follow-up tasks rather than patching mid-plan.

---

## Task 14: VPS deployment

**Target:** Tencent Cloud VPS `124.222.82.73:9527`, Docker Compose.

- [ ] **Step 1: Push code**

From local:

```bash
git push origin main
```

- [ ] **Step 2: SSH to VPS and pull**

```bash
ssh root@124.222.82.73
cd /path/to/smartHR   # substitute real path; see docs/tencent-cloud-deployment.md
git fetch --all
git pull origin main
```

- [ ] **Step 3: Rebuild images**

```bash
docker-compose build backend frontend
```

- [ ] **Step 4: Run migration**

```bash
docker-compose run --rm backend python -m scripts.migrate_add_admin
```

Expected output:
```
[ADDED] column users.must_change_password        (or [OK] if already present)
[ADDED] default admin account  username=admin  password=Admin@2026  (flagged for forced change)
Migration complete.
```

- [ ] **Step 5: Restart services**

```bash
docker-compose up -d
docker-compose ps   # all services healthy
```

- [ ] **Step 6: Smoke test on VPS**

In a browser, open `http://124.222.82.73:9527`:

- [ ] Login as `admin / Admin@2026` → forced-change-password screen appears
- [ ] Change to a secure new password → lands on 用户管理
- [ ] Login in separate incognito as an existing `hr` account → sees "新建职位" button
- [ ] Login as `mgr_admin` (old manager with综合办) → user management menu is gone

- [ ] **Step 7: Record deployment in Memory**

Append a new dated section to `Memory/20260414.md` (create if not present) summarizing the change and the new admin credential handover instructions for the customer.

- [ ] **Step 8: Tag release**

```bash
git tag -a v0.6.0 -m "admin role + hr position CRUD + forced password change"
git push origin v0.6.0
```

---

## Task 15: Clean up

- [ ] **Step 1: Verify all checklist items in design doc §9 are checked**

Open `docs/2026-04-14-admin-role-and-hr-permissions-design.md` and confirm each human-verification item is done.

- [ ] **Step 2: Rotate the default admin password**

The VPS admin should log in and change `Admin@2026` → some strong password you give to the customer out-of-band. The forced-change flow handles this on first login.

- [ ] **Step 3: Final commit / close**

Nothing to commit. Close out this plan.
