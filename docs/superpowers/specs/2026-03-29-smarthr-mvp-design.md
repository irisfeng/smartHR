# SmartHR MVP — Design Spec

## Overview

SmartHR is an internal HR resume screening web application. HR agents upload resume ZIP/PDF files, the system uses AI (MinerU for parsing + DeepSeek/Qwen for screening) to extract candidate information and evaluate against job descriptions, then presents results in a trackable table matching the company's Excel template. Hiring managers can review AI recommendations and update candidate status through the recruitment pipeline.

## User Roles

| Role | Capabilities |
|------|-------------|
| **HR Agent** | Upload ZIP/PDF resumes, view all candidates, update status fields, export Excel |
| **Hiring Manager** | Create/edit job positions with JDs, review AI screening results, update interview status |

Admin functionality (user management) is available to both roles initially — the first user created seeds as admin.

## Tech Stack

- **Frontend:** React (Vite) + Ant Design 5 + TypeScript
- **Backend:** FastAPI + Python 3.11+
- **Database:** SQLite (via SQLAlchemy)
- **Auth:** JWT (access + refresh tokens), bcrypt password hashing
- **File Storage:** Local filesystem (`uploads/` directory)
- **AI Pipeline:** MinerU API (PDF parsing) + DeepSeek/Qwen API (resume screening)
- **Excel Export:** openpyxl (matching the provided template format)

## Data Model

### Users
- id, username, password_hash, role (hr | manager), display_name, created_at

### Job Positions
- id, title, department, description (JD text), requirements (structured), status (open | closed), created_by (user_id), created_at, updated_at

### Candidates
- id, job_position_id, resume_file_path, parsed_text, ai_screening_result (JSON)
- **Template fields (from Excel):**
  - sequence_no (序号), recommend_date (推荐日期), recommend_channel (推荐渠道)
  - name (姓名), id_number (身份证), age (年龄), gender (性别), phone (电话)
  - education (学历), school (毕业学校), major (专业)
  - screening_date (筛选日期), leader_screening (领导初筛), screening_result (筛选邀约结果)
  - interview_date (面试日期), interview_time (面试时间), interview_note (备注)
  - first_interview_result (一面结果), first_interview_note (备注)
  - second_interview_invite (二面邀约), second_interview_result (二面结果), second_interview_note (备注)
  - project_transfer (转项目)
- **AI-added fields:**
  - match_score (0-100), ai_recommendation (推荐 | 待定 | 不推荐), ai_summary (screening rationale)
- created_at, updated_at

### Upload Batches
- id, job_position_id, uploaded_by (user_id), file_name, file_count, status (processing | completed | failed), created_at

## Core Workflows

### 1. Job Position Management (Hiring Manager)
1. Manager creates a position with title, department, and JD (free-text description + key requirements)
2. Position appears in the job list with status "招聘中"
3. Manager can edit JD or close the position

### 2. Resume Upload & AI Processing (HR Agent)
1. HR selects a job position, uploads ZIP or individual PDFs
2. Backend receives file → if ZIP, unzips and extracts all PDFs
3. For each PDF:
   - **MinerU API** extracts structured text from PDF
   - **DeepSeek/Qwen API** receives extracted text + JD → returns:
     - Extracted fields (name, education, school, major, age, gender, phone, etc.)
     - Match score (0-100)
     - Recommendation (推荐/待定/不推荐)
     - Screening summary (why recommended or not)
4. Results saved to database, candidate row created
5. Frontend shows real-time progress via polling (SSE in future)

### 3. Candidate Review & Status Updates
1. HR/Manager views candidate table for a position
2. Table columns match the Excel template, sorted by match score by default
3. Click "详情" to see full AI analysis + original resume PDF
4. Status fields (筛选邀约结果, 一面结果, 二面结果, etc.) are editable inline via dropdowns
5. Filter by AI recommendation, status, education level, etc.

### 4. Excel Export
1. Click "导出 Excel" on the candidate table
2. Backend generates .xlsx using openpyxl, matching the template format exactly (same columns, same order)
3. All candidate data + current status values are exported
4. File downloads in the browser

## API Endpoints

### Auth
- `POST /api/auth/login` — returns JWT tokens
- `POST /api/auth/refresh` — refresh access token
- `GET /api/auth/me` — current user info

### Job Positions
- `GET /api/positions` — list all positions
- `POST /api/positions` — create position (manager only)
- `PUT /api/positions/{id}` — update position
- `GET /api/positions/{id}` — position detail with candidate stats

### Candidates
- `GET /api/positions/{id}/candidates` — list candidates for a position (with pagination, filtering, sorting)
- `GET /api/candidates/{id}` — candidate detail (full AI analysis)
- `PATCH /api/candidates/{id}` — update status fields
- `GET /api/candidates/{id}/resume` — serve original PDF

### Upload
- `POST /api/positions/{id}/upload` — upload ZIP/PDF, returns batch ID
- `GET /api/upload-batches/{id}/status` — polling endpoint for processing progress

### Export
- `GET /api/positions/{id}/export` — download Excel file

### Users (Admin)
- `GET /api/users` — list users
- `POST /api/users` — create user
- `DELETE /api/users/{id}` — remove user

## UI Pages

### Design Language
- **Primary color:** Indigo #6366f1
- **Success:** Green #22c55e | **Warning:** Amber #f59e0b | **Danger:** Red #ef4444
- **Style:** White backgrounds, light card shadows, 12px border-radius, pill-shaped tags, generous whitespace, light sidebar

### Pages
1. **Login** — centered card on gradient background, username/password
2. **Job Positions** — table with search, "+ 新建职位" button, status pills
3. **Resume Upload** — drag & drop zone, processing progress list with status indicators
4. **Candidate Table** — core view matching Excel template columns, AI match score with mini progress bars, inline status dropdowns, filter/sort, export button, summary stats (推荐/待定/不推荐 counts)
5. **Candidate Detail** — drawer/modal with full AI summary, all extracted fields, original PDF viewer
6. **User Management** — simple table to create/delete users with role assignment

### Layout
- Light sidebar navigation (white background, indigo active state)
- Top-right: user display name + logout
- Content area: light gray background (#f8fafc) with white card containers

## AI Prompt Design

### Resume Screening Prompt (DeepSeek/Qwen)
Input: extracted resume text + JD text
Output: structured JSON with:
```json
{
  "name": "张三",
  "gender": "男",
  "age": 28,
  "phone": "13800138000",
  "id_number": null,
  "education": "本科",
  "school": "浙江大学",
  "major": "计算机科学与技术",
  "match_score": 92,
  "recommendation": "推荐",
  "summary": "5年Java开发经验，熟悉Spring Boot和微服务架构，与JD要求高度匹配...",
  "strengths": ["扎实的Java基础", "微服务经验丰富"],
  "concerns": ["缺少大数据经验"]
}
```

## Error Handling

- Upload failures: retry individual PDFs, mark failed ones with error message
- MinerU API failures: queue for retry, show "解析失败" status
- AI API failures: queue for retry, show "分析失败" status
- All errors visible in the upload progress UI

## Security

- JWT tokens with expiration (access: 30min, refresh: 7 days)
- bcrypt password hashing
- Role-based route protection (frontend + backend)
- File upload validation (only ZIP/PDF, size limit 100MB per upload)
- No sensitive data exposure in API responses (password hashes, etc.)

## Out of Scope (MVP)

- Email notifications
- Calendar integration for interviews
- Resume deduplication
- Multi-tenant / multi-company support
- Deployment automation (Docker, CI/CD)
- SSE/WebSocket for real-time progress (use polling for MVP)
