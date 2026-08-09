from datetime import UTC, datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ResumeModel(Base):
    __tablename__ = "resumes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    linkedin: Mapped[str | None] = mapped_column(String(500), nullable=True)
    github: Mapped[str | None] = mapped_column(String(500), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    professional_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    education: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    experience: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    projects: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    skills: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    certifications: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    awards: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    languages: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=lambda: datetime.now(UTC).isoformat())
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False, default=lambda: datetime.now(UTC).isoformat())
