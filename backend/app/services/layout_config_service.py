"""Layout-config persistence — the narrow seam to ``resume_variants.customization``.

The stored dict is namespaced so unrelated customization consumers share the
same column without collision::

    customization = {"layout_config": {...}, ...}

Keys set by other consumers are preserved on update (no wipe).
"""

from __future__ import annotations

from app.services.repositories.factory import get_variant_repository

LAYOUT_CONFIG_KEY = "layout_config"


def get_layout_config(resume_id: str, user_id: str) -> dict:
    """Return the stored ``layout_config`` payload (``{}`` when unset/corrupt)."""
    customization = get_variant_repository().get_customization(resume_id, user_id)
    value = customization.get(LAYOUT_CONFIG_KEY)
    return value if isinstance(value, dict) else {}


def set_layout_config(resume_id: str, user_id: str, layout_config: dict) -> dict:
    """Store ``layout_config`` namespaced in ``customization``, preserving other keys."""
    repo = get_variant_repository()
    customization = dict(repo.get_customization(resume_id, user_id))
    customization[LAYOUT_CONFIG_KEY] = dict(layout_config)
    repo.set_customization(resume_id, user_id, customization)
    return dict(layout_config)
