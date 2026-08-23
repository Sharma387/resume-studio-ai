"""Tests for the P3.6 LayoutBalancer (candidate scoring over safe presets)."""

import pytest
from pydantic import ValidationError

from app.rendering.content_analyzer import ContentAnalysis, ContentAnalyzer, SectionMetrics
from app.rendering.layout import (
    CandidateScore,
    ColumnRatio,
    Density,
    GapSize,
    LayoutBalancer,
    LayoutBalanceResult,
    LayoutConfig,
    LayoutMode,
    SectionLayoutConfig,
    SidebarSide,
)
from app.rendering.layout.layout_resolver import LayoutResolver
from app.rendering.layout.reference_layouts import (
    REFERENCE_LAYOUTS,
    classic_layout,
    executive_layout,
    minimal_layout,
    modern_layout,
    sidebar_layout,
    timeline_layout,
)
from tests.test_tree_html_renderer import _comprehensive_cvm, _long_cvm

SIDEBAR = sidebar_layout()
EXECUTIVE = executive_layout()
MODERN = modern_layout()
CLASSIC = classic_layout()
TIMELINE = timeline_layout()
MINIMAL = minimal_layout()

_ANALYZER = ContentAnalyzer()
_BALANCER = LayoutBalancer()
_RESOLVER = LayoutResolver()

_EXPECTED_COMPONENTS = frozenset(
    {"balance", "main_capacity", "sidebar_capacity", "fragmentation", "simplicity", "ratio"}
)


def _units(**kwargs) -> ContentAnalysis:
    sections = {}
    for section_id, (items, words) in kwargs.items():
        sections[section_id] = SectionMetrics(
            section_id=section_id,
            item_count=items,
            word_count=words,
            char_count=words * 6,
            estimated_units=words,
        )
    return ContentAnalysis(
        sections=sections,
        total_word_count=sum(metric.word_count for metric in sections.values()),
        total_char_count=0,
    )


_COMPREHENSIVE = _ANALYZER.analyze(_comprehensive_cvm())
_LONG = _ANALYZER.analyze(_long_cvm())


def _rail_heavy() -> ContentAnalysis:
    return _units(
        experience=(3, 50),
        projects=(2, 20),
        summary=(1, 10),
        education=(1, 5),
        skills=(300, 300),
        certifications=(100, 100),
        languages=(100, 100),
        awards=(100, 100),
        profile=(1, 5),
    )


def _tiny() -> ContentAnalysis:
    return _units(experience=(1, 2), summary=(1, 2))


class TestRecommendations:
    def test_small_resume_recommends_single_column(self):
        result = _BALANCER.balance(_COMPREHENSIVE, SIDEBAR)
        assert result.config.mode is LayoutMode.SINGLE

    def test_long_resume_recommends_two_column_wider_main(self):
        result = _BALANCER.balance(_LONG, SIDEBAR)
        assert result.config.mode is LayoutMode.TWO_COLUMN
        assert result.config.ratio is ColumnRatio.RATIO_30_70

    def test_experience_heavy_prefers_wider_main_over_narrow(self):
        result = _BALANCER.balance(_LONG, SIDEBAR)
        wide = next(
            c for c in result.candidate_scores if c.config.ratio is ColumnRatio.RATIO_30_70
        )
        narrow = next(
            c for c in result.candidate_scores if c.config.ratio is ColumnRatio.RATIO_40_60
        )
        assert wide.score > narrow.score

    def test_rail_heavy_prefers_wider_rail(self):
        result = _BALANCER.balance(_rail_heavy(), SIDEBAR)
        assert result.config.mode is LayoutMode.TWO_COLUMN
        assert result.config.ratio is ColumnRatio.RATIO_40_60

    def test_rail_heavy_avoid_narrow_rail(self):
        result = _BALANCER.balance(_rail_heavy(), SIDEBAR)
        wide_main = next(
            c for c in result.candidate_scores if c.config.ratio is ColumnRatio.RATIO_30_70
        )
        wide_rail = next(
            c for c in result.candidate_scores if c.config.ratio is ColumnRatio.RATIO_40_60
        )
        assert wide_rail.score > wide_main.score

    def test_empty_analysis_still_returns_valid_config(self):
        result = _BALANCER.balance(ContentAnalysis(sections={}), SIDEBAR)
        assert result.config.mode is LayoutMode.SINGLE
        assert result.score >= 0
        assert len(result.candidate_scores) >= 1

    def test_tiny_content_recommends_single_column(self):
        result = _BALANCER.balance(_tiny(), SIDEBAR)
        assert result.config.mode is LayoutMode.SINGLE

    def test_large_content_recommends_two_columns(self):
        result = _BALANCER.balance(_LONG, SIDEBAR)
        assert result.config.mode is LayoutMode.TWO_COLUMN

    def test_long_golden_two_column_across_modern_and_classic(self):
        for layout in (MODERN, CLASSIC):
            result = _BALANCER.balance(_LONG, layout)
            assert result.config.mode is LayoutMode.TWO_COLUMN
            assert result.config.ratio in (
                ColumnRatio.RATIO_30_70,
                ColumnRatio.RATIO_32_68,
            )

    def test_comprehensive_golden_single_across_capable_layouts(self):
        for layout in (SIDEBAR, MODERN, CLASSIC):
            assert _BALANCER.balance(_COMPREHENSIVE, layout).config.mode is LayoutMode.SINGLE

    def test_single_only_base_yields_only_single_candidate(self):
        for layout in (EXECUTIVE, TIMELINE, MINIMAL):
            result = _BALANCER.balance(_LONG, layout)
            assert len(result.candidate_scores) == 1
            assert result.candidate_scores[0].config.mode is LayoutMode.SINGLE

    def test_single_only_base_still_returns_large_single_column(self):
        for layout in (EXECUTIVE, TIMELINE, MINIMAL):
            assert _BALANCER.balance(_LONG, layout).config.mode is LayoutMode.SINGLE

    def test_single_only_base_rationale_mentions_constraint(self):
        result = _BALANCER.balance(_LONG, EXECUTIVE)
        assert "single" in result.rationale
        assert result.rationale != "Small resume; single-column is simpler and sufficient for the estimated content."

    def test_experience_heavy_rationale_mentions_wide_main(self):
        result = _BALANCER.balance(_LONG, SIDEBAR)
        assert "wider main" in result.rationale

    def test_result_reports_base_layout_id(self):
        assert _BALANCER.balance(_LONG, SIDEBAR).base_layout_id == SIDEBAR.layout_id


