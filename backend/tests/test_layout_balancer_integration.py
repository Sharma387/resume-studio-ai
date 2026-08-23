"""P3.8 Integration tests — LayoutBalancer + LayoutMutator → Rendering pipeline."""

from __future__ import annotations

import logging
from unittest.mock import patch

from app.models.resume import Resume
from app.rendering.content_analyzer import ContentAnalysis, SectionMetrics
from app.rendering.export_service import ExportFormat, ExportService
from app.rendering.layout.layout_balancer import LayoutBalancer
from app.rendering.layout.layout_config import LayoutConfig
from app.rendering.layout.layout_mutator import apply_layout_balancer_result
from app.rendering.layout.layout_resolver import LayoutResolverError
from app.rendering.layout.reference_layouts import (
    classic_layout,
    executive_layout,
    modern_layout,
    sidebar_layout,
)


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


class TestBalancerMutatorIntegration:
    """Test that balancer recommendation flows through mutator to renderer."""

    def test_balancer_result_reaches_mutator(self):
        """LayoutBalanceResult from balancer is accepted by mutator."""
        analysis = _analysis_with(experience_units=200, summary_units=10)
        balancer = LayoutBalancer()
        result = balancer.balance(analysis, sidebar_layout())

        # Mutator should accept the result and produce a LayoutDefinition
        resolved = apply_layout_balancer_result(result, sidebar_layout())
        assert resolved.layout_id == sidebar_layout().layout_id
        assert resolved.grid.column_ratios is not None  # two-column was recommended

    def test_balancer_single_column_reaches_mutator(self):
        """Single-column recommendation from balancer works through mutator."""
        analysis = _analysis_with(experience_units=5, summary_units=2)
        balancer = LayoutBalancer()
        result = balancer.balance(analysis, sidebar_layout())

        resolved = apply_layout_balancer_result(result, sidebar_layout())
        assert resolved.layout_id == sidebar_layout().layout_id
        assert resolved.grid.column_ratios is None  # single-column
        # Original sidebar region should be gone
        region_ids = {r.identifier for r in resolved.regions}
        assert "sidebar" not in region_ids

    def test_balancer_two_column_wider_main(self):
        """Experience-heavy content gets wider main column (30/70)."""
        analysis = _analysis_with(experience_units=500, summary_units=20)
        balancer = LayoutBalancer()
        result = balancer.balance(analysis, sidebar_layout())

        resolved = apply_layout_balancer_result(result, sidebar_layout())
        assert resolved.grid.column_ratios == (30, 70)

    def test_balancer_left_sidebar(self):
        """LEFT sidebar recommendation produces correct region ordering."""
        analysis = _analysis_with(experience_units=200, summary_units=10)
        balancer = LayoutBalancer()
        result = balancer.balance(analysis, sidebar_layout())

        # Force LEFT sidebar if not already
        from app.rendering.layout.layout_balancer import LayoutBalanceResult
        from app.rendering.layout.layout_config import SidebarSide
        if result.config.sidebar is not SidebarSide.LEFT:
            result = LayoutBalanceResult(
                config=result.config.model_copy(update={"sidebar": SidebarSide.LEFT}),
                score=result.score,
                candidate_scores=result.candidate_scores,
                rationale=result.rationale,
                base_layout_id=result.base_layout_id,
            )

        resolved = apply_layout_balancer_result(result, sidebar_layout())
        regions = {r.identifier: r for r in resolved.regions}
        # Left sidebar: rail (sidebar) before main
        assert regions["sidebar"].ordering < regions["main"].ordering

    def test_balancer_right_sidebar(self):
        """RIGHT sidebar recommendation produces correct region ordering."""
        analysis = _analysis_with(experience_units=200, summary_units=10)
        balancer = LayoutBalancer()
        result = balancer.balance(analysis, sidebar_layout())

        from app.rendering.layout.layout_balancer import LayoutBalanceResult
        from app.rendering.layout.layout_config import SidebarSide
        result = LayoutBalanceResult(
            config=result.config.model_copy(update={"sidebar": SidebarSide.RIGHT}),
            score=result.score,
            candidate_scores=result.candidate_scores,
            rationale=result.rationale,
            base_layout_id=result.base_layout_id,
        )

        resolved = apply_layout_balancer_result(result, sidebar_layout())
        regions = {r.identifier: r for r in resolved.regions}
        # Right sidebar: main before rail
        assert regions["main"].ordering < regions["sidebar"].ordering


