from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class ApplicationStatus(str, Enum):
    DRAFT = "draft"
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEWING = "interviewing"
    OFFERED = "offered"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    ACCEPTED = "accepted"
    ARCHIVED = "archived"


class ApplicationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TimelineEventType(str, Enum):
    CREATED = "created"
    STATUS_CHANGED = "status_changed"
    RESUME_UPDATED = "resume_updated"
    COVER_LETTER_GENERATED = "cover_letter_generated"
    MATCH_ANALYZED = "match_analyzed"
    NOTE_ADDED = "note_added"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    OFFER_RECEIVED = "offer_received"
    MOCK_INTERVIEW_COMPLETED = "mock_interview_completed"
    CUSTOM = "custom"


class ApplicationNote(BaseModel):
    id: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TimelineEvent(BaseModel):
    id: str = Field(..., min_length=1)
    application_id: str = Field(..., min_length=1)
    event_type: TimelineEventType = TimelineEventType.CUSTOM
    title: str = Field(default="")
    description: str = Field(default="")
    metadata: dict = {}
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Application(BaseModel):
    user_id: str
    id: str = Field(..., min_length=1)
    company: str = Field(..., min_length=1)
    role_title: str = Field(..., min_length=1)
    location: str | None = None
    url: str | None = None
    status: ApplicationStatus = ApplicationStatus.DRAFT
    priority: ApplicationPriority = ApplicationPriority.MEDIUM
    salary_range: str | None = None
    notes: list[ApplicationNote] = []
    tags: list[str] = []

    resume_id: str | None = None
    cover_letter_ids: list[str] = []
    match_ids: list[str] = []
    version_ids: list[str] = []
    writer_suggestion_ids: list[str] = []

    last_activity: str | None = None
    next_action: str | None = None
    next_action_date: str | None = None

    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ApplicationView(BaseModel):
    """Aggregates an application with its linked resource summaries for the frontend."""

    application: Application
    resume_name: str | None = None
    cover_letter_count: int = 0
    match_count: int = 0
    version_count: int = 0
    interview_count: int = 0
    latest_interview_session: dict | None = None
    latest_readiness: dict | None = None
    recent_timeline: list[TimelineEvent] = []


class DashboardSummary(BaseModel):
    total: int = 0
    by_status: dict[str, int] = {}
    by_priority: dict[str, int] = {}
    active: int = 0
    interviews: int = 0
    offers: int = 0
    recent_applications: list[Application] = []
