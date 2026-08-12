"""Legacy template to layout migration boundary.

The authoritative, deterministic mapping from the legacy ``template_id``
concept to the new ``layout_id`` system. This is the single place that
resolves a legacy template selection into the Layout Engine; application code
must not re-implement template-to-layout resolution elsewhere.

The legacy TemplateRegistry, Jinja templates, HTMLRenderer, PreviewService,
and PDF services remain intact and operational; this module only provides the
compatibility mapping used to migrate users and URLs toward ``layout_id``.
"""

from __future__ import annotations

#: default theme applied when a legacy selection is resolved to a layout.
DEFAULT_LEGACY_THEME = "blue"

#: deterministic legacy template -> layout mapping.
TEMPLATE_TO_LAYOUT: dict[str, str] = {
    "executive": "executive",
    "finance-executive": "executive",
    "corporate-blue": "executive",
    "executive-elite": "sidebar",
    "consulting-pro": "modern",
    "software-engineer": "modern",
    "technology-lead": "modern",
    "creative-portfolio": "modern",
    "modern-ats": "classic",
    "government-standard": "classic",
    "healthcare-professional": "classic",
    "academic-research": "classic",
    "minimal-professional": "minimal",
}

#: all supported legacy template ids (the keys of the mapping, sorted).
LEGACY_TEMPLATE_IDS: tuple[str, ...] = tuple(sorted(TEMPLATE_TO_LAYOUT))

#: representative legacy ``template_id`` per canonical ``layout_id`` (reverse
#: compatibility boundary). Several legacy templates map onto the same layout;
#: the value below is the representative for that layout. ``timeline`` has no
#: legacy equivalent, so it maps to ``None``.
LAYOUT_TO_TEMPLATE: dict[str, str | None] = {
    "executive": "executive",
    "sidebar": "executive-elite",
    "modern": "consulting-pro",
    "classic": "modern-ats",
    "minimal": "minimal-professional",
    "timeline": None,
}


class UnknownLegacyTemplateError(KeyError):
    """Raised when a template id is not part of the supported mapping."""


def resolve_legacy_template(template_id: str) -> str:
    """Resolve a legacy ``template_id`` to the canonical ``layout_id``.

    Raises :class:`UnknownLegacyTemplateError` for unsupported ids. There is
    deliberately no fallback to an unrelated layout.
    """
    layout_id = TEMPLATE_TO_LAYOUT.get(template_id)
    if layout_id is None:
        raise UnknownLegacyTemplateError(
            f"legacy template '{template_id}' has no layout mapping"
        )
    return layout_id


def resolve_legacy_selection(template_id: str) -> tuple[str, str]:
    """Resolve a legacy selection to ``(layout_id, theme_id)``."""
    return resolve_legacy_template(template_id), DEFAULT_LEGACY_THEME
