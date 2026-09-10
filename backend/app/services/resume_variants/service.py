"""Resume Variants — multiple customised versions of the same parsed resume."""

import uuid
from datetime import UTC, datetime
from typing import Any

from app.core.logging import get_logger
from app.models.resume import Resume

logger = get_logger(__name__)

# In-memory storage for variants (can be replaced with DB later)
_variants: dict[str, dict[str, Any]] = {}


def create(
    original_resume: Resume, user_id: str, name: str, template_id: str | None = None, theme: str | None = None
) -> dict[str, Any]:
    """Create a resume variant based on the original parsed resume."""
    variant_id = uuid.uuid4().hex
    variant: dict[str, Any] = {
        "id": variant_id,
        "user_id": user_id,
        "name": name,
        "original_resume_id": original_resume.id if hasattr(original_resume, "id") else None,
        "template_id": template_id or "executive-elite",
        "theme": theme or "default",
        "sections": _default_sections(original_resume),
        "customisations": {},
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }
    _variants[variant_id] = variant
    logger.info("Resume variant created", variant_id=variant_id, name=name)
    return variant


def get(variant_id: str) -> dict[str, Any] | None:
    return _variants.get(variant_id)


def list_by_user(user_id: str) -> list[dict[str, Any]]:
    return [v for v in _variants.values() if v["user_id"] == user_id]


def update(variant_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    variant = _variants.get(variant_id)
    if variant is None:
        return None
    for key in ("name", "template_id", "theme", "sections", "customisations"):
        if key in updates:
            variant[key] = updates[key]
    variant["updated_at"] = datetime.now(UTC).isoformat()
    return variant


def delete(variant_id: str) -> bool:
    if variant_id in _variants:
        del _variants[variant_id]
        return True
    return False


def _default_sections(resume: Resume) -> list[dict[str, Any]]:
    sections = []
    if resume.summary:
        sections.append({"id": "summary", "name": "Professional Summary", "visible": True})
    if resume.experience:
        sections.append({"id": "experience", "name": "Experience", "visible": True})
    if resume.education:
        sections.append({"id": "education", "name": "Education", "visible": True})
    if resume.skills:
        sections.append({"id": "skills", "name": "Skills", "visible": True})
    if resume.projects:
        sections.append({"id": "projects", "name": "Projects", "visible": True})
    if resume.certifications:
        sections.append({"id": "certifications", "name": "Certifications", "visible": True})
    return sections
