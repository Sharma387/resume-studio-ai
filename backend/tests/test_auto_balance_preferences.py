"""P3.10 regression — persisted density/gap/sections survive auto-balance.

The balancer still decides mode/ratio/sidebar; the persisted LayoutConfig is
passed as ``base_config`` so the user's spacing/section preferences are seeded
into the balanced recommendation.
"""

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
from app.rendering.layout.layout_config import LayoutConfig, SectionLayoutConfig
from app.rendering.layout.reference_layouts import sidebar_layout


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
        projects=[
            Project(name=f"Project {i}", description="Desc", url="https://example.com", technologies=["Python"])
            for i in range(5)
        ],
        certifications=[Certification(name=f"Cert {i}", issuer="Org", date="2022") for i in range(3)],
        awards=[Award(name=f"Award {i}", issuer="Org", date="2022") for i in range(2)],
        languages=[
            Language(name="English", proficiency="Native"),
            Language(name="Spanish", proficiency="Professional"),
        ],
    )


class TestPersistedPrefsSurviveAutoBalance:
    def test_persisted_density_survives_auto_balance(self):
        base = sidebar_layout()
        cvm = cvm_from_resume(_long_resume())
        persisted = LayoutConfig(density="spacious", gap="balanced", sections={})
        _, cfg = resolve_effective_layout(base, cvm, auto_balance=True, base_config=persisted)
        assert cfg.density.value == "spacious"

    def test_persisted_gap_survives_auto_balance(self):
        base = sidebar_layout()
        cvm = cvm_from_resume(_long_resume())
        persisted = LayoutConfig(density="normal", gap="wide", sections={})
        _, cfg = resolve_effective_layout(base, cvm, auto_balance=True, base_config=persisted)
        assert cfg.gap.value == "wide"

    def test_persisted_sections_survive_auto_balance(self):
        base = sidebar_layout()
        cvm = cvm_from_resume(_long_resume())
        persisted = LayoutConfig(sections={"summary": SectionLayoutConfig(order=99)})
        _, cfg = resolve_effective_layout(base, cvm, auto_balance=True, base_config=persisted)
        assert "summary" in cfg.sections
        assert cfg.sections["summary"].order == 99

    def test_mode_ratio_sidebar_still_chosen_by_balancer(self):
        # User forced single-column; balancer overrides for long content.
        base = sidebar_layout()
        cvm = cvm_from_resume(_long_resume())
        persisted = LayoutConfig(density="spacious", mode="single")
        layout, cfg = resolve_effective_layout(base, cvm, auto_balance=True, base_config=persisted)
        assert cfg.mode.value == "two_column"
        assert layout.grid.column_ratios is not None
        # density still seeded from persisted
        assert cfg.density.value == "spacious"

    def test_explicit_config_still_wins_over_base_config(self):
        base = sidebar_layout()
        cvm = cvm_from_resume(_long_resume())
        explicit = LayoutConfig(mode="single", density="compact")
        persisted = LayoutConfig(density="spacious")
        layout, cfg = resolve_effective_layout(
            base, cvm, explicit_config=explicit, auto_balance=True, base_config=persisted
        )
        assert cfg is explicit
        assert cfg.density.value == "compact"
        assert layout.grid.column_ratios is None

    def test_no_persisted_config_retains_current_behavior(self):
        base = sidebar_layout()
        cvm = cvm_from_resume(_long_resume())
        # auto_balance with no base_config -> default (normal) density, no persisted influence
        _, cfg = resolve_effective_layout(base, cvm, auto_balance=True, base_config=None)
        assert cfg.density.value == "normal"
        # auto_balance off, no base_config -> base layout, no effective config
        layout2, cfg2 = resolve_effective_layout(base, cvm, auto_balance=False, base_config=None)
        assert layout2 is base
        assert cfg2 is None


class TestAutoBalanceFallbackHasNoRationale:
    """P3.11 — when auto-balance falls back, no rationale/balance result is exposed."""

    def test_balance_result_none_on_resolver_fallback(self, monkeypatch):
        from app.rendering.layout.layout_resolver import LayoutResolverError

        def _boom(*args, **kwargs):
            raise LayoutResolverError("forced")

        monkeypatch.setattr("app.rendering.layout.effective.apply_layout_balancer_result", _boom)

        base = sidebar_layout()
        cvm = cvm_from_resume(_long_resume())
        layout, cfg, balance_result = resolve_effective_layout(base, cvm, auto_balance=True, return_balance_result=True)
        assert balance_result is None
        assert layout is base
        assert cfg is None

    def test_balance_result_none_on_unexpected_error(self, monkeypatch):
        def _boom(*args, **kwargs):
            raise RuntimeError("forced")

        monkeypatch.setattr("app.rendering.layout.effective.apply_layout_balancer_result", _boom)

        base = sidebar_layout()
        cvm = cvm_from_resume(_long_resume())
        layout, cfg, balance_result = resolve_effective_layout(base, cvm, auto_balance=True, return_balance_result=True)
        assert balance_result is None
        assert layout is base
        assert cfg is None
