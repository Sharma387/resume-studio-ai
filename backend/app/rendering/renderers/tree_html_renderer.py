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
from app.rendering.tree import NodeKind, RenderNode
from app.rendering.tree.validator import TreeValidator

THEME_STYLE_ID = "rsai-theme"

_VOID_ELEMENTS = {"hr", "img", "br", "meta", "link", "input"}

#: Density → multiplier applied to the four spacing custom properties.
#: ``normal`` is ``1.0`` and emits nothing; the other levels scale the existing
#: spacing variables via ``calc`` so layout-specific values are preserved.
_DENSITY_SCALE: dict[str, float] = {
    "compact": 0.85,
    "normal": 1.0,
    "spacious": 1.2,
}

#: The custom properties the density scale multiplies.
_DENSITY_VARS: tuple[str, ...] = (
    "--section-spacing",
    "--block-spacing",
    "--inline-spacing",
    "--line-height",
)

#: Density scale → consumer overrides, one ``(var, property, selector, fallback)``
#: row per place a scaled custom property is actually consumed by a rule in
#: ``_css``. Density is applied additively at the *consumer* sites rather than
#: re-declaring the custom property itself: re-declaring ``--x`` in terms of
#: ``var(--x)`` is a custom-property cycle (guaranteed-invalid per the CSS
#: Variables spec), so it would silently break spacing in WeasyPrint/browsers.
#
#: ``selector`` contains a ``{d}`` placeholder for the density value and is
#: deliberately more specific than any ``.layout-*`` rule (and emitted later in
#: the stylesheet) so it wins the cascade for both the base and per-layout
#: ``margin``/``row-gap``/``line-height`` values.
_DENSITY_CONSUMERS: tuple[tuple[str, str, str, str], ...] = (
    ("--line-height", "line-height", ".resume.density-{d}", "1.5"),
    ("--line-height", "line-height", ".resume.density-{d} .resume-text", "1.5"),
    (
        "--section-spacing",
        "margin-bottom",
        ".resume.density-{d} .resume-section, .resume.density-{d} .resume-region-header",
        "14px",
    ),
    (
        "--block-spacing",
        "margin-bottom",
        ".resume.density-{d} .resume-block:not(:last-child)",
        "6px",
    ),
    ("--inline-spacing", "row-gap", ".resume.density-{d} .resume-page", "12px"),
)


