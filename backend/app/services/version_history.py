"""Version history and autosave for resume designs."""

import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

_versions: dict[str, list[dict[str, Any]]] = {}
_autosave: dict[str, dict[str, Any]] = {}


def save_version(variant_id: str, resume_data: dict, label: str | None = None) -> dict[str, Any]:
    """Save a named version of a resume variant."""
    if variant_id not in _versions:
        _versions[variant_id] = []
    version = {
        "id": uuid.uuid4().hex,
        "variant_id": variant_id,
        "label": label or f"Version {len(_versions[variant_id]) + 1}",
        "resume_data": resume_data,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _versions[variant_id].append(version)
    logger.info("Version saved", variant_id=variant_id, label=version["label"])
    return version


def list_versions(variant_id: str) -> list[dict[str, Any]]:
    return _versions.get(variant_id, [])


def get_version(variant_id: str, version_id: str) -> dict[str, Any] | None:
    for v in _versions.get(variant_id, []):
        if v["id"] == version_id:
            return v
    return None


def autosave(variant_id: str, resume_data: dict) -> None:
    _autosave[variant_id] = {
        "resume_data": resume_data,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }


def get_autosave(variant_id: str) -> dict[str, Any] | None:
    return _autosave.get(variant_id)
