import re
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


def validate_password_complexity(v: str) -> str:
    if not re.search(r'[a-z]', v):
        raise ValueError('Must contain a lowercase letter')
    if not re.search(r'[A-Z]', v):
        raise ValueError('Must contain an uppercase letter')
    if not re.search(r'[0-9]', v):
        raise ValueError('Must contain a digit')
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:,.<>?]', v):
        raise ValueError('Must contain a special character')
    return v

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

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator('new_password')
    @classmethod
    def check_complexity(cls, v: str) -> str:
        return validate_password_complexity(v)

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    display_name: str
    created_at: datetime
    must_change_password: bool = False
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
    # Basic info (editable)
    name: Optional[str] = None
    id_number: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    phone: Optional[str] = None
    education: Optional[str] = None
    school: Optional[str] = None
    major: Optional[str] = None
    # Recruitment pipeline fields
    recommend_date: Optional[str] = None
    recommend_channel: Optional[str] = None
    screening_date: Optional[str] = None
    leader_screening: Optional[str] = None
    screening_result: Optional[str] = None
    interview_date: Optional[str] = None
    interview_time: Optional[str] = None
    interview_note: Optional[str] = None
    first_interview_result: Optional[str] = None
    evaluation_result: Optional[str] = None
    first_interview_note: Optional[str] = None
    second_interview_invite: Optional[str] = None
    second_interview_result: Optional[str] = None
    second_interview_note: Optional[str] = None
    project_transfer: Optional[str] = None

class CandidateResponse(BaseModel):
    id: int
    job_position_id: int
    sequence_no: Optional[int] = None
    name: Optional[str] = ""
    id_number: Optional[str] = ""
    gender: Optional[str] = ""
    age: Optional[int] = None
    phone: Optional[str] = ""
    education: Optional[str] = ""
    school: Optional[str] = ""
    major: Optional[str] = ""
    match_score: Optional[float] = None
    parse_quality: Optional[str] = "good"
    ai_recommendation: Optional[str] = ""
    ai_summary: Optional[str] = ""
    screening_result: Optional[str] = ""
    first_interview_result: Optional[str] = ""
    evaluation_result: Optional[str] = ""
    second_interview_result: Optional[str] = ""
    status: Optional[str] = "pending"
    recommend_date: Optional[str] = ""
    recommend_channel: Optional[str] = ""
    screening_date: Optional[str] = ""
    leader_screening: Optional[str] = ""
    interview_date: Optional[str] = ""
    interview_time: Optional[str] = ""
    interview_note: Optional[str] = ""
    first_interview_note: Optional[str] = ""
    second_interview_invite: Optional[str] = ""
    second_interview_note: Optional[str] = ""
    project_transfer: Optional[str] = ""
    created_at: datetime
    class Config:
        from_attributes = True

class CandidateDetailResponse(CandidateResponse):
    id_number: Optional[str] = ""
    parsed_text: Optional[str] = ""
    ai_screening_result: Optional[dict] = None
    ai_analysis: Optional[str] = ""
    resume_file_path: Optional[str] = ""
    error_message: Optional[str] = ""

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
    username: str = Field(..., min_length=2, max_length=32)
    password: str = Field(..., min_length=6, max_length=128)
    role: str = Field(..., pattern="^(hr|manager)$")
    display_name: str = Field(..., min_length=1, max_length=32)