class RenderTreeHTMLRenderer:
    """Translates a RenderTree into semantic, structurally-faithful HTML."""

    def __init__(self, *, validator: TreeValidator | None = None) -> None:
        self._validator = validator or TreeValidator()
        self._column_ratios: tuple[int, int] | None = None
        self._density: str | None = None

    # ── Public API ────────────────────────────────────────────────────────────

    def render(
        self,
        tree: RenderNode,
        *,
        theme: ThemePalette | None = None,
        density: str | None = None,
    ) -> str:
        """Render a validated RenderTree into a complete HTML document.

        ``density`` (``compact``/``normal``/``spacious``) scales the spacing
        custom properties via the existing CSS-variable mechanism. ``normal``
        (or ``None``) emits no density styling, preserving the current values.
        """
        self._validator.assert_valid(tree)
        self._density = density if density in _DENSITY_SCALE else None
        page = self._page_node(tree)
        self._column_ratios = page.column_ratios if page is not None else None
        gap_mm = page.gap_mm if page is not None else None
        css = self._css(
            theme,
            self._layout_key(tree),
            column_ratios=self._column_ratios,
            gap_mm=gap_mm,
            density=self._density,
        )
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

    @staticmethod
    def _layout_key(tree: RenderNode) -> str | None:
        """Derive the layout identity from the document's structural classes."""
        for cls in tree.classes:
            if cls.startswith("layout-"):
                return cls[len("layout-") :]
        return None

    @staticmethod
    def _page_node(tree: RenderNode) -> RenderNode | None:
        """Return the tree's single PAGE node, if present."""
        for child in tree.children:
            if child.kind is NodeKind.PAGE:
                return child
        return None

    # ── Node dispatch ─────────────────────────────────────────────────────────

    def _render_children(self, node: RenderNode) -> str:
        return "\n".join(child for child in (self._render_node(child) for child in node.children) if child)

    def _render_node(self, node: RenderNode) -> str:
        handler = getattr(self, f"_render_{node.kind.value}", None)
        if handler is None:
            return self._render_unknown(node)
        return handler(node)

    def _render_document(self, node: RenderNode) -> str:
        classes = " ".join(node.classes).strip()
        resume_cls = f"resume {classes}" if classes else "resume"
        if self._density and self._density != "normal":
            resume_cls = f"{resume_cls} density-{self._density}"
        return f'<main class="{resume_cls}">\n{self._render_children(node)}\n</main>'

    def _render_page(self, node: RenderNode) -> str:
        return f'<div class="resume-page">\n{self._render_children(node)}\n</div>'

    def _render_region(self, node: RenderNode) -> str:
        region = _html.escape(node.region or node.id)
        return (
            f'<div class="resume-region resume-region-{region}" '
            f'data-region="{region}" style="{self._region_style(node)}">\n'
            f"{self._render_children(node)}\n</div>"
        )

    def _region_style(self, node: RenderNode) -> str:
        """Region grid placement.

        Under an explicit ``column_ratios`` fr template the column regions are
        placed on concrete tracks (tree ``column_index``); full-width regions
        span all tracks. Otherwise the classic 12-column ``span N`` is used.
        """
        if self._column_ratios is not None:
            if node.column_index is not None:
                return f"grid-column: {node.column_index}"
            return "grid-column: 1 / -1"
        return f"grid-column: span {node.span}"

    def _render_section(self, node: RenderNode) -> str:
        section = _html.escape(node.content_ref or node.id)
        title = self._section_title(node.content_ref)
        heading = f'<h2 class="resume-section-title">{_html.escape(title)}</h2>\n' if title else ""
        return (
            f'<section class="resume-section resume-section-{section}" '
            f'data-section="{section}">\n{heading}{self._render_children(node)}\n</section>'
        )

    def _render_block(self, node: RenderNode) -> str:
        return f'<div class="{self._cls(node, "resume-block")}">\n{self._render_children(node)}\n</div>'

    def _render_grid(self, node: RenderNode) -> str:
        return f'<div class="resume-grid">\n{self._render_children(node)}\n</div>'

    def _render_row(self, node: RenderNode) -> str:
        return f'<div class="resume-row">\n{self._render_children(node)}\n</div>'

    def _render_list(self, node: RenderNode) -> str:
        items = []
        for child in node.children:
            text = " ".join(self._leaf_html(leaf) for leaf in child.children)
            items.append(f"<li>{text}</li>")
        return '<ul class="resume-list">\n' + "\n".join(items) + "\n</ul>"

    def _render_timeline(self, node: RenderNode) -> str:
        return f'<div class="resume-timeline">\n{self._render_children(node)}\n</div>'

    # ── Leaf units ────────────────────────────────────────────────────────────

    def _render_text(self, node: RenderNode) -> str:
        return f'<p class="{self._cls(node, "resume-text")}">{_html.escape(node.data.text)}</p>'

    def _render_paragraph(self, node: RenderNode) -> str:
        return f'<p class="{self._cls(node, "resume-text")}">{_html.escape(node.data.text)}</p>'

    def _render_bullet(self, node: RenderNode) -> str:
        return f"<li>{self._leaf_html(node)}</li>"

    def _render_link(self, node: RenderNode) -> str:
        return f'<a href="{_html.escape(node.data.url, quote=True)}">{_html.escape(node.data.text)}</a>'

    def _render_time(self, node: RenderNode) -> str:
        return f'<time class="{self._cls(node, "resume-time")}">{_html.escape(node.data.text)}</time>'

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
    def _cls(node: RenderNode, base: str) -> str:
        return f"{base} {' '.join(node.classes)}" if node.classes else base

    @staticmethod
    def _leaf_text(node: RenderNode) -> str:
        if node.data is not None and hasattr(node.data, "text"):
            return _html.escape(node.data.text)
        return ""

    @staticmethod
    def _leaf_html(node: RenderNode) -> str:
        if node.data is not None and getattr(node.data, "runs", ()):
            parts = []
            for run in node.data.runs:
                text = _html.escape(run.text)
                if run.bold:
                    text = f"<strong>{text}</strong>"
                parts.append(text)
            return "".join(parts)
        return RenderTreeHTMLRenderer._leaf_text(node)

    @staticmethod
    def _section_title(content_ref: str | None) -> str:
        if not content_ref:
            return ""
        definition = SECTION_REGISTRY.get(content_ref)
        return definition.display_name if definition is not None else ""

    @staticmethod
    def _css(
        theme: ThemePalette | None,
        layout_key: str | None,
        *,
        column_ratios: tuple[int, int] | None = None,
        gap_mm: float | None = None,
        density: str | None = None,
    ) -> str:
        root = "".join(
            f"{key}: {value};" for key, value in RenderTreeHTMLRenderer._theme_vars(theme).items()
        )
        root_block = f":root {{{root}}}" if root else ""
        if column_ratios is not None:
            columns = f"{column_ratios[0]}fr {column_ratios[1]}fr"
            gap = f"{gap_mm:g}mm" if gap_mm is not None else "0"
        else:
            columns = "repeat(12, 1fr)"
            gap = "0"
        density_block = RenderTreeHTMLRenderer._density_css(density)
        return f"""{root_block}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: var(--font-family, 'Inter', sans-serif); font-size: var(--font-size-base, 10pt);
       line-height: var(--line-height, 1.5); color: var(--text, #1e293b); background: var(--background, #ffffff); }}
.resume {{ max-width: 820px; margin: 0 auto; padding: 28px 24px; }}
.resume-page {{ display: grid; grid-template-columns: {columns};
       column-gap: {gap}; row-gap: var(--inline-spacing, 12px); }}
.resume-region {{ min-width: 0; }}
.resume-region-header {{ padding-bottom: 12px; margin-bottom: var(--section-spacing, 14px);
       border-bottom: 2px solid var(--primary, #2563eb); }}
.resume-section {{ margin-bottom: var(--section-spacing, 14px); }}
.resume-section-title {{ font-family: var(--heading-font-family, inherit); color: var(--primary, #2563eb);
       text-transform: uppercase; letter-spacing: 1px; font-size: 0.78em; font-weight: 700;
       border-bottom: 1px solid var(--border, #e2e8f0); padding-bottom: 3px; margin-bottom: 8px;
       break-after: avoid; }}
.resume-block {{ margin-bottom: var(--block-spacing, 6px); break-inside: avoid; }}
.resume-block:last-child {{ margin-bottom: 0; }}
.resume-text {{ margin-bottom: 2px; line-height: var(--line-height, 1.5); }}
.resume-name {{ font-size: 1.7em; font-weight: 700; color: var(--primary, #2563eb); letter-spacing: 0.5px; }}
.resume-strong {{ font-weight: 700; }}
.resume-muted {{ color: var(--muted, #64748b); }}
.resume-time {{ color: var(--muted, #64748b); font-size: 0.88em; display: block; margin-bottom: 2px; }}
.resume-list {{ margin: 2px 0 0 18px; padding: 0; break-inside: auto; }}
.resume-list li {{ margin-bottom: 1px; }}
.resume-badge {{ display: inline-block; border: var(--border-width, 0.5px) solid var(--border, #e2e8f0);
       border-radius: var(--radius, 0); padding: 1px 6px; margin-right: 4px; }}
a {{ color: var(--accent, #1e40af); word-break: break-all; }}
{RenderTreeHTMLRenderer._layout_css(layout_key)}
{density_block}@media (max-width: 640px) {{
  .resume-page {{ grid-template-columns: 1fr; }}
  .resume-region {{ grid-column: auto !important; }}
}}
@media print {{ body {{ background: #fff; padding: 0; }} .resume {{ box-shadow: none; max-width: none; padding: 0; }} }}
"""

    @staticmethod
    def _density_css(density: str | None) -> str:
        """Density overrides for the spacing custom properties (additive).

        ``normal`` (and ``None``) emits nothing so the default cascade — and
        the rendered bytes — are byte-identical to the non-density pipeline.

        ``compact``/``spacious`` scale the *consumers* of the four spacing
        custom properties (see :data:`_DENSITY_CONSUMERS`) with a
        ``calc(var(--x, <fallback>) * F)`` multiplier. This deliberately does
        not re-declare ``--x = calc(var(--x) * F)``: that is a self-referential
        custom-property cycle which the CSS Variables spec resolves to the
        guaranteed-invalid value, silently breaking spacing. The override
        selectors are additive rules (higher specificity, later in the
        stylesheet) so every existing rule keeps its exact source text.
        """
        if density is None or density not in _DENSITY_SCALE or density == "normal":
            return ""
        factor = _DENSITY_SCALE[density]
        rules = "\n".join(
            f"{selector.format(d=density)} {{ {prop}: calc(var({var}, {fallback}) * {factor}); }}"
            for var, prop, selector, fallback in _DENSITY_CONSUMERS
        )
        return f"{rules}\n"

    _LAYOUT_CSS: dict[str, str] = {
        # ── Executive Luxe: serif-led single column, hairlines, right dates ──
        "executive": """
.layout-executive { --font-family: 'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif;
                     --heading-font-family: Georgia, 'Times New Roman', Times, serif;
                     --block-spacing: 3.5mm; }
.layout-executive .resume { margin-top: 26px; }
.layout-executive .resume-region-header { border-bottom: none; padding-bottom: 12px; margin-bottom: 14px;
       text-align: center; }
.layout-executive .resume-region-header .resume-section-title { display: none; }
.layout-executive .resume-region-header .resume-name { font-family: var(--heading-font-family);
       font-size: 2.15em; font-weight: 400; color: var(--text); letter-spacing: 0.5px; text-transform: none; }
.layout-executive .resume-region-header .resume-muted { font-size: 0.95em; color: var(--primary); }
.layout-executive .resume-region-header::after { content: ""; display: block; margin: 14px auto 0 auto;
       width: 100%; border-top: 3px double var(--text); }
.layout-executive .resume-section-title { font-family: var(--heading-font-family); font-weight: 400;
       font-size: 0.74em; letter-spacing: 0; color: var(--text); border-bottom: none;
       padding-bottom: 0; margin-bottom: 10px; }
.layout-executive .resume-section-title::after { content: ""; display: block; width: 100%;
       border-top: 1px solid var(--border); margin-top: 4px; }
.layout-executive .resume-section { margin-bottom: 15px; }
.layout-executive .resume-strong { font-weight: 600; }
.layout-executive .resume-block { overflow: hidden; }
.layout-executive .resume-block:has(.resume-time) { display: flex; flex-wrap: wrap;
       justify-content: space-between; align-items: baseline; column-gap: 14px; }
.layout-executive .resume-block:has(.resume-time) .resume-strong { order: 0; }
.layout-executive .resume-block:has(.resume-time) .resume-time { order: 1; }
.layout-executive .resume-block:has(.resume-time) .resume-muted { order: 2; flex-basis: 100%; }
.layout-executive .resume-time { font-style: italic; font-family: var(--heading-font-family); font-size: 0.9em; }
.layout-executive .resume-list { list-style: none; padding-left: 0; margin-top: 4px; }
.layout-executive .resume-list li { padding-left: 13px; position: relative; margin-bottom: 2px; }
.layout-executive .resume-list li::before { content: "—"; position: absolute; left: 0; color: var(--primary); }
""",
        # ── Modern Two-Column: light-tint sidebar rail ──
        "sidebar": """
.layout-sidebar { --font-family: 'Inter', 'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif;
                  --section-spacing: 6mm; --block-spacing: 3.5mm; }
.layout-sidebar .resume-region-sidebar { background: var(--sidebar-bg, #f6f7f9);
       padding: 14px 16px 14px 28px; font-size: 0.9em; }
.layout-sidebar .resume-region-sidebar .resume-section-title { font-size: 0.7em; font-weight: 600;
       border-bottom: none; padding-bottom: 2px; letter-spacing: 0; }
.layout-sidebar .resume-region-sidebar .resume-section { margin-bottom: 14px; }
.layout-sidebar .resume-region-sidebar .resume-section-profile .resume-section-title { display: none; }
.layout-sidebar .resume-region-sidebar .resume-name { font-size: 1.35em; font-weight: 700;
       color: var(--text); letter-spacing: 0; line-height: 1.15; }
.layout-sidebar .resume-region-sidebar .resume-muted { font-size: 0.95em; }
.layout-sidebar .resume-region-sidebar .resume-list { list-style: none; padding-left: 0; margin: 2px 0 0; }
.layout-sidebar .resume-region-sidebar .resume-list li { margin-bottom: 3px; padding-bottom: 3px;
       border-bottom: 1px solid var(--border); }
.layout-sidebar .resume-region-sidebar .resume-list li:last-child { border-bottom: none; }
.layout-sidebar .resume-region-sidebar .resume-strong { font-weight: 600; }
.layout-sidebar .resume-region-sidebar a { word-break: normal; }
.layout-sidebar .resume-region-main .resume-section-title { font-size: 0.74em; letter-spacing: 0;
       border-bottom: none; padding-bottom: 5px; color: var(--text); }
.layout-sidebar .resume-region-main .resume-section-title::after { content: ""; display: block; width: 34px;
       border-top: 2px solid var(--primary); margin-top: 5px; }
.layout-sidebar .resume-block { overflow: hidden; }
.layout-sidebar .resume-block:has(.resume-time) { display: flex; flex-wrap: wrap;
       justify-content: space-between; align-items: baseline; column-gap: 12px; }
.layout-sidebar .resume-block:has(.resume-time) .resume-strong { order: 0; }
.layout-sidebar .resume-block:has(.resume-time) .resume-time { order: 1; }
.layout-sidebar .resume-block:has(.resume-time) .resume-muted { order: 2; flex-basis: 100%; }
.layout-sidebar .resume-time { font-size: 0.85em; }
.layout-sidebar .resume-strong { font-weight: 600; }
""",
        # ── Nordic Minimal: typography + whitespace ──
        "minimal": """
.layout-minimal { --font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }
.layout-minimal .resume { max-width: 690px; padding: 40px 30px; }
.layout-minimal .resume-section-profile .resume-section-title { display: none; }
.layout-minimal .resume-name { font-size: 1.95em; font-weight: 500; letter-spacing: 0.5px;
       color: var(--text); text-transform: none; }
.layout-minimal .resume-section-profile .resume-muted { font-size: 1em; }
.layout-minimal .resume-section { margin-bottom: 26px; }
.layout-minimal .resume-section:first-child { margin-top: 0; }
.layout-minimal .resume-section-title { font-weight: 500; letter-spacing: 0; font-size: 0.72em;
       text-transform: uppercase; color: var(--muted); border-bottom: none; padding-bottom: 0;
       margin-bottom: 12px; }
.layout-minimal .resume-strong { font-weight: 500; }
.layout-minimal .resume-muted { color: var(--muted); }
.layout-minimal .resume-list { list-style: none; padding-left: 0; margin-top: 3px; }
.layout-minimal .resume-list li { padding-left: 1em; position: relative; margin-bottom: 2px; }
.layout-minimal .resume-list li::before { content: "·"; position: absolute; left: 0.1em; color: var(--primary); }
.layout-minimal .resume-time { font-size: 0.85em; }
""",
        # ── Editorial: asymmetric magazine grid, serif display + kickers ──
        "modern": """
.layout-modern { --font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                  --heading-font-family: Georgia, 'Times New Roman', Times, serif; }
.layout-modern .resume-region-header { border-bottom: none; padding-bottom: 10px; margin-bottom: 14px; }
.layout-modern .resume-region-main { --block-spacing: 3.5mm; }
.layout-modern .resume-region-header .resume-section-title { display: none; }
.layout-modern .resume-region-header .resume-name { font-family: var(--heading-font-family);
       font-weight: 400; font-size: 2.5em; letter-spacing: 0; color: var(--text); text-transform: none; }
.layout-modern .resume-region-header .resume-muted { font-family: var(--heading-font-family);
       font-style: italic; font-size: 1.05em; color: var(--muted); }
.layout-modern .resume-region-header::after { content: ""; display: block; border-bottom: 6px solid var(--primary);
       width: 100%; margin-top: 14px; }
.layout-modern .resume-region-main .resume-section-title { font-family: var(--heading-font-family);
       font-weight: 400; font-size: 1.05em; text-transform: none; letter-spacing: 0;
       color: var(--text); border-bottom: none; margin-bottom: 10px; }
.layout-modern .resume-region-main .resume-section-title::before { content: ""; display: block; width: 30px;
       border-top: 2px solid var(--primary); margin-bottom: 5px; }
.layout-modern .resume-region-secondary { padding: 4px 0 0 28px; border-left: 1px solid var(--border); }
.layout-modern .resume-region-secondary .resume-section-title { font-size: 0.68em; letter-spacing: 0;
       text-transform: uppercase; font-weight: 600; color: var(--primary); border-bottom: none;
       padding-bottom: 0; padding-top: 8px; }
.layout-modern .resume-region-secondary .resume-section:first-child .resume-section-title { padding-top: 0; }
.layout-modern .resume-region-secondary .resume-muted { font-size: 0.92em; }
.layout-modern .resume-block { overflow: hidden; }
.layout-modern .resume-block:has(.resume-time) { display: flex; flex-wrap: wrap;
       justify-content: space-between; align-items: baseline; column-gap: 12px; }
.layout-modern .resume-block:has(.resume-time) .resume-strong { order: 0; }
.layout-modern .resume-block:has(.resume-time) .resume-time { order: 1; }
.layout-modern .resume-block:has(.resume-time) .resume-muted { order: 2; flex-basis: 100%; }
.layout-modern .resume-time { font-size: 0.85em; font-style: italic; }
.layout-modern .resume-strong { font-weight: 600; }
""",
        # ── Career Timeline: chronological rail with node indicators ──
        "timeline": """
.layout-timeline { --font-family: 'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif; }
.layout-timeline .resume-section-profile .resume-section-title { display: none; }
.layout-timeline .resume-name { font-size: 1.85em; font-weight: 700; letter-spacing: 0.5px; color: var(--text); }
.layout-timeline .resume-section-profile .resume-muted { color: var(--muted); }
.layout-timeline .resume-section-title { text-transform: uppercase; letter-spacing: 0; font-size: 0.72em;
       font-weight: 700; color: var(--text); border-bottom: none; padding-bottom: 0; }
.layout-timeline .resume-section-experience { position: relative; padding-left: 26px; }
.layout-timeline .resume-section:first-child { margin-top: 0; }
.layout-timeline .resume-section-experience::before { content: ""; position: absolute; left: 6px; top: 10px;
       bottom: 10px; width: 2px; background: var(--border); }
.layout-timeline .resume-section-experience .resume-block { position: relative; }
.layout-timeline .resume-section-experience .resume-block::before { content: ""; position: absolute;
       left: 1px; top: 6px; width: 12px; height: 12px; border-radius: 50%; background: var(--background);
       border: 2px solid var(--primary); }
.layout-timeline .resume-time { font-size: 0.85em; margin-bottom: 1px; color: var(--muted); }
.layout-timeline .resume-section-experience .resume-list li { margin-bottom: 2px; }
""",
        # ── Creative Professional: symmetric two-column, oversize name ──
        "classic": """
.layout-classic { --font-family: 'Inter', 'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif;
                  --section-spacing: 15px; --block-spacing: 3.5mm; }
.layout-classic .resume-region-main, .layout-classic .resume-region-secondary { padding: 0 6px; }
.layout-classic .resume-region-secondary { padding: 0 6px 0 18px; }
.layout-classic .resume-section-profile .resume-section-title { display: none; }
.layout-classic .resume-section-profile { padding-bottom: 10px; margin-bottom: 14px;
       border-bottom: 4px solid var(--primary); }
.layout-classic .resume-name { font-size: 2.3em; font-weight: 800; letter-spacing: 0;
       line-height: 1.05; color: var(--text); text-transform: none; }
.layout-classic .resume-section-title { font-weight: 700; text-transform: uppercase; letter-spacing: 0;
       font-size: 0.72em; color: var(--text); border-bottom: none; border-left: 4px solid var(--primary);
       padding-left: 9px; padding-bottom: 0; }
.layout-classic .resume-strong { font-weight: 600; }
.layout-classic .resume-time { color: var(--muted); font-size: 0.85em; }
.layout-classic .resume-list li { margin-bottom: 2px; }
.layout-classic .resume-muted { color: var(--muted); }
""",
    }

    @staticmethod
    def _layout_css(layout_key: str | None) -> str:
        if layout_key is None:
            return ""
        block = RenderTreeHTMLRenderer._LAYOUT_CSS.get(layout_key)
        return block if block is not None else ""

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
            "--sidebar-bg": RenderTreeHTMLRenderer._tint(tokens.colors.primary, 0.09),
        }

    @staticmethod
    def _tint(hex_color: str, ratio: float) -> str:
        """Blend a hex color toward white by ``ratio`` (0..1) for tinted rails."""
        value = hex_color.lstrip("#")
        parts = tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))
        mixed = tuple(round(channel + (255 - channel) * ratio) for channel in parts)
        return "#{:02x}{:02x}{:02x}".format(*mixed)
