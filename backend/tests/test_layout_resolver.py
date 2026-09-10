"""Tests for the LayoutResolver (Layout Engine, P3.2)."""

import pytest
from pydantic import ValidationError

from app.rendering.layout import (
    REFERENCE_LAYOUTS,
    GridConfig,
    LayoutConfig,
    LayoutDefinition,
    LayoutResolver,
    LayoutResolverError,
    SectionLayoutConfig,
)
from app.rendering.layout.layout_regions import RegionType

RESOLVER = LayoutResolver()


def _layout(layout_id: str) -> LayoutDefinition:
    return next(layout for layout in REFERENCE_LAYOUTS if layout.layout_id == layout_id)


def _region_order(result: LayoutDefinition) -> list[str]:
    return [region.identifier for region in sorted(result.regions, key=lambda r: (r.ordering, r.identifier))]


def _rule(result: LayoutDefinition, section: str):
    return next(rule for rule in result.placement_rules if rule.section == section)


class TestSingleColumn:
    def test_single_column_drops_sidebar(self):
        result = RESOLVER.resolve(_layout("sidebar"), LayoutConfig(mode="single"))
        assert not any(r.region_type is RegionType.SIDEBAR for r in result.regions)
        mains = [r for r in result.regions if r.region_type is RegionType.MAIN]
        assert len(mains) == 1
        assert mains[0].column_span == result.grid.columns
        assert result.capabilities.sidebar is False
        assert result.metadata.supports_sidebar is False

    def test_single_column_drops_secondary(self):
        result = RESOLVER.resolve(_layout("modern"), LayoutConfig(mode="single"))
        assert not any(r.region_type is RegionType.CUSTOM for r in result.regions)
        mains = [r for r in result.regions if r.region_type is RegionType.MAIN]
        assert len(mains) == 1
        assert mains[0].column_span == 12

    def test_single_column_preserves_header(self):
        result = RESOLVER.resolve(_layout("executive"), LayoutConfig())
        types = [r.region_type for r in result.regions]
        assert RegionType.HEADER in types
        assert RegionType.MAIN in types

    def test_single_column_repoints_rules_to_main(self):
        result = RESOLVER.resolve(_layout("modern"), LayoutConfig(mode="single"))
        declared = {r.identifier for r in result.regions}
        for rule in result.placement_rules:
            assert rule.preferred_region in declared
        assert _rule(result, "skills").preferred_region == "main"

    def test_single_column_clears_column_ratios(self):
        result = RESOLVER.resolve(_layout("sidebar"), LayoutConfig(mode="single"))
        assert result.grid.column_ratios is None


class TestTwoColumn:
    def test_two_column_keeps_sidebar(self):
        result = RESOLVER.resolve(_layout("sidebar"), LayoutConfig(mode="two_column"))
        types = {r.region_type for r in result.regions}
        assert RegionType.MAIN in types
        assert RegionType.SIDEBAR in types

    def test_two_column_with_secondary_rail(self):
        result = RESOLVER.resolve(_layout("modern"), LayoutConfig(mode="two_column"))
        types = {r.region_type for r in result.regions}
        assert RegionType.MAIN in types
        assert RegionType.CUSTOM in types

    @pytest.mark.parametrize("layout_id", ["executive", "timeline", "minimal"])
    def test_two_column_incompatible_layout_rejected(self, layout_id):
        with pytest.raises(LayoutResolverError, match="no main"):
            RESOLVER.resolve(_layout(layout_id), LayoutConfig(mode="two_column"))


class TestSidebarSide:
    def test_sidebar_left(self):
        result = RESOLVER.resolve(_layout("sidebar"), LayoutConfig(mode="two_column", sidebar="left"))
        assert _region_order(result) == ["sidebar", "main"]

    def test_sidebar_right(self):
        result = RESOLVER.resolve(_layout("sidebar"), LayoutConfig(mode="two_column", sidebar="right"))
        assert _region_order(result) == ["main", "sidebar"]

    def test_sidebar_left_header_first(self):
        result = RESOLVER.resolve(_layout("modern"), LayoutConfig(mode="two_column", sidebar="left"))
        assert _region_order(result) == ["header", "secondary", "main"]

    def test_sidebar_right_header_first(self):
        result = RESOLVER.resolve(_layout("modern"), LayoutConfig(mode="two_column", sidebar="right"))
        assert _region_order(result) == ["header", "main", "secondary"]

    def test_header_position_single_column(self):
        result = RESOLVER.resolve(_layout("executive"), LayoutConfig())
        order = _region_order(result)
        assert order.index("header") < order.index("main")
        header = next(r for r in result.regions if r.identifier == "header")
        assert header.column_span == 12


class TestRatio:
    @pytest.mark.parametrize(
        "ratio,expected",
        [
            ("30/70", (30, 70)),
            ("32/68", (32, 68)),
            ("35/65", (35, 65)),
            ("40/60", (40, 60)),
        ],
    )
    def test_every_ratio_exact(self, ratio, expected):
        result = RESOLVER.resolve(_layout("sidebar"), LayoutConfig(mode="two_column", ratio=ratio))
        assert result.grid.column_ratios == expected

    def test_ratio_not_approximated(self):
        result = RESOLVER.resolve(_layout("sidebar"), LayoutConfig(mode="two_column", ratio="35/65"))
        assert result.grid.column_ratios == (35, 65)


