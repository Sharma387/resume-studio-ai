from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class CoverLetterTone(str, Enum):
    PROFESSIONAL = "professional"
    ENTHUSIASTIC = "enthusiastic"
    FORMAL = "formal"
    CONCISE = "concise"


class CoverLetterRequest(BaseModel):
    job_description: str = Field(..., min_length=20, description="Full job description text")
    company_name: str | None = Field(None, description="Target company name")
    hiring_manager: str | None = Field(None, description="Hiring manager name if known")
    role_title: str | None = Field(None, description="Job title being applied for")
    tone: CoverLetterTone = Field(default=CoverLetterTone.PROFESSIONAL)


class CoverLetter(BaseModel):
    id: str = Field(..., min_length=1)
    resume_id: str = Field(..., min_length=1)
    application_id: str | None = Field(None, description="Future: links to a JobApplication")
    company_name: str | None = None
    hiring_manager: str | None = None
    role_title: str | None = None
    tone: CoverLetterTone = CoverLetterTone.PROFESSIONAL
    content: str = Field(default="", description="Full cover letter text")
    subject: str | None = Field(None, description="Email subject line suggestion")
    ai_model: str | None = Field(None, description="Model used for generation")
    job_description_hash: str | None = Field(None, description="SHA256 of original job description for dedup")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
