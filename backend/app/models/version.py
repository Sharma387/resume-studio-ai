from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.models.resume import Resume


class ResumeVersion(BaseModel):
    user_id: str
    id: str = Field(..., min_length=1)
    resume_id: str = Field(..., min_length=1)
    label: str | None = None
    resume: Resume
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
