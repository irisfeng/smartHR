from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float, Boolean
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
    must_change_password = Column(Boolean, default=False, nullable=False)

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
    file_hash = Column(String(64), nullable=True, index=True)
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
    evaluation_result = Column(String(50), default="")
    first_interview_note = Column(Text, default="")
    second_interview_invite = Column(String(50), default="")
    second_interview_result = Column(String(50), default="")
    second_interview_note = Column(Text, default="")
    project_transfer = Column(String(100), default="")
    # AI fields
    match_score = Column(Float, nullable=True)
    parse_quality = Column(String(10), default="good")  # "good" or "poor"
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