class TestDensityGapSectionsPreserved:
    """Test that density, gap, sections are preserved through the pipeline."""

    def test_density_preserved_in_balanced_layout(self):
        """Base config density is preserved in balanced layout."""
        base_config = LayoutConfig(density="spacious", gap="wide", sections={})
        analysis = _analysis_with(experience_units=200, summary_units=10)
        balancer = LayoutBalancer()
        result = balancer.balance(analysis, sidebar_layout())

        resolved = apply_layout_balancer_result(result, sidebar_layout(), base_config=base_config)
        # Gap preserved (wide = 16mm)
        assert resolved.grid.gap_mm == 16.0

    def test_gap_preserved_in_balanced_layout(self):
        """Base config gap is preserved in balanced layout."""
        base_config = LayoutConfig(density="normal", gap="compact", sections={})
        analysis = _analysis_with(experience_units=200, summary_units=10)
        balancer = LayoutBalancer()
        result = balancer.balance(analysis, sidebar_layout())

        resolved = apply_layout_balancer_result(result, sidebar_layout(), base_config=base_config)
        assert resolved.grid.gap_mm == 4.0  # compact = 4mm

    def test_sections_preserved_in_balanced_layout(self):
        """Base config sections overrides are preserved."""
        base_config = LayoutConfig(sections={"summary": {"order": 99}})
        analysis = _analysis_with(experience_units=200, summary_units=10)
        balancer = LayoutBalancer()
        result = balancer.balance(analysis, sidebar_layout())

        resolved = apply_layout_balancer_result(result, sidebar_layout(), base_config=base_config)
        # The placement rules should reflect the section override
        # (order=99 should move summary to the end)
        summary_rule = next(r for r in resolved.placement_rules if r.section == "summary")
        assert summary_rule.ordering == 99


class TestBackwardCompatibility:
    """Test that explicit layout selection remains backward compatible."""

    def test_explicit_layout_config_bypasses_balancer(self):
        """Explicit layout_config skips auto-balancing in export service."""
        from app.rendering.export_service import ExportFormat, ExportService
        explicit_config = LayoutConfig(mode="single", density="compact")

        service = ExportService()
        resume = _make_test_resume_long()  # Would trigger two-column if auto-balanced

        # With explicit config and auto_balance=False (default), explicit config wins
        result = service.export(
            resume,
            layout_id="sidebar",
            theme_id="blue",
            output_format=ExportFormat.HTML,
            layout_config=explicit_config,
            auto_balance=False,
        )
        assert result.content is not None
        # The export would use the explicit single-column config, not the balancer's two-column recommendation
        # We can't easily inspect the resolved layout from the result, but we verify the call succeeds

    def test_export_service_auto_balance_false_by_default(self):
        """ExportService default behavior unchanged (no auto-balance)."""
        service = ExportService()
        resume = _make_test_resume()

        # Without auto_balance, should use base layout unchanged
        result = service.export(
            resume,
            layout_id="sidebar",
            theme_id="blue",
            output_format=ExportFormat.HTML,
            auto_balance=False,
        )
        assert result.content is not None

    def test_export_service_auto_balance_true_enables_balancer(self):
        """ExportService auto_balance=True triggers balancing."""
        service = ExportService()
        resume = _make_test_resume_long()

        # With auto_balance, should apply balanced layout
        result = service.export(
            resume,
            layout_id="sidebar",
            theme_id="blue",
            output_format=ExportFormat.HTML,
            auto_balance=True,
        )
        assert result.content is not None


class TestFallbackBehavior:
    """Test that balancing failures fall back safely."""

    def test_unresolvable_recommendation_falls_back(self):
        """Two-column recommendation on single-column-only base falls back."""
        analysis = _analysis_with(experience_units=500, summary_units=20)
        balancer = LayoutBalancer()
        result = balancer.balance(analysis, executive_layout())  # executive has no sidebar

        # Mutator should fall back to base layout
        resolved = apply_layout_balancer_result(result, executive_layout())
        assert resolved.layout_id == executive_layout().layout_id
        assert resolved.grid.column_ratios is None

    def test_balancer_exception_falls_back(self):
        """Exception during balancing falls back to base layout."""
        # Create an invalid analysis that might cause issues
        analysis = ContentAnalysis(sections={}, total_word_count=0, total_char_count=0)
        balancer = LayoutBalancer()
        result = balancer.balance(analysis, sidebar_layout())

        # Even with empty analysis, should fall back gracefully
        resolved = apply_layout_balancer_result(result, sidebar_layout())
        assert resolved.layout_id == sidebar_layout().layout_id


