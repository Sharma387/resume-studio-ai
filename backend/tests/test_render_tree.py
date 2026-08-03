"""Tests for the Render Tree models (Layout Engine, Phase 0)."""

import pytest
from pydantic import ValidationError

from app.rendering.tree import (
    A4,
    LETTER,
    LinkData,
    NodeKind,
    PageBreakData,
    PageMargins,
    ParagraphData,
    RenderNode,
    TextData,
    TimeData,
)


def _text_node(id: str, text: str, **kw) -> RenderNode:
    return RenderNode(id=id, kind=NodeKind.TEXT, data=TextData(type="text", text=text), **kw)


def _minimal_document() -> RenderNode:
    """A minimal valid document: document → page → region → section → block → text."""
    return RenderNode(
        id="doc",
        kind=NodeKind.DOCUMENT,
        children=(
            RenderNode(
                id="p1",
                kind=NodeKind.PAGE,
                page_size=A4,
                margins=PageMargins(),
                children=(
                    RenderNode(
                        id="r-main",
                        kind=NodeKind.REGION,
                        region="main",
                        children=(
                            RenderNode(
                                id="s-summary",
                                kind=NodeKind.SECTION,
                                content_ref="summary",
                                region="main",
                                children=(
                                    RenderNode(
                                        id="b1",
                                        kind=NodeKind.BLOCK,
                                        children=(_text_node("t1", "Hello"),),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


# ── NodeKind ──────────────────────────────────────────────────────────────────


class TestNodeKind:
    def test_kinds_are_string_serializable(self):
        assert NodeKind.DOCUMENT.value == "document"
        assert NodeKind.PAGE_BREAK.value == "page_break"


# ── Valid tree construction ───────────────────────────────────────────────────


class TestConstruction:
    def test_minimal_document_is_valid(self):
        doc = _minimal_document()
        assert doc.kind is NodeKind.DOCUMENT
        assert doc.children[0].kind is NodeKind.PAGE

    def test_block_contains_text_leaf(self):
        block = RenderNode(
            id="b", kind=NodeKind.BLOCK, children=(_text_node("t", "x"),)
        )
        assert block.children[0].is_leaf is True

    def test_container_block_accepts_block_children(self):
        grid = RenderNode(
            id="g",
            kind=NodeKind.GRID,
            children=(
                RenderNode(id="b1", kind=NodeKind.BLOCK),
                RenderNode(id="b2", kind=NodeKind.BLOCK),
            ),
        )
        assert len(grid.children) == 2

    def test_page_break_allowed_at_page_and_region_level(self):
        page = RenderNode(
            id="p", kind=NodeKind.PAGE, page_size=A4, margins=PageMargins(),
            children=(RenderNode(id="pb", kind=NodeKind.PAGE_BREAK, data=PageBreakData(type="page_break")),),
        )
        region = RenderNode(
            id="r", kind=NodeKind.REGION, children=(
                RenderNode(id="pb2", kind=NodeKind.PAGE_BREAK, data=PageBreakData(type="page_break")),
            ),
        )
        assert page.children[0].data is not None
        assert region.children[0].data is not None


# ── Structural validation ─────────────────────────────────────────────────────


class TestStructuralValidation:
    def test_leaf_cannot_have_children(self):
        with pytest.raises(ValidationError):
            RenderNode(
                id="t", kind=NodeKind.TEXT, data=TextData(type="text", text="x"),
                children=(_text_node("t2", "y"),),
            )

    def test_text_requires_data(self):
        with pytest.raises(ValidationError):
            RenderNode(id="t", kind=NodeKind.TEXT)

    def test_structural_node_cannot_carry_data(self):
        with pytest.raises(ValidationError):
            RenderNode(id="s", kind=NodeKind.SECTION, data=TextData(type="text", text="x"))

    def test_document_cannot_contain_section(self):
        with pytest.raises(ValidationError):
            RenderNode(
                id="doc", kind=NodeKind.DOCUMENT,
                children=(RenderNode(id="s", kind=NodeKind.SECTION),),
            )

    def test_region_cannot_contain_block(self):
        with pytest.raises(ValidationError):
            RenderNode(
                id="r", kind=NodeKind.REGION,
                children=(RenderNode(id="b", kind=NodeKind.BLOCK),),
            )

    def test_section_cannot_contain_text_directly(self):
        with pytest.raises(ValidationError):
            RenderNode(
                id="s", kind=NodeKind.SECTION, children=(_text_node("t", "x"),)
            )

    def test_grid_cannot_contain_text(self):
        with pytest.raises(ValidationError):
            RenderNode(id="g", kind=NodeKind.GRID, children=(_text_node("t", "x"),))

    def test_page_requires_page_size_and_margins(self):
        with pytest.raises(ValidationError):
            RenderNode(id="p", kind=NodeKind.PAGE)

    def test_non_page_cannot_set_page_size(self):
        with pytest.raises(ValidationError):
            RenderNode(
                id="s", kind=NodeKind.SECTION, page_size=A4, margins=PageMargins()
            )

    def test_data_type_must_match_kind(self):
        with pytest.raises(ValidationError):
            RenderNode(id="t", kind=NodeKind.TEXT, data=ParagraphData(type="paragraph", text="x"))

    def test_link_requires_url(self):
        with pytest.raises(ValidationError):
            RenderNode(id="l", kind=NodeKind.LINK, data=LinkData(type="link", text="x"))

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            RenderNode(id="x", kind=NodeKind.TEXT, data=TextData(type="text", text="x"), bogus=1)

    def test_span_must_be_positive(self):
        with pytest.raises(ValidationError):
            RenderNode(id="x", kind=NodeKind.TEXT, data=TextData(type="text", text="x"), span=0)


# ── Round-trip serialization ──────────────────────────────────────────────────


class TestSerialization:
    def test_json_round_trip(self):
        doc = _minimal_document()
        raw = doc.model_dump_json()
        restored = RenderNode.model_validate_json(raw)
        assert restored == doc
        assert restored.children[0].page_size == A4

    def test_serialized_structure_is_stable(self):
        node = RenderNode(
            id="t", kind=NodeKind.TIME,
            data=TimeData(type="time", text="2020 – Present", start="2020", current=True),
        )
        raw = node.model_dump_json()
        assert '"kind":"time"' in raw
        assert '"current":true' in raw


# ── Properties & constants ────────────────────────────────────────────────────


class TestProperties:
    def test_is_leaf(self):
        assert _text_node("t", "x").is_leaf is True
        assert RenderNode(id="s", kind=NodeKind.SECTION).is_leaf is False

    def test_page_size_constants(self):
        assert A4.width_mm == 210.0
        assert A4.height_mm == 297.0
        assert LETTER.id == "Letter"
        assert LETTER.width_mm == 215.9
