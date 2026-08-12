"""RenderTree → PDF renderer (Layout Engine).

Consumes a validated :class:`RenderNode` (RenderTree) and an optional
:class:`ThemePalette` and returns PDF bytes. The tree is rendered to the same
semantic HTML used by the HTML preview (via :class:`RenderTreeHTMLRenderer`)
and converted with WeasyPrint, so content, ordering, region/column placement,
typography hierarchy, spacing, theme colors, links, and multi-page flow all
correspond to the preview. Page size/margins are taken from the RenderTree's
PAGE node.

This renderer is a pure RenderTree consumer: it knows nothing about Resume,
ContentView, LayoutDefinition, ComponentRegistry, the retired legacy
template/Jinja stack, PreviewService, database, or API layers.
"""

from __future__ import annotations

from app.rendering.renderers.tree_html_renderer import RenderTreeHTMLRenderer
from app.rendering.theme.theme_palette import ThemePalette
from app.rendering.tree import NodeKind, RenderNode
from app.rendering.tree.validator import TreeValidator


class RenderTreePDFRenderer:
    """Renders a validated RenderTree to PDF bytes."""

    def __init__(self, *, validator: TreeValidator | None = None) -> None:
        self._validator = validator or TreeValidator()
        self._html_renderer = RenderTreeHTMLRenderer(validator=self._validator)

    # ── Public API ────────────────────────────────────────────────────────────

    def render(self, tree: RenderNode, *, theme: ThemePalette | None = None) -> bytes:
        """Render ``tree`` (with optional ``theme``) into PDF bytes."""
        self._validator.assert_valid(tree)
        html = self._html_renderer.render(tree, theme=theme)
        html = self._inject_page_geometry(html, tree)
        return _weasyprint_pdf(html)

    # ── Page geometry ─────────────────────────────────────────────────────────

    @staticmethod
    def _inject_page_geometry(html: str, tree: RenderNode) -> str:
        page = _first_page(tree)
        if page is None:
            return html
        size = page.page_size.id if page.page_size is not None else "A4"
        margins = page.margins
        if margins is None:
            return html
        margin = (
            f"{margins.top_mm}mm {margins.right_mm}mm {margins.bottom_mm}mm {margins.left_mm}mm"
        )
        style = f"<style>@page {{ size: {size}; margin: {margin}; }}</style>"
        return html.replace("</head>", f"{style}</head>", 1)


def _first_page(node: RenderNode) -> RenderNode | None:
    if node.kind is NodeKind.PAGE:
        return node
    for child in node.children:
        page = _first_page(child)
        if page is not None:
            return page
    return None


def _weasyprint_pdf(html: str) -> bytes:
    import weasyprint

    document = weasyprint.HTML(string=html)
    return document.write_pdf()