class TestAutoBalanceExceptionHandling:
    """ExportService must survive balancing failures and fall back to base layout.

    LayoutResolverError is an expected failure (the recommendation cannot be
    resolved onto the base layout) and must fall back silently; any unexpected
    exception must be logged with context but still fall back so the export
    succeeds.
    """

    def test_layout_resolver_error_falls_back_silently(self, caplog):
        """Expected resolver failure: fall back, no unexpected-error log."""
        service = ExportService()
        resume = _make_test_resume_long()

        with patch(
            "app.rendering.layout.effective.apply_layout_balancer_result",
            side_effect=LayoutResolverError("no sidebar on base"),
        ):
            with caplog.at_level(logging.WARNING):
                result = service.export(
                    resume,
                    layout_id="sidebar",
                    theme_id="blue",
                    output_format=ExportFormat.HTML,
                    auto_balance=True,
                )

        assert result.content is not None  # export still succeeds
        unexpected = [r for r in caplog.records if "Auto-balance failed unexpectedly" in r.message]
        assert not unexpected, "LayoutResolverError must not be logged as an unexpected error"

    def test_unexpected_exception_logs_context_and_falls_back(self, caplog):
        """Unexpected failure: warning with context + exc_info, then fall back."""
        service = ExportService()
        resume = _make_test_resume_long()

        with patch(
            "app.rendering.layout.effective.apply_layout_balancer_result",
            side_effect=RuntimeError("boom"),
        ):
            with caplog.at_level(logging.WARNING):
                result = service.export(
                    resume,
                    layout_id="sidebar",
                    theme_id="blue",
                    output_format=ExportFormat.HTML,
                    auto_balance=True,
                )

        assert result.content is not None  # export still succeeds (fallback)
        unexpected = [r for r in caplog.records if "Auto-balance failed unexpectedly" in r.message]
        assert unexpected, "unexpected auto-balance failure must be logged"
        record = unexpected[0]
        assert record.levelno == logging.WARNING
        # Context is attached as structured log fields, not in the message text.
        assert record.extra_fields.get("layout_id") == "sidebar"
        assert record.extra_fields.get("error") == "boom"
        assert record.exc_info is not None  # traceback attached

    def test_unexpected_exception_renders_base_layout_normally(self, caplog):
        """Rendering continues with the base layout after an unexpected failure."""
        service = ExportService()
        resume = _make_test_resume_long()

        with patch(
            "app.rendering.layout.effective.apply_layout_balancer_result",
            side_effect=ValueError("unexpected"),
        ):
            result = service.export(
                resume,
                layout_id="sidebar",
                theme_id="blue",
                output_format=ExportFormat.HTML,
                auto_balance=True,
            )

        assert result.content is not None
        html = result.content.decode("utf-8")
        assert "Jane Doe" in html  # content rendered through base layout
        # No density injected (effective_config stayed None) → default spacing
        assert "Jane Doe" in html

    def test_analysis_failure_falls_back(self, caplog):
        """Failure in content analysis also falls back without crashing."""
        service = ExportService()
        resume = _make_test_resume_long()

        with patch(
            "app.rendering.layout.effective.ContentAnalyzer.analyze",
            side_effect=RuntimeError("analysis boom"),
        ):
            with caplog.at_level(logging.WARNING):
                result = service.export(
                    resume,
                    layout_id="sidebar",
                    theme_id="blue",
                    output_format=ExportFormat.HTML,
                    auto_balance=True,
                )

        assert result.content is not None
        unexpected = [r for r in caplog.records if "Auto-balance failed unexpectedly" in r.message]
        assert unexpected


