"""Legacy template lookup — the only place canonical code reaches the legacy
``TemplateRegistry`` for listing/metadata. Kept out of canonical rendering
code; used solely by the legacy-compatibility API endpoints.
"""

from __future__ import annotations

from typing import Any

from app.rendering.legacy_templates import UnknownLegacyTemplateError, resolve_legacy_template
from app.rendering.registry.template_registry import TemplateRegistry


def list_legacy_templates() -> list[dict[str, Any]]:
    """List all legacy template manifests."""
    return TemplateRegistry().list()


def get_legacy_template(template_id: str) -> dict[str, Any] | None:
    """Return a legacy template's manifest dict, or ``None`` if unknown."""
    registry = TemplateRegistry()
    pkg = registry.get(template_id)
    if pkg is None:
        return None
    return registry._manifest_to_dict(pkg)


def template_exists(template_id: str) -> bool:
    """True if the legacy template id is discoverable in the registry."""
    return TemplateRegistry().get(template_id) is not None


def get_layout_id(template_id: str) -> str | None:
    """Resolve a legacy ``template_id`` to its canonical ``layout_id``.

    Returns ``None`` for unknown ids (the caller decides how to map that).
    """
    try:
        return resolve_legacy_template(template_id)
    except UnknownLegacyTemplateError:
        return None
