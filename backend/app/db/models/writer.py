from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WriterSuggestionModel(Base):
    __tablename__ = "writer_suggestions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resume_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    suggestion_type: Mapped[str] = mapped_column(String(50), nullable=False, default="phrasing")
    section: Mapped[str] = mapped_column(String(255), nullable=False)
    field_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    suggested_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.8)
    ai_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="ai_writer")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=lambda: datetime.now(UTC).isoformat())

    __table_args__ = (
        CheckConstraint("status IN ('pending','accepted','rejected')", name="ck_writer_suggestions_status"),
    )
