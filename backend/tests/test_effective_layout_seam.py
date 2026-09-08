"""Unit tests for the P3.9 shared effective-layout resolution seam.

These pin the exact precedence and fallback behavior so preview and export
cannot drift:

    request-explicit > auto_balance > persisted > base
"""

import logging
from unittest.mock import patch

from app.models.resume import (
    Award,
    Certification,
    Education,
    Experience,
    Language,
    Project,
    Resume,
    Skill,
)
from app.rendering.content import cvm_from_resume
from app.rendering.layout.effective import resolve_effective_layout
from app.rendering.layout.layout_config import LayoutConfig
from app.rendering.layout.layout_resolver import LayoutResolverError
from app.rendering.layout.reference_layouts import executive_layout, sidebar_layout


def _long_resume() -> Resume:
    experiences = [
        Experience(
            company=f"Company {i}",
            title=f"Engineer {i}",
            start_date="2020",
            end_date="2023",
            description=["Did work", "More work"],
        )
        for i in range(10)
    ]
    return Resume(
        user_id="test",
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


class TestEffectiveLayoutPrecedence:
    def test_explicit_config_wins_over_auto_balance(self):
        """Case 1: request config + auto_balance -> explicit wins, balancer skipped."""
        base = sidebar_layout()
        cvm = cvm_from_resume(_long_resume())
        explicit = LayoutConfig(mode="single", density="compact")
        layout, cfg = resolve_effective_layout(base, cvm, explicit_config=explicit, auto_balance=True)
        assert cfg is explicit
        assert layout.grid.column_ratios is None  # single column, not balanced
        assert cfg.mode.value == "single"

    def test_no_explicit_auto_balance_balances(self):
        """Case 2: no request config + auto_balance -> balanced two-column."""
        base = sidebar_layout()
        cvm = cvm_from_resume(_long_resume())
        layout, cfg = resolve_effective_layout(base, cvm, auto_balance=True)
        assert cfg is not None
        assert layout.grid.column_ratios is not None  # two-column recommendation applied
        assert cfg.density.value == "normal"  # balanced default density

    def test_no_explicit_no_auto_balance_returns_base(self):
        """Case 3/4: no request config + auto_balance off -> base, no config."""
        base = sidebar_layout()
        cvm = cvm_from_resume(_long_resume())
        layout, cfg = resolve_effective_layout(base, cvm, auto_balance=False)
        assert layout is base
        assert cfg is None

    def test_explicit_config_resolves_through_resolver(self):
        """Explicit config is resolved via LayoutResolver (two-column on sidebar)."""
        base = sidebar_layout()
        cvm = cvm_from_resume(_long_resume())
        explicit = LayoutConfig(mode="two_column", ratio="40/60", sidebar="right")
        layout, cfg = resolve_effective_layout(base, cvm, explicit_config=explicit)
        assert cfg is explicit
        assert layout.grid.column_ratios == (40, 60)


class TestEffectiveLayoutErrorHandling:
    def test_layout_resolver_error_falls_back_silently(self):
        """Expected resolver failure during balancing -> base layout, no config."""
        base = executive_layout()  # single-column-only base
        cvm = cvm_from_resume(_long_resume())
        with patch(
            "app.rendering.layout.effective.apply_layout_balancer_result",
            side_effect=LayoutResolverError("unresolvable"),
        ):
            layout, cfg = resolve_effective_layout(base, cvm, auto_balance=True)
        assert layout is base
        assert cfg is None

    def test_unexpected_exception_logs_and_falls_back(self, caplog):
        """Unexpected balancing failure -> structured warning + safe fallback."""
        base = sidebar_layout()
        cvm = cvm_from_resume(_long_resume())
        with patch(
            "app.rendering.layout.effective.apply_layout_balancer_result",
            side_effect=RuntimeError("boom"),
        ):
            with caplog.at_level(logging.WARNING):
                layout, cfg = resolve_effective_layout(base, cvm, auto_balance=True)
        assert layout is base
        assert cfg is None
        recs = [r for r in caplog.records if "Auto-balance failed unexpectedly" in r.message]
        assert recs, "unexpected failure must be logged"
        assert recs[0].levelno == logging.WARNING
        assert recs[0].extra_fields.get("layout_id") == base.layout_id
        assert recs[0].extra_fields.get("error") == "boom"
        assert recs[0].exc_info is not None

    def test_persisted_two_column_on_rail_less_base_falls_back(self):
        """A persisted two_column config on a rail-less template falls back to base.

        Regression: saving a balanced two-column layout on a rail-capable
        template, then switching to executive/timeline/minimal must not raise —
        the stale persisted config resolves to the base layout with no config.
        """
        base = executive_layout()  # no sidebar/secondary rail
        cvm = cvm_from_resume(_long_resume())
        persisted = LayoutConfig(mode="two_column", ratio="35/65", sidebar="left")
        layout, cfg = resolve_effective_layout(base, cvm, auto_balance=False, base_config=persisted)
        assert layout is base
        assert cfg is None

    def test_persisted_valid_config_still_applies(self):
        """A persisted config that resolves is applied normally (not fallen back)."""
        base = sidebar_layout()
        cvm = cvm_from_resume(_long_resume())
        persisted = LayoutConfig(mode="two_column", ratio="40/60", sidebar="right")
        layout, cfg = resolve_effective_layout(base, cvm, auto_balance=False, base_config=persisted)
        assert cfg is persisted
        assert layout.grid.column_ratios == (40, 60)


class TestEffectiveLayoutParity:
    def test_balanced_result_is_deterministic(self):
        """Identical inputs -> identical effective layout + density (preview == export)."""
        base = sidebar_layout()
        cvm = cvm_from_resume(_long_resume())
        l1, c1 = resolve_effective_layout(base, cvm, auto_balance=True)
        l2, c2 = resolve_effective_layout(base, cvm, auto_balance=True)
        assert l1.layout_id == l2.layout_id
        assert l1.grid.column_ratios == l2.grid.column_ratios
        assert c1.density == c2.density
