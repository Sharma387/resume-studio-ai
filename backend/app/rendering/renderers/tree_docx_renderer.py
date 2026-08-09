"""RenderTree → DOCX renderer (Layout Engine).

Consumes a validated :class:`RenderNode` (RenderTree) and an optional
:class:`ThemePalette` and returns DOCX bytes. Maps RenderTree structure to
native Word structures: full-width regions become document paragraphs;
multi-region rows (e.g. main + sidebar) become a borderless table with one
cell per region; sections become headings with content; lists become bullets;
links become clickable hyperlinks; page size/margins come from the PAGE node.

This renderer is a pure RenderTree consumer: it knows nothing about Resume,
ContentView, LayoutDefinition, ComponentRegistry, TemplateRegistry, Jinja,
PreviewService, database, or API layers.
"""

from __future__ import annotations

from io import BytesIO

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor

from app.rendering.common.section_types import SECTION_REGISTRY
from app.rendering.theme.theme_palette import ThemePalette
from app.rendering.tree import NodeKind, RenderNode
from app.rendering.tree.validator import TreeValidator

REL_HYPERLINK = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"

#: Node kinds that are intentionally decorative in a Word resume; rendered as a
#: no-op (documented fallback). No substantive content is dropped.
_DECORATIVE_KINDS = {NodeKind.IMAGE, NodeKind.QR_CODE, NodeKind.SPACER}