class TestCandidateSet:
    def test_two_column_capable_base_exposes_full_candidate_set(self):
        result = _BALANCER.balance(_LONG, SIDEBAR)
        assert len(result.candidate_scores) == 9

    def test_all_ratios_and_sides_present(self):
        result = _BALANCER.balance(_LONG, SIDEBAR)
        seen = {
            (c.config.ratio, c.config.sidebar)
            for c in result.candidate_scores
            if c.config.mode is LayoutMode.TWO_COLUMN
        }
        expected = {
            (ratio, side)
            for ratio in (
                ColumnRatio.RATIO_30_70,
                ColumnRatio.RATIO_32_68,
                ColumnRatio.RATIO_35_65,
                ColumnRatio.RATIO_40_60,
            )
            for side in (SidebarSide.LEFT, SidebarSide.RIGHT)
        }
        assert seen == expected

    def test_side_pairs_score_equally(self):
        result = _BALANCER.balance(_LONG, SIDEBAR)
        for ratio in (
            ColumnRatio.RATIO_30_70,
            ColumnRatio.RATIO_32_68,
            ColumnRatio.RATIO_35_65,
            ColumnRatio.RATIO_40_60,
        ):
            left = next(
                c
                for c in result.candidate_scores
                if c.config.mode is LayoutMode.TWO_COLUMN
                and c.config.ratio is ratio
                and c.config.sidebar is SidebarSide.LEFT
            )
            right = next(
                c
                for c in result.candidate_scores
                if c.config.mode is LayoutMode.TWO_COLUMN
                and c.config.ratio is ratio
                and c.config.sidebar is SidebarSide.RIGHT
            )
            assert left.score == right.score

    def test_winner_prefers_left_side_on_tie(self):
        result = _BALANCER.balance(_LONG, SIDEBAR)
        assert result.config.sidebar is SidebarSide.LEFT

    def test_unresolvable_candidates_skipped_for_single_only_base(self):
        for layout in (EXECUTIVE, TIMELINE, MINIMAL):
            result = _BALANCER.balance(_LONG, layout)
            assert all(c.config.mode is LayoutMode.SINGLE for c in result.candidate_scores)

    def test_candidate_components_keys_exact(self):
        result = _BALANCER.balance(_LONG, SIDEBAR)
        for candidate in result.candidate_scores:
            assert set(candidate.components) == _EXPECTED_COMPONENTS

    def test_scores_equal_component_sum(self):
        result = _BALANCER.balance(_LONG, SIDEBAR)
        for candidate in result.candidate_scores:
            assert abs(candidate.score - sum(candidate.components.values())) < 1e-6
            assert candidate.score >= 0

    def test_single_candidate_has_constant_components(self):
        result = _BALANCER.balance(_LONG, SIDEBAR)
        single = next(
            c for c in result.candidate_scores if c.config.mode is LayoutMode.SINGLE
        )
        assert single.components["balance"] == 100.0
        assert single.components["main_capacity"] == 100.0
        assert single.components["sidebar_capacity"] == 100.0
        assert single.components["fragmentation"] == 0.0
        assert single.components["ratio"] == 0.0

    def test_winner_is_highest_scoring_candidate(self):
        result = _BALANCER.balance(_LONG, SIDEBAR)
        assert result.score == max(c.score for c in result.candidate_scores)
        assert result.config == next(
            c.config for c in result.candidate_scores if c.score == result.score
        )


