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
