"""Unified export orchestration - one RenderTree, multiple output formats.

The ExportService builds the RenderTree once (Resume -> CVM -> RenderContext ->
TreeBuilder -> RenderTree) and dispatches it to the format-specific renderer (HTML / PDF /
DOCX). Each renderer is a pure RenderTree consumer; no business/content/layout
logic is duplicated per format.

Caching is intentionally deferred for this first implementation: PDF/DOCX are
generated on demand. A future phase may cache exports keyed by
(content_hash + layout stable id + theme stable id + format).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.models.resume import Resume
from app.rendering.builder import TreeBuilder
from app.rendering.components import ComponentRegistry
from app.rendering.content import cvm_from_resume
from app.rendering.context import OutputFormat, RenderContext, RenderState
from app.rendering.layout.effective import resolve_effective_layout
from app.rendering.layout.layout_config import LayoutConfig
from app.rendering.layout.layout_registry import LayoutRegistry
from app.rendering.layout_html import default_component_registry
from app.rendering.layout_preview import default_layout_registry, default_theme_registry
from app.rendering.renderers.tree_docx_renderer import RenderTreeDOCXRenderer
from app.rendering.renderers.tree_html_renderer import RenderTreeHTMLRenderer
from app.rendering.renderers.tree_pdf_renderer import RenderTreePDFRenderer
from app.rendering.theme.theme_registry import ThemeRegistry


class ExportFormat(str, Enum):
    """Output formats supported by the unified export API."""

    HTML = "html"
    PDF = "pdf"
    DOCX = "docx"


_FORMAT_TO_OUTPUT: dict[ExportFormat, OutputFormat] = {
    ExportFormat.HTML: OutputFormat.HTML,
    ExportFormat.PDF: OutputFormat.PDF,
    ExportFormat.DOCX: OutputFormat.DOCX,
}

_RENDERERS: dict[OutputFormat, type] = {
    OutputFormat.HTML: RenderTreeHTMLRenderer,
    OutputFormat.PDF: RenderTreePDFRenderer,
    OutputFormat.DOCX: RenderTreeDOCXRenderer,
}

_CONTENT_TYPES: dict[ExportFormat, str] = {
    ExportFormat.HTML: "text/html; charset=utf-8",
    ExportFormat.PDF: "application/pdf",
    ExportFormat.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class ExportFormatError(ValueError):
    """Raised when an unsupported output format is requested."""


@dataclass(frozen=True)
class ExportResult:
    """Rendered artifact bytes plus response metadata."""

    content: bytes
    content_type: str
    filename: str


class ExportService:
    """Orchestrates Resume -> CVM -> RenderContext -> TreeBuilder -> RenderTree -> renderer."""

    def __init__(
        self,
        *,
        layout_registry: LayoutRegistry | None = None,
        theme_registry: ThemeRegistry | None = None,
        component_registry: ComponentRegistry | None = None,
    ) -> None:
        self._layouts = layout_registry or default_layout_registry()
        self._themes = theme_registry or default_theme_registry()
        self._components = component_registry or default_component_registry()

    def export(
        self,
        resume: Resume,
        *,
        layout_id: str,
        theme_id: str,
        output_format: ExportFormat,
        layout_config: LayoutConfig | None = None,
        auto_balance: bool = False,
        base_config: LayoutConfig | None = None,
    ) -> ExportResult:
        """Build the RenderTree once and render it in the requested format.

        ``layout_config``, when provided, resolves a layout variant on top of
        the base ``layout_id``; otherwise the base layout is used unchanged.
        If ``auto_balance`` is True and no explicit config is provided, the
        layout is auto-balanced based on the resume content. ``base_config`` is
        the persisted per-resume configuration; when supplied it seeds the
        balancer's ``density``/``gap``/``sections`` preferences (mode/ratio/
        sidebar are still chosen by the balancer). It is ignored for explicit
        ``layout_config`` and when auto-balance is disabled.
        """
        base = self._layouts.resolve(layout_id)  # raises LayoutLookupError

        cvm = cvm_from_resume(resume)

        # Single source of truth for effective-layout precedence (P3.9 seam).
        layout, effective_config = resolve_effective_layout(
            base,
            cvm,
            explicit_config=layout_config,
            auto_balance=auto_balance,
            base_config=base_config,
        )

        theme = self._themes.resolve(theme_id)  # raises ThemeLookupError
        output = _FORMAT_TO_OUTPUT.get(output_format)
        renderer_cls = _RENDERERS.get(output)
        if output is None or renderer_cls is None:
            raise ExportFormatError(f"Unsupported output format '{output_format.value}'")

        context = RenderContext(layout=layout, theme=theme, state=RenderState(output_format=output))
        tree = TreeBuilder(self._components).build(cvm, context)

        renderer = renderer_cls()
        if output in (OutputFormat.HTML, OutputFormat.PDF):
            density = effective_config.density.value if effective_config is not None else None
            content = renderer.render(tree, theme=theme, density=density)
        else:
            content = renderer.render(tree, theme=theme)
        if isinstance(content, str):
            content = content.encode("utf-8")

        filename = f"resume-{_safe_slug(layout_id)}.{output_format.value}"
        return ExportResult(
            content=content,
            content_type=_CONTENT_TYPES[output_format],
            filename=filename,
        )


def _safe_slug(value: str) -> str:
    slug = "".join(ch for ch in value if ch.isalnum() or ch in "-_").strip("-")
    return slug or "resume"


_service = ExportService()


def export_resume(
    resume: Resume,
    *,
    layout_id: str,
    theme_id: str,
    output_format: ExportFormat,
    layout_config: LayoutConfig | None = None,
    auto_balance: bool = False,
    base_config: LayoutConfig | None = None,
) -> ExportResult:
    """Module-level convenience delegating to the default :class:`ExportService`."""
    return _service.export(
        resume,
        layout_id=layout_id,
        theme_id=theme_id,
        output_format=output_format,
        layout_config=layout_config,
        auto_balance=auto_balance,
        base_config=base_config,
    )