class TestContractAndPurity:
    def test_deterministic_same_input_same_output(self):
        first = _BALANCER.balance(_LONG, SIDEBAR)
        second = _BALANCER.balance(_LONG, SIDEBAR)
        assert first.config == second.config
        assert first.score == second.score
        assert first.rationale == second.rationale
        assert first.candidate_scores == second.candidate_scores

    def test_base_layout_not_mutated(self):
        before = SIDEBAR.model_dump()
        _BALANCER.balance(_LONG, SIDEBAR)
        assert SIDEBAR.model_dump() == before

    def test_base_config_not_mutated(self):
        base_config = LayoutConfig(density=Density.SPACIOUS, gap=GapSize.WIDE)
        before = base_config.model_dump()
        _BALANCER.balance(_LONG, SIDEBAR, base_config)
        assert base_config.model_dump() == before

    def test_candidate_configs_seed_from_base_config(self):
        base_config = LayoutConfig(
            density=Density.SPACIOUS,
            gap=GapSize.WIDE,
            sections={"summary": SectionLayoutConfig(order=5)},
        )
        result = _BALANCER.balance(_COMPREHENSIVE, SIDEBAR, base_config)
        assert result.config.density is Density.SPACIOUS
        assert result.config.gap is GapSize.WIDE
        assert result.config.sections == {"summary": SectionLayoutConfig(order=5)}
        for candidate in result.candidate_scores:
            assert candidate.config.density is Density.SPACIOUS
            assert candidate.config.gap is GapSize.WIDE

    def test_default_base_config_uses_defaults(self):
        result = _BALANCER.balance(_COMPREHENSIVE, SIDEBAR)
        assert result.config.density is LayoutConfig().density
        assert result.config.gap is LayoutConfig().gap

    def test_result_models_are_frozen(self):
        result = _BALANCER.balance(_LONG, SIDEBAR)
        with pytest.raises(ValidationError):
            result.score = 1.0
        with pytest.raises(ValidationError):
            result.candidate_scores[0].score = 1.0
        with pytest.raises(ValidationError):
            result.config.mode = LayoutMode.SINGLE

    def test_result_exposes_candidate_scores_and_rationale(self):
        result = _BALANCER.balance(_LONG, SIDEBAR)
        assert isinstance(result, LayoutBalanceResult)
        assert isinstance(result.candidate_scores, tuple)
        assert all(isinstance(c, CandidateScore) for c in result.candidate_scores)
        assert result.candidate_scores
        assert result.rationale.strip()

    def test_winner_config_round_trips_through_resolver(self):
        result = _BALANCER.balance(_LONG, SIDEBAR)
        resolved = _RESOLVER.resolve(SIDEBAR, result.config)
        assert resolved.capabilities.multi_column
        assert resolved.layout_id == SIDEBAR.layout_id

    def test_single_winner_resolves_to_single_main(self):
        result = _BALANCER.balance(_COMPREHENSIVE, SIDEBAR)
        resolved = _RESOLVER.resolve(SIDEBAR, result.config)
        assert resolved.grid.column_ratios is None

    def test_balancer_never_returns_section_unknown(self):
        result = _BALANCER.balance(_LONG, SIDEBAR)
        assert result.config.sections == {}

    def test_every_reference_layout_can_be_balanced(self):
        for layout in REFERENCE_LAYOUTS:
            result = _BALANCER.balance(_COMPREHENSIVE, layout)
            assert result.base_layout_id == layout.layout_id
            assert result.candidate_scores


class TestSimplicityThresholds:
    def test_simplicity_small_single_beats_two_column(self):
        result = _BALANCER.balance(_tiny(), SIDEBAR)
        single = next(
            c for c in result.candidate_scores if c.config.mode is LayoutMode.SINGLE
        )
        assert single.score > max(
            c.score for c in result.candidate_scores if c.config.mode is LayoutMode.TWO_COLUMN
        )

    def test_simplicity_large_two_column_beats_single(self):
        result = _BALANCER.balance(_LONG, SIDEBAR)
        two_column = next(
            c
            for c in result.candidate_scores
            if c.config.mode is LayoutMode.TWO_COLUMN and c.config.ratio is result.config.ratio
        )
        single = next(
            c for c in result.candidate_scores if c.config.mode is LayoutMode.SINGLE
        )
        assert two_column.score > single.score