class TestSectionPlacement:
    def test_placement_override_adds_rule(self):
        result = RESOLVER.resolve(
            _layout("timeline"),
            LayoutConfig(sections={"education": SectionLayoutConfig(region="main")}),
        )
        assert _rule(result, "education").preferred_region == "main"

    def test_placement_override_to_main(self):
        result = RESOLVER.resolve(
            _layout("classic"),
            LayoutConfig(
                mode="two_column",
                sections={"skills": SectionLayoutConfig(region="main")},
            ),
        )
        assert _rule(result, "skills").preferred_region == "main"

    def test_placement_override_to_sidebar(self):
        result = RESOLVER.resolve(
            _layout("sidebar"),
            LayoutConfig(
                mode="two_column",
                sections={"skills": SectionLayoutConfig(region="sidebar")},
            ),
        )
        assert _rule(result, "skills").preferred_region == "sidebar"

    def test_impossible_placement_rejected(self):
        with pytest.raises(LayoutResolverError, match="cannot be placed"):
            RESOLVER.resolve(
                _layout("sidebar"),
                LayoutConfig(
                    mode="two_column",
                    sections={"education": SectionLayoutConfig(region="sidebar")},
                ),
            )

    def test_region_not_in_layout_rejected(self):
        with pytest.raises(LayoutResolverError, match="no such region"):
            RESOLVER.resolve(
                _layout("executive"),
                LayoutConfig(
                    mode="single",
                    sections={"skills": SectionLayoutConfig(region="sidebar")},
                ),
            )


class TestSectionOrder:
    def test_order_override_wins_over_base(self):
        result = RESOLVER.resolve(
            _layout("sidebar"),
            LayoutConfig(mode="two_column", sections={"experience": SectionLayoutConfig(order=1)}),
        )
        assert _rule(result, "experience").ordering == 1

    def test_order_and_region_together(self):
        result = RESOLVER.resolve(
            _layout("classic"),
            LayoutConfig(
                mode="two_column",
                sections={"skills": SectionLayoutConfig(region="main", order=5)},
            ),
        )
        rule = _rule(result, "skills")
        assert rule.preferred_region == "main"
        assert rule.ordering == 5


class TestGapDensityVisibility:
    @pytest.mark.parametrize(
        "gap,expected_mm",
        [("none", 0.0), ("compact", 4.0), ("balanced", 8.0), ("wide", 16.0)],
    )
    def test_gap_mapping(self, gap, expected_mm):
        result = RESOLVER.resolve(_layout("sidebar"), LayoutConfig(mode="two_column", gap=gap))
        assert result.grid.gap_mm == expected_mm

    def test_density_does_not_change_resolution(self):
        a = RESOLVER.resolve(_layout("sidebar"), LayoutConfig(mode="two_column", density="compact"))
        b = RESOLVER.resolve(_layout("sidebar"), LayoutConfig(mode="two_column", density="spacious"))
        assert a == b

    def test_visibility_is_noop(self):
        result = RESOLVER.resolve(
            _layout("sidebar"),
            LayoutConfig(
                mode="two_column",
                sections={"skills": SectionLayoutConfig(visible=False)},
            ),
        )
        assert _rule(result, "skills").preferred_region == "sidebar"


class TestImmutabilityAndIndependence:
    def test_base_layout_unchanged(self):
        base = _layout("sidebar")
        original = base.model_dump()
        RESOLVER.resolve(
            base,
            LayoutConfig(mode="two_column", sidebar="right", ratio="40/60", gap="wide"),
        )
        assert base.model_dump() == original

    def test_multiple_configs_independent(self):
        base = _layout("sidebar")
        left = RESOLVER.resolve(base, LayoutConfig(mode="two_column", sidebar="left"))
        right = RESOLVER.resolve(base, LayoutConfig(mode="two_column", sidebar="right"))
        assert _region_order(left) == ["sidebar", "main"]
        assert _region_order(right) == ["main", "sidebar"]
        assert left is not right
        assert left != right
        assert base.model_dump() == _layout("sidebar").model_dump()

    @pytest.mark.parametrize("layout", REFERENCE_LAYOUTS)
    def test_resolved_default_remains_valid(self, layout):
        result = RESOLVER.resolve(layout, LayoutConfig())
        assert LayoutDefinition.model_validate(result.model_dump()) == result

    @pytest.mark.parametrize("layout_id", ["sidebar", "modern", "classic"])
    def test_resolved_two_column_remains_valid(self, layout_id):
        result = RESOLVER.resolve(_layout(layout_id), LayoutConfig(mode="two_column", sidebar="right"))
        assert LayoutDefinition.model_validate(result.model_dump()) == result


class TestGridExtension:
    def test_invalid_column_ratios_rejected(self):
        with pytest.raises(ValidationError):
            GridConfig(column_ratios=(0, 100))
        with pytest.raises(ValidationError):
            GridConfig(column_ratios=(35,))

    def test_default_grid_unaffected(self):
        assert GridConfig().column_ratios is None
