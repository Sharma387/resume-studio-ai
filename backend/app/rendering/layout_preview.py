"""Layout engine preview orchestration (additive; legacy path untouched).

Bridges the new rendering pipeline into Resume Studio preview:

    Resume
      ↓
    ContentView (cvm_from_resume)
      ↓
    RenderContext(layout, theme, state=preview)
      ↓
    TreeBuilder
      ↓
    RenderTree
      ↓
    RenderTreeHTMLRenderer
      ↓
    HTML (written to the shared preview cache, served by the preview file API)

The retired legacy template/Jinja preview path is not involved here. Layout and theme
are resolved through the new Layout/Theme registries; unknown ids raise their
respective lookup errors (mapped to 404 by the API).
"""

from __future__ import annotations

import hashlib

from app.core.logging import get_logger
from app.models.resume import Resume
from app.rendering.content import cvm_from_resume
from app.rendering.context import RenderMode, RenderState
from app.rendering.layout.layout_config import LayoutConfig
from app.rendering.layout.layout_definition import LayoutDefinition
from app.rendering.layout.layout_registry import LayoutRegistry
from app.rendering.layout.layout_resolver import LayoutResolver
from app.rendering.layout.reference_layouts import REFERENCE_LAYOUTS
from app.rendering.layout_html import render_layout_html
from app.rendering.paths import PREVIEW_DIR
from app.rendering.theme.reference_themes import REFERENCE_THEMES
from app.rendering.theme.theme_registry import ThemeRegistry

logger = get_logger(__name__)

#: Default theme applied when the request does not specify one.
DEFAULT_THEME_ID = REFERENCE_THEMES[0].theme_id


def default_layout_registry() -> LayoutRegistry:
    """A LayoutRegistry populated with the built-in reference layouts."""
    registry = LayoutRegistry()
    for layout in REFERENCE_LAYOUTS:
        registry.register(layout)
    return registry


def default_theme_registry() -> ThemeRegistry:
    """A ThemeRegistry populated with the built-in reference themes."""
    registry = ThemeRegistry()
    for theme in REFERENCE_THEMES:
        registry.register(theme)
    return registry


_LAYOUT_REGISTRY = default_layout_registry()
_THEME_REGISTRY = default_theme_registry()


def resolve_preview_layout(
    layout_id: str,
    config: LayoutConfig | None = None,
) -> LayoutDefinition:
    """Resolve ``layout_id`` (+ optional ``LayoutConfig``) into a concrete layout.

    Without a config this returns the base reference layout unchanged. With a
    config the :class:`LayoutResolver` derives a new definition; an impossible
    preference raises :class:`LayoutResolverError`.
    """
    base = _LAYOUT_REGISTRY.resolve(layout_id)

    if config is None:
        return base
    return LayoutResolver().resolve(base, config)


def render_layout_preview_html(
    resume: Resume,
    layout_id: str,
    theme_id: str | None = None,
    layout: LayoutDefinition | None = None,
    density: str | None = None,
) -> str:
    """Render ``resume`` through a layout + ``theme_id`` into HTML.

    When ``layout`` is supplied it is used as-is (typically a resolved variant);
    otherwise the base reference layout is resolved from ``layout_id``.
    ``density`` scales the spacing custom properties when not ``normal``.
    """
    layout = layout if layout is not None else _LAYOUT_REGISTRY.resolve(layout_id)
    theme = _THEME_REGISTRY.resolve(theme_id or DEFAULT_THEME_ID)
    cvm = cvm_from_resume(resume)
    return render_layout_html(cvm, layout, theme, state=RenderState(mode=RenderMode.PREVIEW), density=density)


def generate_layout_preview(
    resume: Resume,
    layout_id: str,
    theme_id: str | None = None,
    layout: LayoutDefinition | None = None,
    density: str | None = None,
) -> str:
    """Generate (and cache) an HTML preview file, returning its path.

    The cache key covers the resume content hash + the concrete layout + theme
    + density so identical requests (including resolved layout variants) reuse
    the same file (deterministic). When ``layout`` is supplied it is used as-is.
    Otherwise the base reference layout is resolved.
    """
    cvm = cvm_from_resume(resume)
    if layout is not None:
        # Explicit layout provided — use as-is
        pass
    else:
        layout = _LAYOUT_REGISTRY.resolve(layout_id)
    theme = _THEME_REGISTRY.resolve(theme_id or DEFAULT_THEME_ID)

    cache_key = hashlib.md5(
        f"{cvm.content_hash}{layout.model_dump_json()}{theme.theme_id}{density}".encode()
    ).hexdigest()
    preview_path = PREVIEW_DIR / f"{cache_key}.html"
    if preview_path.exists():
        logger.info("Layout preview cache hit", layout_id=layout_id, theme_id=theme.theme_id, key=cache_key)
        return str(preview_path)

    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    preview_path.write_text(
        render_layout_preview_html(resume, layout_id, theme.theme_id, layout=layout, density=density),
        encoding="utf-8",
    )
    logger.info("Layout preview generated", layout_id=layout_id, theme_id=theme.theme_id, key=cache_key)
    return str(preview_path)
