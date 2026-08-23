"""Tests for the P3.7 Layout mutator — applying a LayoutBalancer recommendation."""


from app.rendering.content_analyzer import ContentAnalysis, ContentAnalyzer, SectionMetrics
from app.rendering.layout.layout_balancer import LayoutBalancer, LayoutBalanceResult
from app.rendering.layout.layout_config import (
    LayoutConfig,
    SectionLayoutConfig,
    SidebarSide,
)
from app.rendering.layout.layout_mutator import apply_layout_balancer_result
from app.rendering.layout.reference_layouts import (
    classic_layout,
    executive_layout,
    minimal_layout,
    modern_layout,
    sidebar_layout,
    timeline_layout,
)
from tests.test_tree_html_renderer import _comprehensive_cvm


def _analysis_with(*, experience_units: int = 0, summary_units: int = 0) -> ContentAnalysis:
    sections = {}
    if experience_units:
        sections["experience"] = SectionMetrics(
            section_id="experience", item_count=1, word_count=experience_units, char_count=experience_units * 6, estimated_units=experience_units
        )
    if summary_units:
        sections["summary"] = SectionMetrics(
            section_id="summary", item_count=1, word_count=summary_units, char_count=summary_units * 6, estimated_units=summary_units
        )
    total_words = sum(m.word_count for m in sections.values())
    return ContentAnalysis(sections=sections, total_word_count=total_words, total_char_count=0)


def _override_result(result: LayoutBalanceResult, **kwargs) -> LayoutBalanceResult:
    """Create a new LayoutBalanceResult with overridden config fields."""
    new_config = result.config.model_copy(update=kwargs)
    return LayoutBalanceResult(
        config=new_config,
        score=result.score,
        candidate_scores=result.candidate_scores,
        rationale=result.rationale,
        base_layout_id=result.base_layout_id,
    )


class TestApplyLayoutBalancerResult:
    def test_single_column_on_sidebar_base(self):
        analysis = _analysis_with(experience_units=5, summary_units=2)
        balancer = LayoutBalancer()
        br = balancer.balance(analysis, sidebar_layout())
        new_layout = apply_layout_balancer_result(br, sidebar_layout())
        assert new_layout.regions[0].region_type.name == "MAIN"
        # Original unchanged
        assert sidebar_layout().regions[1].region_type.name == "SIDEBAR"

    def test_two_column_wider_main_on_sidebar(self):
        analysis = _analysis_with(experience_units=200, summary_units=10)
        balancer = LayoutBalancer()
        br = balancer.balance(analysis, sidebar_layout())
        new_layout = apply_layout_balancer_result(br, sidebar_layout())
        assert new_layout.grid.column_ratios == (30, 70)  # wider main

    def test_left_sidebar_applied(self):
        analysis = _analysis_with(experience_units=200, summary_units=10)
        balancer = LayoutBalancer()
        br = balancer.balance(analysis, sidebar_layout())
        # Force LEFT sidebar if not already
        if br.config.sidebar is not SidebarSide.LEFT:
            br = _override_result(br, sidebar=SidebarSide.LEFT)
        new_layout = apply_layout_balancer_result(br, sidebar_layout())
        # Check that ordering reflects left sidebar (rail before main)
        regions = {r.identifier: r for r in new_layout.regions}
        # In left sidebar: rail=1, main=2
        assert regions["sidebar"].ordering < regions["main"].ordering

    def test_right_sidebar_applied(self):
        analysis = _analysis_with(experience_units=200, summary_units=10)
        balancer = LayoutBalancer()
        br = balancer.balance(analysis, sidebar_layout())
        # Force RIGHT sidebar
        br = _override_result(br, sidebar=SidebarSide.RIGHT)
        new_layout = apply_layout_balancer_result(br, sidebar_layout())
        regions = {r.identifier: r for r in new_layout.regions}
        # In right sidebar: main=1, rail=2
        assert regions["main"].ordering < regions["sidebar"].ordering

    def test_density_gap_sections_preserved(self):
        base_config = LayoutConfig(density="spacious", gap="wide", sections={"summary": SectionLayoutConfig(order=5)})
        analysis = _analysis_with(experience_units=50, summary_units=10)
        balancer = LayoutBalancer()
        br = balancer.balance(analysis, sidebar_layout())
        new_layout = apply_layout_balancer_result(br, sidebar_layout(), base_config=base_config)
        # Verify preservation via gap mapping
        assert new_layout.grid.gap_mm == 16.0  # GapSize.WIDE maps to 16.0

    def test_original_objects_unchanged(self):
        base_config = LayoutConfig(density="normal", gap="balanced", sections={})
        analysis = _analysis_with(experience_units=50, summary_units=10)
        balancer = LayoutBalancer()
        br = balancer.balance(analysis, sidebar_layout())
        old_layout = sidebar_layout()
        old_config = base_config
        apply_layout_balancer_result(br, sidebar_layout(), base_config=base_config)
        # Original layout unchanged
        assert old_layout.layout_id == sidebar_layout().layout_id
        # Original config unchanged (frozen pydantic)
        assert old_config.density.value == "normal"
        assert old_config.gap.value == "balanced"

    def test_unresolvable_falls_back_to_base(self):
        # Executive layout has no sidebar/rail → two-column recommendation cannot resolve
        analysis = _analysis_with(experience_units=200, summary_units=10)
        balancer = LayoutBalancer()
        br = balancer.balance(analysis, executive_layout())
        new_layout = apply_layout_balancer_result(br, executive_layout())
        # Should return the base executive layout unchanged
        assert new_layout.layout_id == executive_layout().layout_id

    def test_resolver_validates_after_mutation(self):
        base_config = LayoutConfig(density="spacious", gap="wide", sections={})
        analysis = _analysis_with(experience_units=200, summary_units=10)
        balancer = LayoutBalancer()
        br = balancer.balance(analysis, sidebar_layout())
        new_layout = apply_layout_balancer_result(br, sidebar_layout(), base_config=base_config)
        # The returned layout should be a valid LayoutDefinition (resolver already ran)
        assert new_layout.layout_id is not None
        # Verify column_ratios were set
        assert new_layout.grid.column_ratios is not None

    def test_deterministic_same_input_same_output(self):
        analysis = _analysis_with(experience_units=200, summary_units=10)
        balancer = LayoutBalancer()
        br1 = balancer.balance(analysis, sidebar_layout())
        br2 = balancer.balance(analysis, sidebar_layout())
        assert br1.config == br2.config
        new1 = apply_layout_balancer_result(br1, sidebar_layout())
        new2 = apply_layout_balancer_result(br2, sidebar_layout())
        assert new1.layout_id == new2.layout_id

    def test_comprehensive_single_column(self):
        analyzer = ContentAnalyzer()
        ca = analyzer.analyze(_comprehensive_cvm())
        balancer = LayoutBalancer()
        br = balancer.balance(ca, sidebar_layout())
        new_layout = apply_layout_balancer_result(br, sidebar_layout())
        assert new_layout.regions[0].region_type.name == "MAIN"

    def test_result_preserves_base_layout_when_single_recommended(self):
        # Small content on a base that can do two-column but balancer picks single
        analysis = ContentAnalysis(sections={}, total_word_count=0, total_char_count=0)
        balancer = LayoutBalancer()
        br = balancer.balance(analysis, sidebar_layout())
        new_layout = apply_layout_balancer_result(br, sidebar_layout())
        # Falls back to original
        assert new_layout.layout_id == sidebar_layout().layout_id


