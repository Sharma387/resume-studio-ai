"""Tests for the Render Tree validator (Layout Engine, Phase 0)."""

import pytest

from app.rendering.tree import (
    A4,
    NodeKind,
    PageBreakData,
    PageMargins,
    RenderNode,
    TextData,
    TimeData,
    TreeValidationError,
    TreeValidator,
)

# ── Builders ──────────────────────────────────────────────────────────────────


def _text(id: str, text: str, content_ref: str | None = None, region: str | None = None) -> RenderNode:
    return RenderNode(
        id=id,
        kind=NodeKind.TEXT,
        content_ref=content_ref,
        region=region,
        data=TextData(type="text", text=text),
    )


def _block(id: str, units: tuple[RenderNode, ...] = (), region: str | None = None, span: int = 1) -> RenderNode:
    children = units if isinstance(units, tuple) else (units,)
    return RenderNode(id=id, kind=NodeKind.BLOCK, region=region, span=span, children=children)


def _section(
    id: str,
    content_ref: str,
    blocks: tuple[RenderNode, ...] = (),
    region: str | None = None,
) -> RenderNode:
    return RenderNode(id=id, kind=NodeKind.SECTION, content_ref=content_ref, region=region, children=tuple(blocks))


def _region(id: str, region_id: str, sections: tuple[RenderNode, ...] = (), span: int = 1) -> RenderNode:
    return RenderNode(id=id, kind=NodeKind.REGION, region=region_id, span=span, children=tuple(sections))


def _page(id: str, regions: tuple[RenderNode, ...] = ()) -> RenderNode:
    return RenderNode(id=id, kind=NodeKind.PAGE, page_size=A4, margins=PageMargins(), children=tuple(regions))


def _document(id: str, pages: tuple[RenderNode, ...] = ()) -> RenderNode:
    return RenderNode(id=id, kind=NodeKind.DOCUMENT, children=tuple(pages))


