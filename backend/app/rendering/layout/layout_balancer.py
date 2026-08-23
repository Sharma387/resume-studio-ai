"""LayoutBalancer — recommend a LayoutConfig for a ContentView's content size.

P3.6 is CANDIDATE SCORING ONLY. It evaluates a small, safe set of presets for
a given base layout and picks the best-scoring, valid ``LayoutConfig``; it
never mutates a LayoutDefinition, never renders, and never measures pages.

Pipeline position::

    ContentView → ContentAnalyzer → ContentAnalysis → LayoutBalancer
        → recommended LayoutConfig → LayoutResolver → LayoutDefinition

The balancer returns a ``LayoutConfig`` (plus immutable scoring diagnostics)
so :class:`LayoutResolver` remains the single place that converts config into
a concrete LayoutDefinition — the balancer never constructs layouts itself.

Scope
-----
* Two-column candidates: the four safe ratios (30/70, 32/68, 35/65, 40/60)
  crossed with both sides (left/right), plus single-column. No arbitrary
  ratios are ever generated.
* A candidate is scored only if it can actually be resolved against the base
  layout; every candidate passes through ``LayoutResolver.resolve``, so layouts
  without a main+rail pair simply never receive two-column candidates.
* ``density``/``gap``/per-section overrides of a supplied ``base_config`` are
  preserved on every candidate (additive: the balancer only recommends
  ``mode``/``ratio``/``sidebar``).

Scoring (higher = better; pure, deterministic, documented)
----------------------------------------------------------
Per two-column candidate:

    score = balance + main_capacity + sidebar_capacity + ratio + simplicity

* ``balance`` — content vs width: penalise how far the realised rail content
  share strays from the candidate's rail width fraction.
* ``main_capacity`` — experience/projects need main-column width: reward when
  the candidate's main width fraction covers the main content share.
* ``sidebar_capacity`` — penalise overloading a narrow rail (rail content
  share exceeding the rail width share by more than a small tolerance).
* ``ratio`` — experience-heavy content prefers a wider main column; the ideal
  main fraction derives from the experience+projects share of content.
* ``simplicity`` — small resumes should not be forced into two columns; large
  resumes should not be squeezed into one.
* ``fragmentation`` — constant 0: this balancer reorders nothing, so it never
  splits related sections.

The score is a relative heuristic, NOT a page/line/pixel prediction.

Content weighting
-----------------
``estimated_units`` (P3.5) is the base measure; section-level weights reflect
semantic density (deterministic; documented in ``_SECTION_WEIGHTS``). Grouped
skills/certifications already count as single logical items (P3.5), so no
per-skill counting is redone here. Placement is read from the base layout's
own PlacementRules — the balancer respects existing semantics and never
invents placement that contradicts them.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.rendering.content_analyzer import ContentAnalysis
from app.rendering.layout.layout_config import (
    ColumnRatio,
    LayoutConfig,
    LayoutMode,
    SidebarSide,
)
from app.rendering.layout.layout_definition import LayoutDefinition
from app.rendering.layout.layout_regions import RegionType
from app.rendering.layout.layout_resolver import LayoutResolver, LayoutResolverError

#: Weighted-unit thresholds for the simplicity component (documented constants).
#: ``estimated_units`` are words; ``_SECTION_WEIGHTS`` makes dense sections
#: heavier. At/below ``_SMALL_CONTENT_UNITS`` single column is preferred; at or
#: above ``_LARGE_CONTENT_UNITS`` two columns are strongly preferred.
_SMALL_CONTENT_UNITS: float = 120.0
_LARGE_CONTENT_UNITS: float = 500.0

#: Semantic weights per section, applied to ``estimated_units`` (words).
#: Deterministic and easy to tune later. Main-narrative sections are heavy;
#: supporting sections are lighter; profile/summary are identity/header text.
_SECTION_WEIGHTS: dict[str, float] = {
    "experience": 2.5,
    "projects": 2.0,
    "summary": 1.0,
    "education": 1.2,
    "skills": 1.5,
    "certifications": 1.0,
    "awards": 0.8,
    "languages": 0.6,
    "profile": 0.5,
}

#: Sections whose content drives the "wider main column" preference.
_MAIN_HEAVY_SECTIONS: frozenset[str] = frozenset({"experience", "projects"})

#: Safe candidates: single-column, then every ratio × both sides.
_SCORED_RATIOS: tuple[ColumnRatio, ...] = (
    ColumnRatio.RATIO_30_70,
    ColumnRatio.RATIO_32_68,
    ColumnRatio.RATIO_35_65,
    ColumnRatio.RATIO_40_60,
)

#: ColumnRatio → (rail fraction, main fraction) of the grid width.
_RATIO_FRACTIONS: dict[ColumnRatio, tuple[float, float]] = {
    ColumnRatio.RATIO_30_70: (0.30, 0.70),
    ColumnRatio.RATIO_32_68: (0.32, 0.68),
    ColumnRatio.RATIO_35_65: (0.35, 0.65),
    ColumnRatio.RATIO_40_60: (0.40, 0.60),
}

#: Region types that count as the main column / the rail for content split.
_MAIN_TYPES = (RegionType.MAIN,)
_RAIL_TYPES = (RegionType.SIDEBAR, RegionType.CUSTOM)

#: Rail content may exceed its width share by this tolerance before the
#: sidebar-capacity penalty applies (documented constant).
_RAIL_OVERLOAD_TOLERANCE: float = 0.05


class CandidateScore(BaseModel):
    """Scored layout candidate (config + deterministic scoring diagnostics)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    config: LayoutConfig
    score: float = Field(ge=0)
    components: dict[str, float]