class TestFallbackBehavior:
    def test_two_column_on_executive_falls_back(self):
        analysis = _analysis_with(experience_units=500, summary_units=20)
        balancer = LayoutBalancer()
        br = balancer.balance(analysis, executive_layout())
        new_layout = apply_layout_balancer_result(br, executive_layout())
        assert new_layout.layout_id == executive_layout().layout_id

    def test_small_content_single_then_fallback_preserves_config(self):
        analysis = _analysis_with(summary_units=5)
        balancer = LayoutBalancer()
        br = balancer.balance(analysis, sidebar_layout())
        new_layout = apply_layout_balancer_result(br, sidebar_layout())
        assert new_layout.regions[0].region_type.name == "MAIN"

    def test_medium_content_two_column_selected_preserves_density_gap(self):
        analysis = _analysis_with(experience_units=200, summary_units=30)
        balancer = LayoutBalancer()
        br = balancer.balance(analysis, sidebar_layout())
        new_layout = apply_layout_balancer_result(br, sidebar_layout())
        # Should have two-column with wider main
        assert new_layout.grid.column_ratios == (30, 70)
        # Default gap preserved
        assert new_layout.grid.gap_mm == 8.0


class TestIntegrationWithExistingLayouts:
    def test_modern_layout_two_column(self):
        analysis = _analysis_with(experience_units=300, summary_units=50)
        balancer = LayoutBalancer()
        br = balancer.balance(analysis, modern_layout())
        new_layout = apply_layout_balancer_result(br, modern_layout())
        # modern has main + CUSTOM secondary; should resolve two-column
        assert new_layout.grid.column_ratios is not None

    def test_classic_layout_two_column(self):
        analysis = _analysis_with(experience_units=300, summary_units=50)
        balancer = LayoutBalancer()
        br = balancer.balance(analysis, classic_layout())
        new_layout = apply_layout_balancer_result(br, classic_layout())
        # classic has main + CUSTOM secondary
        assert new_layout.grid.column_ratios is not None

    def test_timeline_minimal_always_single(self):
        for layout in (timeline_layout(), minimal_layout()):
            analysis = _analysis_with(experience_units=500, summary_units=100)
            balancer = LayoutBalancer()
            br = balancer.balance(analysis, layout)
            new_layout = apply_layout_balancer_result(br, layout)
            # Timeline/minimal should stay single-column even with large content
            assert new_layout.regions[0].region_type.name == "MAIN"
