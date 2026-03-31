# SmartHR MVP — Fixes & Hardening Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all critical bugs and security issues identified in code review, add missing error handling, and harden the MVP to production-ready quality.

**Architecture:** FastAPI backend + React frontend. Fixes are organized into 3 phases: (1) commit current work, (2) fix critical frontend bugs, (3) fix backend security + harden both layers.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, React 19, TypeScript, Ant Design 6, Axios, Zustand

---

## Phase 0: Commit Current Work

### Task 0: Commit uncommitted frontend pages

**Files:**
- Already modified: `frontend/src/pages/CandidatesPage.tsx`, `PositionsPage.tsx`, `UploadPage.tsx`, `UsersPage.tsx`

- [ ] **Step 1: Stage and commit**

```bash
git add frontend/src/pages/CandidatesPage.tsx frontend/src/pages/PositionsPage.tsx frontend/src/pages/UploadPage.tsx frontend/src/pages/UsersPage.tsx
git commit -m "feat: implement all frontend pages with API integration

- PositionsPage: CRUD table with search, role-gated create/edit
- UploadPage: drag-drop upload with polling progress
- CandidatesPage: full table with AI scores, inline edits, detail drawer, export
- UsersPage: user management with create/delete"
```

---

## Phase 1: Frontend Critical Fixes

### Task 1: Fix token refresh race condition + TypeScript errors in api.ts

**Files:**
- Modify: `frontend/src/api.ts`

The `_retry` property is untyped, and concurrent 401s cause multiple refresh calls. Fix by adding a mutex Promise and declaring the custom property.

- [ ] **Step 1: Rewrite `frontend/src/api.ts` with refresh mutex and proper types**

```typescript
import axios from 'axios';

const api = axios.create({ baseURL: '' });

let refreshPromise: Promise<void> | null = null;

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

interface RetryableConfig {
  _retry?: boolean;
  [key: string]: unknown;
}

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config as RetryableConfig;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      if (!refreshPromise) {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) {
          localStorage.clear();
          window.location.href = '/login';
          return Promise.reject(error);
        }
        refreshPromise = axios.post('/api/auth/refresh', { refresh_token: refreshToken })
          .then((res) => {
            localStorage.setItem('access_token', res.data.access_token);
            localStorage.setItem('refresh_token', res.data.refresh_token);
          })
          .catch(() => {
            localStorage.clear();
            window.location.href = '/login';
          })
          .finally(() => {
            refreshPromise = null;
          });
      }
      await refreshPromise;
      const token = localStorage.getItem('access_token');
      if (token) {
        original.headers.Authorization = `Bearer ${token}`;
        return api(original);
      }
    }
    return Promise.reject(error);
  }
);

export default api;
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api.ts
git commit -m "fix: add token refresh mutex and fix TypeScript type errors in api.ts"
```

---

### Task 2: Fix React hook issues across all pages (useCallback + deps)

**Files:**
- Modify: `frontend/src/pages/CandidatesPage.tsx`
- Modify: `frontend/src/pages/PositionsPage.tsx`
- Modify: `frontend/src/pages/UsersPage.tsx`
- Modify: `frontend/src/components/AppLayout.tsx`

All fetch functions are recreated every render causing stale closures. Move fetch logic inside useEffect or wrap with useCallback.

- [ ] **Step 1: Fix `frontend/src/pages/CandidatesPage.tsx` — move fetch inside useEffect**

Replace lines 57-72 with:

```typescript
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(false);
  const [positionTitle, setPositionTitle] = useState('');
  const [filterRec, setFilterRec] = useState<string | undefined>();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [detail, setDetail] = useState<CandidateDetail | null>(null);

  useEffect(() => {
    api.get(`/api/positions/${id}`).then((res) => setPositionTitle(res.data.title)).catch(() => {});
    setLoading(true);
    const params: Record<string, string> = {};
    if (filterRec) params.recommendation = filterRec;
    api.get(`/api/positions/${id}/candidates`, { params })
      .then((res) => setCandidates(res.data))
      .catch(() => message.error('获取候选人列表失败'))
      .finally(() => setLoading(false));
  }, [id, filterRec]);
```

