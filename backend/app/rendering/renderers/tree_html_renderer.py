"""RenderTree → HTML renderer (Layout Engine).

Consumes an already-resolved, validated :class:`RenderNode` (RenderTree) and a
:class:`ThemePalette` (optional) and emits semantic HTML. It determines
*how it looks*, never *what goes where*: section existence, placement, and
ordering were decided upstream by the TreeBuilder from the LayoutDefinition.

The renderer must NOT inspect the CVM, LayoutDefinition, or any registry. It
walks the tree and the theme tokens only.
"""

from __future__ import annotations

import html as _html

from app.rendering.common.section_types import SECTION_REGISTRY
from app.rendering.theme.theme_palette import ThemePalette
from app.rendering.tree import RenderNode
from app.rendering.tree.validator import TreeValidator

THEME_STYLE_ID = "rsai-theme"

_VOID_ELEMENTS = {"hr", "img", "br", "meta", "link", "input"}


class RenderTreeHTMLRenderer:
    """Translates a RenderTree into semantic, structurally-faithful HTML."""

    def __init__(self, *, validator: TreeValidator | None = None) -> None:
        self._validator = validator or TreeValidator()

    # ── Public API ────────────────────────────────────────────────────────────

    def render(self, tree: RenderNode, *, theme: ThemePalette | None = None) -> str:
        """Render a validated RenderTree into a complete HTML document."""
        self._validator.assert_valid(tree)
        css = self._css(theme)
        body = self._render_node(tree)
        return (
            "<!DOCTYPE html>\n"
            '<html lang="en">\n'
            "<head>\n"
            '<meta charset="UTF-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            f'<style id="{THEME_STYLE_ID}">\n{css}\n</style>\n'
            "</head>\n"
            "<body>\n"
            f"{body}\n"
            "</body>\n"
            "</html>"
        )

    # ── Node dispatch ─────────────────────────────────────────────────────────

    def _render_children(self, node: RenderNode) -> str:
        return "\n".join(child for child in (self._render_node(child) for child in node.children) if child)

    def _render_node(self, node: RenderNode) -> str:
        handler = getattr(self, f"_render_{node.kind.value}", None)
        if handler is None:
            return self._render_unknown(node)
        return handler(node)

    def _render_document(self, node: RenderNode) -> str:
        return f'<main class="resume">\n{self._render_children(node)}\n</main>'

    def _render_page(self, node: RenderNode) -> str:
        return f'<div class="resume-page">\n{self._render_children(node)}\n</div>'

    def _render_region(self, node: RenderNode) -> str:
        region = _html.escape(node.region or node.id)
        return (
            f'<div class="resume-region resume-region-{region}" '
            f'data-region="{region}" style="grid-column: span {node.span}">\n'
            f"{self._render_children(node)}\n</div>"
        )

    def _render_section(self, node: RenderNode) -> str:
        section = _html.escape(node.content_ref or node.id)
        title = self._section_title(node.content_ref)
        heading = f'<h2 class="resume-section-title">{_html.escape(title)}</h2>\n' if title else ""
        return (
            f'<section class="resume-section resume-section-{section}" '
            f'data-section="{section}">\n{heading}{self._render_children(node)}\n</section>'
        )

    def _render_block(self, node: RenderNode) -> str:
        return f'<div class="resume-block">\n{self._render_children(node)}\n</div>'

    def _render_grid(self, node: RenderNode) -> str:
        return f'<div class="resume-grid">\n{self._render_children(node)}\n</div>'

    def _render_row(self, node: RenderNode) -> str:
        return f'<div class="resume-row">\n{self._render_children(node)}\n</div>'

    def _render_list(self, node: RenderNode) -> str:
        return f'<ul class="resume-list">\n{self._render_children(node)}\n</ul>'

    def _render_timeline(self, node: RenderNode) -> str:
        return f'<div class="resume-timeline">\n{self._render_children(node)}\n</div>'

    # ── Leaf units ────────────────────────────────────────────────────────────

    def _render_text(self, node: RenderNode) -> str:
        return f'<p class="resume-text">{_html.escape(node.data.text)}</p>'

    def _render_paragraph(self, node: RenderNode) -> str:
        return f'<p class="resume-text">{_html.escape(node.data.text)}</p>'

    def _render_bullet(self, node: RenderNode) -> str:
        return f"<li>{_html.escape(node.data.text)}</li>"

    def _render_link(self, node: RenderNode) -> str:
        return f'<a href="{_html.escape(node.data.url, quote=True)}">{_html.escape(node.data.text)}</a>'

    def _render_time(self, node: RenderNode) -> str:
        return f'<time class="resume-time">{_html.escape(node.data.text)}</time>'

    def _render_icon(self, node: RenderNode) -> str:
        label = f" {_html.escape(node.data.label)}" if node.data.label else ""
        return f'<span class="resume-icon icon-{_html.escape(node.data.name)}" aria-hidden="true">{label}</span>'

    def _render_badge(self, node: RenderNode) -> str:
        return f'<span class="resume-badge">{_html.escape(node.data.text)}</span>'

    def _render_metric(self, node: RenderNode) -> str:
        label = f' <span class="resume-metric-label">{_html.escape(node.data.label)}</span>' if node.data.label else ""
        return f'<span class="resume-metric">{_html.escape(node.data.value)}{label}</span>'

    def _render_image(self, node: RenderNode) -> str:
        alt = _html.escape(node.data.alt or "", quote=True)
        return f'<img class="resume-image" src="{_html.escape(node.data.src, quote=True)}" alt="{alt}">'

    def _render_qr_code(self, node: RenderNode) -> str:
        label = _html.escape(node.data.label or node.data.value)
        return f'<span class="resume-qr">{label}</span>'

    def _render_divider(self, node: RenderNode) -> str:
        return '<hr class="resume-divider">'

    def _render_spacer(self, node: RenderNode) -> str:
        return '<div class="resume-spacer"></div>'

    def _render_page_break(self, node: RenderNode) -> str:
        return '<div class="resume-page-break"></div>'

    def _render_unknown(self, node: RenderNode) -> str:
        return ""

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _section_title(content_ref: str | None) -> str:
        if not content_ref:
            return ""
        definition = SECTION_REGISTRY.get(content_ref)
        return definition.display_name if definition is not None else ""

    @staticmethod
    def _css(theme: ThemePalette | None) -> str:
        root = "".join(f"{key}: {value};" for key, value in RenderTreeHTMLRenderer._theme_vars(theme).items())
        root_block = f":root {{{root}}}" if root else ""
        return f"""{root_block}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: var(--font-family, 'Inter', sans-serif); font-size: var(--font-size-base, 10pt);
       line-height: var(--line-height, 1.5); color: var(--text, #1e293b); background: var(--background, #ffffff); }}
.resume {{ max-width: 820px; margin: 0 auto; padding: 20px; }}
.resume-page {{ display: grid; grid-template-columns: repeat(12, 1fr); gap: var(--inline-spacing, 10px); }}
.resume-region {{ min-width: 0; }}
.resume-section {{ margin-bottom: var(--section-spacing, 14px); break-inside: avoid; }}
.resume-section-title {{ font-family: var(--heading-font-family, inherit); color: var(--primary, #2563eb);
       text-transform: uppercase; letter-spacing: 1px; font-size: 0.8em;
       border-bottom: 1px solid var(--border, #e2e8f0); padding-bottom: 3px; margin-bottom: 6px; }}
.resume-block {{ margin-bottom: var(--block-spacing, 6px); }}
.resume-text {{ margin-bottom: 2px; }}
.resume-badge {{ display: inline-block; border: var(--border-width, 0.5px) solid var(--border, #e2e8f0);
       border-radius: var(--radius, 0); padding: 1px 6px; margin-right: 4px; }}
a {{ color: var(--accent, #1e40af); }}
"""

    @staticmethod
    def _theme_vars(theme: ThemePalette | None) -> dict[str, str]:
        if theme is None:
            return {}
        tokens = theme.tokens
        size = tokens.typography.size_scale[0] if tokens.typography.size_scale else 10.0
        return {
            "--primary": tokens.colors.primary,
            "--on-primary": tokens.colors.on_primary,
            "--accent": tokens.colors.accent,
            "--background": tokens.colors.background,
            "--on-background": tokens.colors.on_background,
            "--text": tokens.colors.text,
            "--muted": tokens.colors.muted,
            "--border": tokens.colors.border,
            "--success": tokens.colors.success,
            "--font-family": tokens.typography.family,
            "--heading-font-family": tokens.typography.heading_family,
            "--font-size-base": f"{size}pt",
            "--line-height": str(tokens.typography.line_height),
            "--section-spacing": f"{tokens.spacing.section_mm}mm",
            "--block-spacing": f"{tokens.spacing.block_mm}mm",
            "--inline-spacing": f"{tokens.spacing.inline_mm}mm",
            "--border-width": f"{tokens.shape.border_width_mm}mm",
            "--radius": f"{tokens.shape.radius_mm}mm",
            "--accent-style": tokens.effects.accent_style,
            "--density": tokens.spacing.density,
        }