def _valid_doc() -> RenderNode:
    """A fully valid document: document → page → region → section → block → text."""
    return _document(
        "doc",
        pages=(
            _page(
                "p1",
                regions=(
                    _region(
                        "r-main",
                        "main",
                        sections=(
                            _section(
                                "s-summary",
                                "summary",
                                region="main",
                                blocks=(_block("b1", units=(_text("t1", "Hello", content_ref="summary")), region="main"),),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


@pytest.fixture
def validator() -> TreeValidator:
    return TreeValidator()


# ── Valid trees ───────────────────────────────────────────────────────────────


class TestValid:
    def test_minimal_document_is_valid(self, validator):
        assert validator.is_valid(_valid_doc())
        result = validator.validate(_valid_doc())
        assert result.valid
        assert result.errors == []

    def test_valid_sidebar_layout_spans(self, validator):
        doc = _document(
            "doc",
            pages=(
                _page(
                    "p1",
                    regions=(
                        _region("r-side", "sidebar", span=5),
                        _region("r-main", "main", span=7),
                    ),
                ),
            ),
        )
        assert validator.is_valid(doc)

    def test_region_id_reused_across_pages_is_allowed(self, validator):
        doc = _document(
            "doc",
            pages=(
                _page("p1", regions=(_region("r1a", "main"),)),
                _page("p2", regions=(_region("r2a", "main"),)),
            ),
        )
        assert validator.is_valid(doc)

    def test_leaf_region_optional_under_region(self, validator):
        doc = _valid_doc()
        assert validator.is_valid(doc)


# ── Root / ids ────────────────────────────────────────────────────────────────


class TestRootAndIds:
    def test_root_must_be_document(self, validator):
        node = _page("p1")
        assert not validator.is_valid(node)
        assert any("root must be a document" in e for e in validator.validate(node).errors)

    def test_duplicate_node_ids(self, validator):
        doc = _document(
            "doc",
            pages=(
                _page("p1", regions=(_region("r-main", "main"), _region("r-main2", "sidebar"))),
            ),
        )
        assert validator.is_valid(doc)

    def test_duplicate_leaf_ids(self, validator):
        doc = _document(
            "doc",
            pages=(
                _page(
                    "p1",
                    regions=(
                        _region(
                            "r-main",
                            "main",
                            sections=(
                                _section(
                                    "s1",
                                    "summary",
                                    region="main",
                                    blocks=(
                                        _block(
                                            "b1",
                                            region="main",
                                            units=(
                                                _text("t", "a", content_ref="summary"),
                                                _text("t", "b", content_ref="summary"),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        )
        result = validator.validate(doc)
        assert not result.valid
        assert any("duplicate node id 't'" in e for e in result.errors)


# ── Regions ───────────────────────────────────────────────────────────────────


class TestRegionIntegrity:
    def test_region_requires_id(self, validator):
        doc = _document("doc", pages=(_page("p1", regions=(RenderNode(id="r", kind=NodeKind.REGION),)),))
        result = validator.validate(doc)
        assert any("must declare a region id" in e for e in result.errors)

    def test_duplicate_region_id_within_page(self, validator):
        doc = _document(
            "doc",
            pages=(_page("p1", regions=(_region("r1", "main"), _region("r2", "main"))),),
        )
        result = validator.validate(doc)
        assert any("duplicated within a page" in e for e in result.errors)

    def test_unknown_region_reference(self, validator):
        doc = _document(
            "doc",
            pages=(
                _page(
                    "p1",
                    regions=(
                        _region(
                            "r-main",
                            "main",
                            sections=(_section("s1", "summary", region="bogus"),),
                        ),
                    ),
                ),
            ),
        )
        result = validator.validate(doc)
        assert any("unknown region 'bogus'" in e for e in result.errors)

    def test_region_mismatch_under_region(self, validator):
        doc = _document(
            "doc",
            pages=(
                _page(
                    "p1",
                    regions=(
                        _region("r-side", "sidebar"),
                        _region(
                            "r-main",
                            "main",
                            sections=(
                                _section(
                                    "s1",
                                    "summary",
                                    region="sidebar",
                                    blocks=(_block("b1", region="main"),),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        )
        result = validator.validate(doc)
        assert any("sits under region 'main'" in e for e in result.errors)

    def test_section_under_region_must_declare_region(self, validator):
        doc = _document(
            "doc",
            pages=(
                _page("p1", regions=(_region("r-main", "main", sections=(_section("s1", "summary"),)),)),
            ),
        )
        result = validator.validate(doc)
        assert any("must declare its region" in e for e in result.errors)

    def test_block_under_region_must_declare_region(self, validator):
        doc = _document(
            "doc",
            pages=(
                _page(
                    "p1",
                    regions=(
                        _region(
                            "r-main",
                            "main",
                            sections=(_section("s1", "summary", region="main", blocks=(_block("b1"),)),),
                        ),
                    ),
                ),
            ),
        )
        result = validator.validate(doc)
        assert any("must declare its region" in e for e in result.errors)

    def test_page_break_under_region_needs_no_region(self, validator):
        doc = _document(
            "doc",
            pages=(
                _page(
                    "p1",
                    regions=(
                        _region(
                            "r-main",
                            "main",
                            sections=(RenderNode(id="pb", kind=NodeKind.PAGE_BREAK, data=PageBreakData(type="page_break")),),
                        ),
                    ),
                ),
            ),
        )
        assert validator.is_valid(doc)


# ── Sections / text provenance ────────────────────────────────────────────────


class TestProvenance:
    def test_section_requires_content_ref(self, validator):
        doc = _document(
            "doc",
            pages=(
                _page(
                    "p1",
                    regions=(
                        _region("r-main", "main", sections=(RenderNode(id="s1", kind=NodeKind.SECTION, region="main"),)),
                    ),
                ),
            ),
        )
        result = validator.validate(doc)
        assert any("must declare a content reference" in e for e in result.errors)

    def test_text_requires_content_ref(self, validator):
        doc = _document(
            "doc",
            pages=(
                _page(
                    "p1",
                    regions=(
                        _region(
                            "r-main",
                            "main",
                            sections=(
                                _section(
                                    "s1",
                                    "summary",
                                    region="main",
                                    blocks=(_block("b1", region="main", units=(_text("t1", "x"),)),),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        )
        result = validator.validate(doc)
        assert any("must declare a content reference" in e for e in result.errors)

    def test_empty_text_rejected(self, validator):
        doc = _document(
            "doc",
            pages=(
                _page(
                    "p1",
                    regions=(
                        _region(
                            "r-main",
                            "main",
                            sections=(
                                _section(
                                    "s1",
                                    "summary",
                                    region="main",
                                    blocks=(
                                        _block(
                                            "b1",
                                            region="main",
                                            units=(_text("t1", "   ", content_ref="summary"),),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        )
        result = validator.validate(doc)
        assert any("must not be empty" in e for e in result.errors)


# ── Span budget ───────────────────────────────────────────────────────────────


class TestSpanBudget:
    def test_region_sum_within_budget(self, validator):
        doc = _document("doc", pages=(_page("p1", regions=(_region("a", "a", span=5), _region("b", "b", span=7))),))
        assert validator.is_valid(doc)

    def test_region_sum_exceeds_budget(self, validator):
        doc = _document("doc", pages=(_page("p1", regions=(_region("a", "a", span=7), _region("b", "b", span=7))),))
        result = validator.validate(doc)
        assert any("span sum 14 exceeds" in e for e in result.errors)

    def test_single_span_exceeds_budget(self, validator):
        doc = _document("doc", pages=(_page("p1", regions=(_region("a", "a", span=13),)),))
        result = validator.validate(doc)
        assert any("span 13 exceeds" in e for e in result.errors)

    def test_grid_block_spans_valid(self, validator):
        doc = _document(
            "doc",
            pages=(
                _page(
                    "p1",
                    regions=(
                        _region(
                            "r-main",
                            "main",
                            sections=(
                                _section(
                                    "s1",
                                    "projects",
                                    region="main",
                                    blocks=(
                                        RenderNode(
                                            id="g",
                                            kind=NodeKind.GRID,
                                            region="main",
                                            children=(_block("b1", span=6, region="main"), _block("b2", span=6, region="main")),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        )
        assert validator.is_valid(doc)

    def test_grid_block_spans_exceed_budget(self, validator):
        doc = _document(
            "doc",
            pages=(
                _page(
                    "p1",
                    regions=(
                        _region(
                            "r-main",
                            "main",
                            sections=(
                                _section(
                                    "s1",
                                    "projects",
                                    region="main",
                                    blocks=(
                                        RenderNode(
                                            id="g",
                                            kind=NodeKind.GRID,
                                            region="main",
                                            children=(_block("b1", span=7, region="main"), _block("b2", span=7, region="main")),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        )
        result = validator.validate(doc)
        assert any("span sum 14 exceeds" in e for e in result.errors)


# ── Text extraction & API surface ─────────────────────────────────────────────


class TestTextExtraction:
    def test_extract_text_returns_render_order(self, validator):
        doc = _document(
            "doc",
            pages=(
                _page(
                    "p1",
                    regions=(
                        _region(
                            "r-main",
                            "main",
                            sections=(
                                _section(
                                    "s1",
                                    "summary",
                                    region="main",
                                    blocks=(_block("b1", region="main", units=(_text("t1", "First", content_ref="summary"),)),),
                                ),
                                _section(
                                    "s2",
                                    "experience",
                                    region="main",
                                    blocks=(_block("b2", region="main", units=(_text("t2", "Second", content_ref="experience"),)),),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        )
        spans = validator.extract_text(doc)
        assert [s.text for s in spans] == ["First", "Second"]
        assert [s.content_ref for s in spans] == ["summary", "experience"]
        assert spans[0].node_id == "t1"

    def test_text_extraction_includes_kind(self, validator):
        node = RenderNode(
            id="tm",
            kind=NodeKind.TIME,
            content_ref="experience",
            data=TimeData(type="time", text="2020 – Present", current=True),
        )
        spans = validator.extract_text(RenderNode(id="b", kind=NodeKind.BLOCK, children=(node,)))
        assert spans[0].kind is NodeKind.TIME
        assert spans[0].text == "2020 – Present"


class TestApiSurface:
    def test_assert_valid_raises_on_invalid(self, validator):
        with pytest.raises(TreeValidationError):
            validator.assert_valid(_page("p1"))

    def test_assert_valid_passes_on_valid(self, validator):
        validator.assert_valid(_valid_doc())

    def test_node_count(self, validator):
        result = validator.validate(_valid_doc())
        assert result.node_count == 6  # doc, page, region, section, block, text

    def test_columns_must_be_positive(self):
        with pytest.raises(ValueError):
            TreeValidator(columns=0)