def _hex_rgb(hex_color: str) -> RGBColor:
    value = hex_color.lstrip("#")
    return RGBColor(int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def _font_name(family: str) -> str:
    return family.split(",")[0].strip().strip("'\"")


def _group_rows(regions: list[RenderNode], max_span: int) -> list[list[RenderNode]]:
    """Group a page's region nodes into layout rows.

    A region spanning the full grid (== ``max_span``) is its own row; the
    remaining (partial-span) regions form one multi-region table row.
    """
    rows: list[list[RenderNode]] = []
    current: list[RenderNode] = []
    for region in regions:
        if region.span == max_span:
            if current:
                rows.append(current)
                current = []
            rows.append([region])
        else:
            current.append(region)
    if current:
        rows.append(current)
    return rows


class _Writer:
    """Writes DOCX content into the document body or an active table cell."""

    def __init__(self, document: Document, theme: ThemePalette | None) -> None:
        self.document = document
        self._container = document
        self._theme = theme
        self._apply_base_typography()

    # ── theme / fonts ─────────────────────────────────────────────────────────

    @property
    def _colors(self):
        return self._theme.tokens.colors if self._theme is not None else None

    def _apply_base_typography(self) -> None:
        if self._theme is None:
            return
        family = _font_name(self._theme.tokens.typography.family)
        normal = self.document.styles["Normal"]
        normal.font.name = family
        normal.font.size = Pt(10)

    def _color(self, kind: str):
        colors = self._colors
        if colors is None:
            return None
        return _hex_rgb(getattr(colors, kind))

    # ── container management ──────────────────────────────────────────────────

    def set_container(self, container) -> None:
        self._container = container

    @property
    def in_cell(self) -> bool:
        return self._container is not self.document

    # ── content helpers ───────────────────────────────────────────────────────

    def _add_paragraph(self):
        return self._container.add_paragraph()

    def paragraph(
        self,
        text: str,
        *,
        bold: bool = False,
        italic: bool = False,
        size: int | None = None,
        color: RGBColor | None = None,
        alignment=None,
        space_before: int = 0,
        space_after: int = 4,
    ):
        p = self._add_paragraph()
        run = p.add_run(text)
        run.bold = bold
        run.italic = italic
        if size is not None:
            run.font.size = Pt(size)
        if color is not None:
            run.font.color.rgb = color
        fmt = p.paragraph_format
        fmt.space_before = Pt(space_before)
        fmt.space_after = Pt(space_after)
        if alignment is not None:
            fmt.alignment = alignment
        return p

    def styled_text(self, text: str, classes: tuple[str, ...]) -> None:
        is_name = "resume-name" in classes
        is_strong = "resume-strong" in classes
        is_muted = "resume-muted" in classes
        size = 20 if is_name else (11 if is_strong else 10)
        color = self._color("primary") if is_name else (self._color("muted") if is_muted else self._color("text"))
        self.paragraph(text, bold=is_name or is_strong, size=size, color=color, space_after=(4 if is_strong else 2))

    def heading(self, text: str) -> None:
        self.paragraph(
            text.upper(),
            bold=True,
            size=11,
            color=self._color("primary"),
            space_before=10,
            space_after=4,
        )

    def time(self, text: str) -> None:
        self.paragraph(text, size=9, color=self._color("muted"), space_after=2)

    def bullet(self, text: str) -> None:
        p = self._add_paragraph()
        p.add_run("\u2022 ").font.size = Pt(10)
        p.add_run(text).font.size = Pt(10)
        fmt = p.paragraph_format
        fmt.left_indent = Mm(8)
        fmt.space_after = Pt(2)

    def hyperlink(self, text: str, url: str) -> None:
        part = self.document.part
        r_id = part.relate_to(url, REL_HYPERLINK, is_external=True)
        p = self._add_paragraph()
        hyperlink = OxmlElement("w:hyperlink")
        hyperlink.set(qn("r:id"), r_id)
        run_el = OxmlElement("w:r")
        r_pr = OxmlElement("w:rPr")
        accent = (self._theme.tokens.colors.accent.lstrip("#") if self._theme is not None else "1E40AF")
        color_el = OxmlElement("w:color")
        color_el.set(qn("w:val"), accent)
        r_pr.append(color_el)
        underline = OxmlElement("w:u")
        underline.set(qn("w:val"), "single")
        r_pr.append(underline)
        run_el.append(r_pr)
        t_el = OxmlElement("w:t")
        t_el.text = text
        run_el.append(t_el)
        hyperlink.append(run_el)
        p._p.append(hyperlink)


class RenderTreeDOCXRenderer:
    """Renders a validated RenderTree into DOCX bytes."""

    def __init__(self, *, validator: TreeValidator | None = None) -> None:
        self._validator = validator or TreeValidator()

    # ── Public API ────────────────────────────────────────────────────────────

    def render(self, tree: RenderNode, *, theme: ThemePalette | None = None) -> bytes:
        """Render ``tree`` (with optional ``theme``) into DOCX bytes."""
        self._validator.assert_valid(tree)
        document = Document()
        self._configure_page(document, tree)
        writer = _Writer(document, theme)
        page = self._first_page(tree)
        if page is not None:
            self._render_page(writer, page)
        buffer = BytesIO()
        document.save(buffer)
        return buffer.getvalue()

    # ── page ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _first_page(node: RenderNode) -> RenderNode | None:
        if node.kind is NodeKind.PAGE:
            return node
        for child in node.children:
            page = RenderTreeDOCXRenderer._first_page(child)
            if page is not None:
                return page
        return None

    def _configure_page(self, document: Document, tree: RenderNode) -> None:
        page = self._first_page(tree)
        if page is None:
            return
        section = document.sections[0]
        if page.page_size is not None:
            section.page_width = Mm(page.page_size.width_mm)
            section.page_height = Mm(page.page_size.height_mm)
        if page.margins is not None:
            section.top_margin = Mm(page.margins.top_mm)
            section.right_margin = Mm(page.margins.right_mm)
            section.bottom_margin = Mm(page.margins.bottom_mm)
            section.left_margin = Mm(page.margins.left_mm)

    def _render_page(self, writer: _Writer, page: RenderNode) -> None:
        regions = [child for child in page.children if child.kind is NodeKind.REGION]
        if not regions:
            return
        max_span = max(region.span for region in regions)
        for row in _group_rows(regions, max_span):
            if len(row) == 1:
                writer.set_container(writer.document)
                self._render_region(writer, row[0])
            else:
                table = writer.document.add_table(rows=1, cols=len(row))
                table.autofit = False
                self._size_table_columns(writer, table, row)
                for index, region in enumerate(row):
                    cell = table.cell(0, index)
                    writer.set_container(cell)
                    self._render_region(writer, region)
                writer.set_container(writer.document)

    @staticmethod
    def _size_table_columns(writer: _Writer, table, row: list[RenderNode]) -> None:
        section = writer.document.sections[0]
        usable = max(
            10.0,
            section.page_width.mm - section.left_margin.mm - section.right_margin.mm,
        )
        total = sum(region.span for region in row)
        for index, region in enumerate(row):
            table.cell(0, index).width = Mm((region.span / total) * usable)

    def _render_region(self, writer: _Writer, region: RenderNode) -> None:
        for child in region.children:
            self._render_node(writer, child)

    # ── node dispatch ─────────────────────────────────────────────────────────

    def _render_node(self, writer: _Writer, node: RenderNode) -> None:
        handler = getattr(self, f"_render_{node.kind.value}", None)
        if handler is not None:
            handler(writer, node)
        elif node.kind in _DECORATIVE_KINDS:
            return
        else:
            self._fallback(writer, node)

    def _render_section(self, writer: _Writer, node: RenderNode) -> None:
        title = self._section_title(node.content_ref)
        if title:
            writer.heading(title)
        for child in node.children:
            self._render_node(writer, child)

    def _render_block(self, writer: _Writer, node: RenderNode) -> None:
        for child in node.children:
            self._render_node(writer, child)

    def _render_grid(self, writer: _Writer, node: RenderNode) -> None:
        self._render_block(writer, node)

    def _render_row(self, writer: _Writer, node: RenderNode) -> None:
        self._render_block(writer, node)

    def _render_timeline(self, writer: _Writer, node: RenderNode) -> None:
        self._render_block(writer, node)

    def _render_list(self, writer: _Writer, node: RenderNode) -> None:
        for child in node.children:
            for leaf in child.children:
                if leaf.kind is NodeKind.BULLET:
                    writer.bullet(leaf.data.text)

    def _render_text(self, writer: _Writer, node: RenderNode) -> None:
        writer.styled_text(node.data.text, node.classes)

    def _render_paragraph(self, writer: _Writer, node: RenderNode) -> None:
        writer.paragraph(node.data.text, size=10)

    def _render_bullet(self, writer: _Writer, node: RenderNode) -> None:
        writer.bullet(node.data.text)

    def _render_time(self, writer: _Writer, node: RenderNode) -> None:
        writer.time(node.data.text)

    def _render_link(self, writer: _Writer, node: RenderNode) -> None:
        writer.hyperlink(node.data.text, node.data.url)

    def _render_icon(self, writer: _Writer, node: RenderNode) -> None:
        if node.data.label:
            writer.paragraph(node.data.label, size=10)

    def _render_badge(self, writer: _Writer, node: RenderNode) -> None:
        writer.paragraph(node.data.text, size=10)

    def _render_metric(self, writer: _Writer, node: RenderNode) -> None:
        label = f" {node.data.label}" if node.data.label else ""
        writer.paragraph(f"{node.data.value}{label}", size=10)

    def _render_divider(self, writer: _Writer, node: RenderNode) -> None:
        writer.paragraph("", space_after=2)

    def _render_page_break(self, writer: _Writer, node: RenderNode) -> None:
        if not writer.in_cell:
            writer.document.add_page_break()

    def _fallback(self, writer: _Writer, node: RenderNode) -> None:
        if node.data is not None and hasattr(node.data, "text") and node.data.text:
            writer.paragraph(node.data.text, size=10)

    @staticmethod
    def _section_title(content_ref: str | None) -> str:
        if not content_ref:
            return ""
        definition = SECTION_REGISTRY.get(content_ref)
        return definition.display_name if definition is not None else ""
