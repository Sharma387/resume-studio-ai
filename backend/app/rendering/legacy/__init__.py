"""Legacy rendering compatibility adapter.

Everything the canonical application needs from the legacy rendering system
is reached through this package. Canonical modules must not import
``TemplateRegistry`` / ``PreviewService`` / ``ResumeRenderingService`` / Jinja
``HTMLRenderer`` / ReportLab ``pdf_templates`` directly; the compatibility
endpoints delegate here instead.

The deterministic ``template_id → layout_id`` mapping stays in
:mod:`app.rendering.legacy_templates` (a pure-data module with no rendering
imports). It is re-exported for convenience.

The submodules are imported lazily by the API layer so that importing this
package (or the canonical routers that delegate to it) does not initialize the
legacy renderer stack.
"""

from app.rendering.legacy_templates import (
    DEFAULT_LEGACY_THEME,
    LAYOUT_TO_TEMPLATE,
    LEGACY_TEMPLATE_IDS,
    TEMPLATE_TO_LAYOUT,
    UnknownLegacyTemplateError,
    resolve_legacy_selection,
    resolve_legacy_template,
)

__all__ = [
    "DEFAULT_LEGACY_THEME",
    "LAYOUT_TO_TEMPLATE",
    "LEGACY_TEMPLATE_IDS",
    "TEMPLATE_TO_LAYOUT",
    "UnknownLegacyTemplateError",
    "resolve_legacy_selection",
    "resolve_legacy_template",
]