class LayoutBalanceResult(BaseModel):
    """Immutable recommendation: a LayoutConfig plus explainable diagnostics."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    config: LayoutConfig
    score: float = Field(ge=0)
    candidate_scores: tuple[CandidateScore, ...]
    rationale: str
    base_layout_id: str


class _SectionTotals(BaseModel):
    """Weighted content split derived from the base layout's placement."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    main_units: float = 0.0
    rail_units: float = 0.0
    main_heavy_units: float = 0.0
    total_units: float = 0.0


class LayoutBalancer:
    """Deterministic candidate selection over safe layout presets."""

    def __init__(self, *, resolver: LayoutResolver | None = None) -> None:
        self._resolver = resolver or LayoutResolver()

    def balance(
        self,
        analysis: ContentAnalysis,
        base_layout: LayoutDefinition,
        base_config: LayoutConfig | None = None,
    ) -> LayoutBalanceResult:
        """Recommend a :class:`LayoutConfig` for ``analysis`` against ``base_layout``.

        ``base_config`` (when supplied) seeds ``density``/``gap``/``sections``
        onto every candidate so prior per-resume preferences are preserved.
        """
        seed = LayoutConfig(
            density=base_config.density if base_config else LayoutConfig().density,
            gap=base_config.gap if base_config else LayoutConfig().gap,
            sections=base_config.sections if base_config else {},
        )
        totals = self._section_totals(analysis, base_layout)

        candidates: list[CandidateScore] = []
        single_score = _simplicity(LayoutMode.SINGLE, totals.total_units)
        single = self._candidate(
            base_layout,
            seed.model_copy(update={"mode": LayoutMode.SINGLE}),
            totals,
            simplicity=single_score,
            ratio=None,
        )
        if single is not None:
            candidates.append(single)
        for ratio in _SCORED_RATIOS:
            for side in (SidebarSide.LEFT, SidebarSide.RIGHT):
                config = seed.model_copy(
                    update={"mode": LayoutMode.TWO_COLUMN, "ratio": ratio, "sidebar": side}
                )
                scored = self._candidate(
                    base_layout,
                    config,
                    totals,
                    simplicity=_simplicity(LayoutMode.TWO_COLUMN, totals.total_units),
                    ratio=ratio,
                )
                if scored is not None:
                    candidates.append(scored)

        best = max(enumerate(candidates), key=lambda item: (item[1].score, -item[0]))[1]
        return LayoutBalanceResult(
            config=best.config,
            score=best.score,
            candidate_scores=tuple(candidates),
            rationale=_rationale(best.config, totals),
            base_layout_id=base_layout.layout_id,
        )

    # ── Measurement ───────────────────────────────────────────────────────────

    def _section_totals(
        self, analysis: ContentAnalysis, base_layout: LayoutDefinition
    ) -> _SectionTotals:
        """Weight each present section once, split along the base placement."""
        region_index = {region.identifier: region for region in base_layout.regions}
        rule_index = {rule.section: rule for rule in base_layout.placement_rules}
        main_units = 0.0
        rail_units = 0.0
        main_heavy_units = 0.0
        total_units = 0.0
        for section, metrics in analysis.sections.items():
            weight = _SECTION_WEIGHTS.get(section)
            if weight is None:
                continue
            units = weight * metrics.estimated_units
            total_units += units
            if section in _MAIN_HEAVY_SECTIONS:
                main_heavy_units += units
            rule = rule_index.get(section)
            region = (
                region_index.get(rule.preferred_region)
                if rule is not None and rule.preferred_region
                else None
            )
            region_type = region.region_type if region is not None else None
            if region_type in _MAIN_TYPES:
                main_units += units
            elif region_type in _RAIL_TYPES:
                rail_units += units
        return _SectionTotals(
            main_units=main_units,
            rail_units=rail_units,
            main_heavy_units=main_heavy_units,
            total_units=total_units,
        )

    # ── Candidate scoring ─────────────────────────────────────────────────────

    def _candidate(
        self,
        base_layout: LayoutDefinition,
        config: LayoutConfig,
        totals: _SectionTotals,
        *,
        simplicity: float,
        ratio: ColumnRatio | None,
    ) -> CandidateScore | None:
        """Score (and validate) one candidate; ``None`` when it cannot resolve."""
        try:
            self._resolver.resolve(base_layout, config)
        except LayoutResolverError:
            return None
        if config.mode is LayoutMode.SINGLE:
            components: dict[str, float] = {
                "balance": 100.0,
                "main_capacity": 100.0,
                "sidebar_capacity": 100.0,
                "fragmentation": 0.0,
                "simplicity": simplicity,
                "ratio": 0.0,
            }
        else:
            components = self._two_column_components(totals, ratio, simplicity)
        score = round(sum(components.values()), 6)
        return CandidateScore(config=config, score=score, components=components)

    @staticmethod
    def _two_column_components(
        totals: _SectionTotals, ratio: ColumnRatio, simplicity: float
    ) -> dict[str, float]:
        rail_frac, main_frac = _RATIO_FRACTIONS[ratio]
        column_units = totals.main_units + totals.rail_units
        if column_units > 0 and totals.total_units > 0:
            main_share = totals.main_units / column_units
            rail_share = totals.rail_units / column_units
            main_heavy_share = totals.main_heavy_units / totals.total_units
        else:
            main_share = rail_share = 0.5
            main_heavy_share = 0.0
        over_rail = max(0.0, rail_share - (rail_frac + _RAIL_OVERLOAD_TOLERANCE))
        return {
            "balance": max(0.0, 100.0 - 150.0 * abs(rail_share - rail_frac)),
            "main_capacity": 50.0 + 50.0 * min(1.0, main_frac / max(main_share, 1e-9)),
            "sidebar_capacity": max(0.0, 100.0 - 200.0 * over_rail),
            "fragmentation": 0.0,
            "simplicity": simplicity,
            "ratio": max(0.0, 100.0 - 4.0 * abs(main_frac * 100.0 - _ideal_main_pct(main_heavy_share))),
        }


