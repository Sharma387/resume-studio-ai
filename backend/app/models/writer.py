from datetime import datetime, timezone

from pydantic import BaseModel, Field


class SuggestionType(str):
    PHRASING = "phrasing"
    GRAMMAR = "grammar"
    SKILLS = "skills"
    SUMMARY = "summary"
    ACHIEVEMENT = "achievement"
    COMPLETENESS = "completeness"
    KEYWORD = "keyword"
    FULL_REVIEW = "full_review"


class ResumeSuggestion(BaseModel):
    id: str = Field(..., min_length=1)
    resume_id: str = Field(..., min_length=1)
    suggestion_type: str = Field(default=SuggestionType.PHRASING)
    section: str = Field(..., min_length=1, description="Resume section (experience, summary, skills, etc.)")
    field_path: str | None = Field(None, description="JSON path to the specific field")
    original_text: str = Field(default="")
    suggested_text: str = Field(default="")
    reason: str = Field(default="")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    ai_model: str | None = Field(default=None)
    source: str = Field(default="ai_writer")
    status: str = Field(default="pending", pattern=r"^(pending|accepted|rejected)$")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class WriterRequest(BaseModel):
    prompt: str = Field(..., min_length=3, description="What the user wants to improve")
    focus_section: str | None = Field(None, description="Optional: limit to one section")


class BulkAcceptRequest(BaseModel):
    suggestion_ids: list[str] = []