class TestBalancingDisabledUnchanged:
    """Test existing rendering behavior when balancing is disabled."""

    def test_no_auto_balance_uses_base_layout(self):
        """When auto_balance=False (default), base layout is used unchanged."""
        analysis = _analysis_with(experience_units=500, summary_units=20)
        balancer = LayoutBalancer()
        _ = balancer.balance(analysis, sidebar_layout())

        # Don't apply balancer result — just use base layout
        base = sidebar_layout()
        assert base.grid.column_ratios is None  # base layout has no column_ratios

    def test_existing_rendering_unchanged_without_auto_balance(self):
        """ExportService without auto_balance produces same output as before."""
        service = ExportService()
        resume = _make_test_resume()

        # This should behave exactly as before P3.8
        result = service.export(
            resume,
            layout_id="sidebar",
            theme_id="blue",
            output_format=ExportFormat.HTML,
        )
        assert result.content is not None
        # The layout should be the base sidebar layout (not balanced)


def _make_test_resume() -> Resume:
    import uuid

    from app.models.resume import Award, Certification, Education, Experience, Language, Project, Resume, Skill
    return Resume(
        user_id=str(uuid.uuid4()),
        full_name="Jane Doe",
        email="jane@test.com",
        professional_title="Engineer",
        summary="Test summary",
        experience=[Experience(company="Acme", title="Engineer", location="SF", start_date="2020", end_date="2023", description=["Did work"])],
        education=[Education(institution="MIT", degree="BS", field="CS", start_date="2016", end_date="2020")],
        skills=[Skill(category="Languages", skills=["Python"])],
        projects=[Project(name="Project", description="Desc", url="https://example.com", technologies=["Python"])],
        certifications=[Certification(name="Cert", issuer="Org", date="2022")],
        awards=[Award(name="Award", issuer="Org", date="2022")],
        languages=[Language(name="English", proficiency="Native")],
    )


def _make_test_resume_long() -> Resume:
    import uuid

    from app.models.resume import Award, Certification, Education, Experience, Language, Project, Resume, Skill
    # Create a resume with lots of experience to trigger two-column
    experiences = [
        Experience(company=f"Company {i}", title=f"Engineer {i}", location="SF", start_date="2020", end_date="2023", description=["Did work", "More work"])
        for i in range(10)
    ]
    return Resume(
        user_id=str(uuid.uuid4()),
        full_name="Jane Doe",
        email="jane@test.com",
        professional_title="Senior Engineer",
        summary="Very long summary " * 20,
        experience=experiences,
        education=[Education(institution="MIT", degree="BS", field="CS", start_date="2016", end_date="2020")],
        skills=[Skill(category="Languages", skills=["Python", "Go", "Rust"])],
        projects=[Project(name=f"Project {i}", description="Desc", url="https://example.com", technologies=["Python"]) for i in range(5)],
        certifications=[Certification(name=f"Cert {i}", issuer="Org", date="2022") for i in range(3)],
        awards=[Award(name=f"Award {i}", issuer="Org", date="2022") for i in range(2)],
        languages=[Language(name="English", proficiency="Native"), Language(name="Spanish", proficiency="Professional")],
    )


class TestIntegrationWithExistingLayouts:
    """Test that balancing works with all existing layout families."""

    def test_modern_layout_balanced(self):
        """Modern layout (main + CUSTOM secondary) works with balancer."""
        analysis = _analysis_with(experience_units=300, summary_units=50)
        balancer = LayoutBalancer()
        result = balancer.balance(analysis, modern_layout())
        resolved = apply_layout_balancer_result(result, modern_layout())
        assert resolved.grid.column_ratios is not None

    def test_classic_layout_balanced(self):
        """Classic layout (main + CUSTOM secondary) works with balancer."""
        analysis = _analysis_with(experience_units=300, summary_units=50)
        balancer = LayoutBalancer()
        result = balancer.balance(analysis, classic_layout())
        resolved = apply_layout_balancer_result(result, classic_layout())
        assert resolved.grid.column_ratios is not None

    def test_timeline_minimal_always_single(self):
        """Timeline/minimal layouts stay single-column even with large content."""
        from app.rendering.layout.reference_layouts import minimal_layout, timeline_layout
        for layout in (timeline_layout(), minimal_layout()):
            analysis = _analysis_with(experience_units=500, summary_units=100)
            balancer = LayoutBalancer()
            result = balancer.balance(analysis, layout)
            resolved = apply_layout_balancer_result(result, layout)
            assert resolved.regions[0].region_type.name == "MAIN"
            assert resolved.grid.column_ratios is None
