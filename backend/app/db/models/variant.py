from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ResumeVariantModel(Base):
    __tablename__ = "resume_variants"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resume_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    template_id: Mapped[str] = mapped_column(String(64), nullable=False, default="executive-elite")
    theme: Mapped[str] = mapped_column(String(32), nullable=False, default="default")
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    layout: Mapped[str] = mapped_column(String(32), nullable=False, default="single-column")
    customization: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[str] = mapped_column(
        String(32), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: Mapped[str] = mapped_column(
        String(32), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat()
    )


class ResumeVersionSnapshotModel(Base):
    __tablename__ = "resume_version_snapshots"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    variant_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("resume_variants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_name: Mapped[str] = mapped_column(String(255), nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[str] = mapped_column(
        String(32), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat()
    )
