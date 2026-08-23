from datetime import UTC, datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MatchResultModel(Base):
    __tablename__ = "match_results"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resume_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    overall_score: Mapped[float] = mapped_column(nullable=False)
    skill_matches: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    matched_skills: Mapped[list] = mapped_column(ARRAY(Text), nullable=False, default=list)
    missing_skills: Mapped[list] = mapped_column(ARRAY(Text), nullable=False, default=list)
    recommendations: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=lambda: datetime.now(UTC).isoformat())
