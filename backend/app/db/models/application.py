from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ApplicationModel(Base):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    role_title: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    priority: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    salary_range: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resume_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    tags: Mapped[list] = mapped_column(ARRAY(Text), nullable=False, default=list)
    last_activity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    next_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_action_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=lambda: datetime.now(UTC).isoformat())
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False, default=lambda: datetime.now(UTC).isoformat())

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','applied','screening','interviewing','offered','rejected','withdrawn','accepted','archived')",
            name="ck_applications_status",
        ),
        CheckConstraint("priority IN ('low','medium','high')", name="ck_applications_priority"),
    )


class ApplicationNoteModel(Base):
    __tablename__ = "application_notes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    application_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=lambda: datetime.now(UTC).isoformat())


class TimelineEventModel(Base):
    __tablename__ = "timeline_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    application_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, default="custom")
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    event_metadata: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=lambda: datetime.now(UTC).isoformat())