- [ ] **Step 2: Fix `frontend/src/pages/PositionsPage.tsx` — move fetch inside useEffect**

Replace lines 29-39 with:

```typescript
  useEffect(() => {
    setLoading(true);
    api.get('/api/positions')
      .then((res) => setPositions(res.data))
      .catch(() => message.error('获取职位列表失败'))
      .finally(() => setLoading(false));
  }, []);
```

- [ ] **Step 3: Fix `frontend/src/pages/UsersPage.tsx` — move fetch inside useEffect**

Replace lines 20-30 with:

```typescript
  useEffect(() => {
    setLoading(true);
    api.get('/api/users')
      .then((res) => setUsers(res.data))
      .catch(() => message.error('获取用户列表失败'))
      .finally(() => setLoading(false));
  }, []);
```

Also need a reload function for after create/delete. Add after the useEffect:

```typescript
  const reload = () => {
    setLoading(true);
    api.get('/api/users')
      .then((res) => setUsers(res.data))
      .catch(() => message.error('获取用户列表失败'))
      .finally(() => setLoading(false));
  };
```

Update `handleCreate` (line 38) and `handleDelete` (line 44) to call `reload()` instead of `fetchUsers()`.

- [ ] **Step 4: Fix `frontend/src/components/AppLayout.tsx` — add user to useEffect deps**

Change line 30 from `}, []);` to `}, [user, setUser, logout, navigate]);`

- [ ] **Step 5: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/ frontend/src/components/AppLayout.tsx
git commit -m "fix: resolve React hook dependency issues and stale closures across all pages"
```

---

### Task 3: Fix resume PDF access (broken auth) + fix ProtectedRoute React import

**Files:**
- Modify: `frontend/src/pages/CandidatesPage.tsx` (line 273-278)
- Modify: `frontend/src/components/ProtectedRoute.tsx`

The resume PDF `window.open()` sends no auth header. Fix by downloading via axios and opening a blob URL.

- [ ] **Step 1: Fix resume PDF access in `frontend/src/pages/CandidatesPage.tsx`**

Replace lines 273-279 with:

```typescript
            <Button
              type="link"
              onClick={async () => {
                try {
                  const res = await api.get(`/api/candidates/${detail.id}/resume`, { responseType: 'blob' });
                  const url = URL.createObjectURL(res.data);
                  window.open(url, '_blank');
                } catch {
                  message.error('获取简历失败');
                }
              }}
              style={{ padding: 0, color: '#6366f1' }}
            >
              查看原始简历 PDF →
            </Button>
