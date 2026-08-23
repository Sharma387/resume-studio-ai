"""JSON variant repository — file-backed ``resume_variants.customization``.

Each resume stores one record at ``storage/variants/{resume_id}.json``
mirroring the ``ResumeVariantModel`` column semantics; the ``customization``
dict is the namespace consumers write into (e.g. ``{"layout_config": {...}}``)
and is the only field this repository mutates.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.services.repositories.interfaces import VariantRepository

VARIANTS_DIR = Path("storage") / "variants"


def _now() -> str:
    return datetime.now(UTC).isoformat()


class JsonVariantRepository(VariantRepository):
    def get_customization(self, resume_id: str, user_id: str) -> dict:
        record = self._load(resume_id, user_id)
        if record is None:
            return {}
        customization = record.get("customization")
        return customization if isinstance(customization, dict) else {}

    def set_customization(self, resume_id: str, user_id: str, customization: dict) -> None:
        record = self._load(resume_id, user_id) or {
            "id": uuid.uuid4().hex,
            "user_id": user_id,
            "resume_id": resume_id,
            "template_id": "executive-elite",
            "theme": "default",
            "name": "Default variant",
            "layout": "single-column",
            "created_at": _now(),
        }
        record["customization"] = customization
        record["updated_at"] = _now()
        path = VARIANTS_DIR / f"{resume_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=2), encoding="utf-8")

    def _load(self, resume_id: str, user_id: str) -> dict | None:
        path = VARIANTS_DIR / f"{resume_id}.json"
        if not path.exists():
            return None
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("user_id") != user_id:
            return None
        return record
