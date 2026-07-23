from datetime import datetime, timezone

from pydantic import BaseModel, Field


class Notification(BaseModel):
    id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    type: str = Field(..., description="resume_exported, cover_letter_generated, interview_scheduled, ai_suggestions_ready, application_follow_up")
    title: str = Field(..., min_length=1)
    message: str = ""
    read: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
