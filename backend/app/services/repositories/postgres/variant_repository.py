"""PostgreSQL variant repository — persistence against ``resume_variants``.

Uses ``ResumeVariantModel.customization`` (JSONB). If a resume has no variant
row yet, one is created on first write (the "default variant" contract),
mirroring how the frontend treats a resume's customization as scoped to a
single implicit variant.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.db.database import get_sync_session
from app.db.models.variant import ResumeVariantModel
from app.services.repositories.interfaces import VariantRepository


def _now() -> str:
    return datetime.now(UTC).isoformat()


class PostgresVariantRepository(VariantRepository):
    def get_customization(self, resume_id: str, user_id: str) -> dict:
        session = get_sync_session()
        try:
            model = self._get_first(session, resume_id, user_id)
            return dict(model.customization) if model else {}
        finally:
            session.close()

    def set_customization(self, resume_id: str, user_id: str, customization: dict) -> None:
        session = get_sync_session()
        try:
            model = self._get_first(session, resume_id, user_id)
            if model is None:
                model = ResumeVariantModel(
                    id=uuid.uuid4().hex,
                    user_id=user_id,
                    resume_id=resume_id,
                    template_id="executive-elite",
                    theme="default",
                    name="Default variant",
                    layout="single-column",
                    customization=customization,
                    created_at=_now(),
                    updated_at=_now(),
                )
                session.add(model)
            else:
                model.customization = customization
                model.updated_at = _now()
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def _get_first(session, resume_id: str, user_id: str) -> ResumeVariantModel | None:
        return (
            session.query(ResumeVariantModel)
            .filter(
                ResumeVariantModel.resume_id == resume_id,
                ResumeVariantModel.user_id == user_id,
            )
            .order_by(ResumeVariantModel.created_at.asc())
            .first()
        )
