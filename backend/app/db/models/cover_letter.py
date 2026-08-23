from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CoverLetterModel(Base):
    __tablename__ = "cover_letters"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resume_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("applications.id", ondelete="SET NULL"), nullable=True, index=True
    )
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hiring_manager: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tone: Mapped[str] = mapped_column(String(20), nullable=False, default="professional")
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    job_description_hash: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=lambda: datetime.now(UTC).isoformat())
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False, default=lambda: datetime.now(UTC).isoformat())

    __table_args__ = (
        CheckConstraint("tone IN ('professional','enthusiastic','formal','concise')", name="ck_cover_letters_tone"),
    )