def _ideal_main_pct(main_heavy_share: float) -> float:
    """Ideal main-column fraction (percent), driven by the main-heavy share.

    More experience/projects content widens the ideal main column. The band is
    deliberately clamped so a wide-main recommendation can never fall below
    55% or exceed 72% (documented constants).
    """
    return min(72.0, max(55.0, 60.0 + 10.0 * (main_heavy_share * 4.0 - 0.4)))


def _simplicity(mode: LayoutMode, total_units: float) -> float:
    """Documented piecewise simplicity score (higher = simpler/better fit).

    * Single column: strong bonus below ``_SMALL_CONTENT_UNITS`` (do not force
      small resumes into two columns); neutral in the middle band; zero for
      large resumes (dense single column is a poor fit).
    * Two columns: zero below ``_SMALL_CONTENT_UNITS`` (unnecessary); full
      credit once content is large enough to warrant the rail.
    """
    if mode is LayoutMode.SINGLE:
        if total_units <= _SMALL_CONTENT_UNITS:
            return 160.0
        if total_units >= _LARGE_CONTENT_UNITS:
            return 0.0
        return 50.0
    return 0.0 if total_units <= _SMALL_CONTENT_UNITS else 100.0


def _rationale(config: LayoutConfig, totals: _SectionTotals) -> str:
    """Short, deterministic, non-AI explanation of the recommendation."""
    if config.mode is LayoutMode.SINGLE:
        if totals.total_units >= _LARGE_CONTENT_UNITS:
            return (
                "This base layout offers a single main column only, so the "
                "candidate set is constrained to single-column."
            )
        return "Small resume; single-column is simpler and sufficient for the estimated content."
    main_heavy_share = (
        totals.main_heavy_units / totals.total_units if totals.total_units > 0 else 0.0
    )
    if main_heavy_share >= 0.4:
        return (
            f"Experience-heavy resume; {config.ratio.value} provides a wider main "
            f"column while keeping supporting sections on the {config.sidebar.value} rail."
        )
    return (
        f"Balanced resume; {config.ratio.value} two-column layout with the rail "
        f"on the {config.sidebar.value}."
    )