```

- [ ] **Step 2: Fix `frontend/src/components/ProtectedRoute.tsx` — add ReactNode import**

```typescript
import { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

export default function ProtectedRoute({ children }: { children: ReactNode }) {
  const user = useAuthStore((s) => s.user);
  const token = localStorage.getItem('access_token');

  if (!token && !user) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/CandidatesPage.tsx frontend/src/components/ProtectedRoute.tsx
git commit -m "fix: resume PDF now downloaded via axios with auth; fix ReactNode import"
```

---

### Task 4: Add error handling to all API call sites

**Files:**
- Modify: `frontend/src/pages/PositionsPage.tsx`
- Modify: `frontend/src/pages/CandidatesPage.tsx`
- Modify: `frontend/src/pages/UsersPage.tsx`
- Modify: `frontend/src/pages/UploadPage.tsx`

Every user-facing action needs try/catch with `message.error()`.

- [ ] **Step 1: Add error handling to `PositionsPage.tsx` handleSave**

Replace lines 45-57 with:

```typescript
  const handleSave = async () => {
    try {
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
      // Reload positions
      setLoading(true);
      api.get('/api/positions')
        .then((res) => setPositions(res.data))
        .finally(() => setLoading(false));
    } catch (e: any) {
      if (e.response?.data?.detail) {
        message.error(e.response.data.detail);
      }
    }
  };
```

- [ ] **Step 2: Add error handling to `CandidatesPage.tsx` updateField**

Replace lines 74-79 with:

```typescript
  const updateField = async (candidateId: number, field: string, value: string) => {
    try {
      await api.patch(`/api/candidates/${candidateId}`, { [field]: value });
      setCandidates((prev) =>
        prev.map((c) => (c.id === candidateId ? { ...c, [field]: value } : c))
      );
    } catch {
      message.error('更新失败');
    }
  };
```

- [ ] **Step 3: Add error handling to `CandidatesPage.tsx` openDetail**

Replace lines 81-85 with:

```typescript
  const openDetail = async (candidateId: number) => {
    try {
      const res = await api.get(`/api/candidates/${candidateId}`);
      setDetail(res.data);
      setDrawerOpen(true);
    } catch {
      message.error('获取详情失败');
    }
  };
```

- [ ] **Step 4: Add error handling to `CandidatesPage.tsx` exportExcel**

Replace lines 87-96 with:

```typescript
  const exportExcel = async () => {
    try {
      const res = await api.get(`/api/positions/${id}/export`, { responseType: 'blob' });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${positionTitle}_候选人.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
      message.success('导出成功');
    } catch {
      message.error('导出失败');
    }
  };
```

- [ ] **Step 5: Add error handling to `UsersPage.tsx` handleCreate and handleDelete**

Replace lines 32-45 with:

```typescript
  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      await api.post('/api/users', values);
      message.success('用户已创建');
      setModalOpen(false);
      form.resetFields();
      reload();
    } catch (e: any) {
      if (e.response?.data?.detail) {
        message.error(e.response.data.detail);
      }
    }
  };

  const handleDelete = async (userId: number) => {
    try {
      await api.delete(`/api/users/${userId}`);
      message.success('已删除');
      reload();
    } catch (e: any) {
      message.error(e.response?.data?.detail || '删除失败');
    }
  };
```

- [ ] **Step 6: Add error handling to `UploadPage.tsx` position fetch**

Replace line 24 with:

```typescript
    api.get(`/api/positions/${id}`).then((res) => setPositionTitle(res.data.title)).catch(() => message.error('获取职位信息失败'));
```

- [ ] **Step 7: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/
git commit -m "fix: add error handling with user feedback to all API call sites"
```

---

### Task 5: Fix ai_screening_result type safety + add Error Boundary

**Files:**
- Modify: `frontend/src/pages/CandidatesPage.tsx`
- Create: `frontend/src/components/ErrorBoundary.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add typed interface for AI screening result in `CandidatesPage.tsx`**

Add after the `CandidateDetail` interface (after line 43):

```typescript
interface AiScreeningResult {
  strengths?: string[];
  concerns?: string[];
  [key: string]: unknown;
}
```

Replace `(detail.ai_screening_result as any)` casts (lines 253, 256, 261, 264) with:

```typescript
{(() => {
  const ai = detail.ai_screening_result as AiScreeningResult | null;
  if (!ai) return null;
  return (
    <>
      {ai.strengths && ai.strengths.length > 0 && (
        <div style={{ marginBottom: 8 }}>
          <strong style={{ fontSize: 12, color: '#22c55e' }}>优势：</strong>
          {ai.strengths.map((s: string, i: number) => (
            <Tag key={i} color="success" style={{ margin: 2 }}>{s}</Tag>
          ))}
        </div>
      )}
      {ai.concerns && ai.concerns.length > 0 && (
        <div>
          <strong style={{ fontSize: 12, color: '#f59e0b' }}>顾虑：</strong>
          {ai.concerns.map((s: string, i: number) => (
            <Tag key={i} color="warning" style={{ margin: 2 }}>{s}</Tag>
          ))}
        </div>
      )}
    </>
  );
})()}
```

- [ ] **Step 2: Create `frontend/src/components/ErrorBoundary.tsx`**

```typescript
import { Component, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 48, textAlign: 'center' }}>
          <h2 style={{ color: '#ef4444' }}>页面出错了</h2>
          <p style={{ color: '#71717a' }}>请刷新页面重试</p>
          <a href="/" style={{ color: '#6366f1' }}>返回首页</a>
        </div>
      );
    }
    return this.props.children;
  }
}
```

- [ ] **Step 3: Wrap routes in ErrorBoundary in `frontend/src/App.tsx`**

Add import: `import ErrorBoundary from './components/ErrorBoundary';`

Wrap the `<Routes>` block:

```typescript
      <BrowserRouter>
        <ErrorBoundary>
          <Routes>
            ...
          </Routes>
        </ErrorBoundary>
      </BrowserRouter>
```

- [ ] **Step 4: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ErrorBoundary.tsx frontend/src/App.tsx frontend/src/pages/CandidatesPage.tsx
git commit -m "fix: type-safe ai_screening_result, add Error Boundary component"
```

---

### Task 6: Add position status toggle + strengthen password validation

**Files:**
- Modify: `frontend/src/pages/PositionsPage.tsx`
- Modify: `frontend/src/pages/UsersPage.tsx`

- [ ] **Step 1: Add status toggle to PositionsPage edit form**

In `frontend/src/pages/PositionsPage.tsx`, add after the `requirements` Form.Item (after line 153):

```typescript
          {editingId && (
            <Form.Item name="status" label="状态">
              <Select options={[{ label: '招聘中', value: 'open' }, { label: '已关闭', value: 'closed' }]} />
            </Form.Item>
          )}
```

- [ ] **Step 2: Strengthen password minimum length in UsersPage**

In `frontend/src/pages/UsersPage.tsx`, change line 95 from:

```typescript
          <Form.Item name="password" label="密码" rules={[{ required: true, min: 4 }]}>
```

to:

```typescript
          <Form.Item name="password" label="密码" rules={[{ required: true, min: 6, message: '密码至少6位' }]}>
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/PositionsPage.tsx frontend/src/pages/UsersPage.tsx
git commit -m "feat: add position status toggle in edit form, strengthen password to 6 chars min"
```

---

## Phase 2: Backend Hardening

### Task 7: Fix path traversal in file_service.py

**Files:**
- Modify: `backend/app/services/file_service.py`

The `extract_zip` function uses `os.path.basename(name)` which is safe for writing, but the resume serve endpoint in `candidates_router.py:70` uses `FileResponse(candidate.resume_file_path)` — if `candidate.resume_file_path` were somehow manipulated (e.g., via a future admin API), it could serve arbitrary files. Harden file_service to validate paths are within the upload directory.

- [ ] **Step 1: Add path validation to `backend/app/services/file_service.py`**

Add at the end of the file:

```python
def validate_resume_path(file_path: str) -> bool:
    """Ensure the file path is within the upload directory."""
    upload_root = Path(settings.upload_dir).resolve()
    resolved = Path(file_path).resolve()
    try:
        resolved.relative_to(upload_root)
    except ValueError:
        return False
    return resolved.exists() and resolved.is_file()
```

- [ ] **Step 2: Use validation in `backend/app/routers/candidates_router.py`**

Add import at top: `from app.services.file_service import validate_resume_path`

Replace lines 66-70 with:

```python
    if not validate_resume_path(candidate.resume_file_path):
        raise HTTPException(status_code=404, detail="Resume file not found")
    return FileResponse(candidate.resume_file_path, media_type="application/pdf")
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/file_service.py backend/app/routers/candidates_router.py
git commit -m "fix: add path traversal protection for resume file serving"
```

---

### Task 8: Fix ZIP extraction vulnerability (zip bomb / zip slip)

**Files:**
- Modify: `backend/app/services/file_service.py`

The `extract_zip` function doesn't validate that extracted paths stay within the upload directory (zip slip), and doesn't limit decompressed size (zip bomb).

- [ ] **Step 1: Harden `extract_zip` in `backend/app/services/file_service.py`**

Replace the `extract_zip` function (lines 20-33) with:

```python
def extract_zip(zip_path: str, position_id: int) -> list[str]:
    pdf_paths = []
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
            # Zip slip check
            base_name = os.path.basename(info.filename)
            if not base_name:
                continue
            # Size check
            if info.file_size > max_single_file_mb * 1024 * 1024:
                continue
            content = zf.read(info.filename)
            unique_name = f"{uuid.uuid4().hex}_{base_name}"
            file_path = upload_dir / unique_name
            file_path.write_bytes(content)
            pdf_paths.append(str(file_path))
            if len(pdf_paths) >= max_total_files:
                break
    return pdf_paths
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/file_service.py
git commit -m "fix: harden ZIP extraction against zip slip and zip bomb attacks"
```

---

### Task 9: Add backend input validation + rate limiting seed

**Files:**
- Modify: `backend/app/routers/users_router.py`
- Modify: `backend/app/schemas.py`

User creation allows any-length passwords and usernames. The `sort_by` parameter in candidates is passed directly to `getattr(Candidate, sort_by)` which could access unintended model attributes.

- [ ] **Step 1: Add validation to `backend/app/schemas.py` UserCreate**

Find the `UserCreate` schema and add field constraints. Read the file first to see the current definition, then add `min_length` constraints:

```python
class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=32)
    password: str = Field(..., min_length=6, max_length=128)
    role: str = Field(..., pattern="^(hr|manager)$")
    display_name: str = Field(..., min_length=1, max_length=32)
```

Add `from pydantic import BaseModel, Field` to imports.

- [ ] **Step 2: Whitelist sort_by columns in `backend/app/routers/candidates_router.py`**

Replace line 27 with:

```python
    allowed_sort = {"match_score", "sequence_no", "name", "education", "age", "created_at"}
    sort_col = getattr(Candidate, sort_by, Candidate.match_score) if sort_by in allowed_sort else Candidate.match_score
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas.py backend/app/routers/candidates_router.py
git commit -m "fix: add input validation for user creation, whitelist sort columns"
```

---

## Phase 3: Smoke Test

### Task 10: End-to-end smoke test

**Files:** No changes — verification only.

- [ ] **Step 1: Create `.env` file from example**

```bash
cd backend
cp .env.example .env
```

(Contents: `secret_key=smarthr-dev-secret-change-me`)

- [ ] **Step 2: Seed database and start backend**

```bash
cd backend
python seed.py
uvicorn app.main:app --reload --port 8000 &
```

Expected: Server starts, health check returns `{"status": "ok"}`

- [ ] **Step 3: Start frontend**

```bash
cd frontend
npm run dev &
```

Expected: Vite starts on port 5173

- [ ] **Step 4: Manual verification checklist**

Open http://localhost:5173 and verify:
1. Login with `admin` / `admin123` — should succeed
2. Positions page loads (empty table is fine)
3. Create a position (title + dept + JD)
4. Navigate to upload, upload a test PDF
5. Navigate to candidates, verify table shows
6. Click candidate detail drawer
7. Export Excel button
8. Users page shows admin user
9. Create a new HR user
10. Logout, login as new user
11. Verify "新建职位" button is hidden for HR role

- [ ] **Step 5: Stop servers**

```bash
kill %1 %2 2>/dev/null
```

- [ ] **Step 6: Final commit (if any fixes needed from smoke test)**

If any issues were found and fixed during smoke testing, commit them:

```bash
git add -A
git commit -m "fix: address issues found during smoke test"
```

---

## Summary

| Phase | Tasks | Focus |
|-------|-------|-------|
| Phase 0 | Task 0 | Commit current work |
| Phase 1 | Tasks 1-6 | Fix all frontend critical bugs, hooks, auth, error handling |
| Phase 2 | Tasks 7-9 | Backend security hardening |
| Phase 3 | Task 10 | End-to-end smoke test |

**Total: 10 tasks, ~30 steps**
