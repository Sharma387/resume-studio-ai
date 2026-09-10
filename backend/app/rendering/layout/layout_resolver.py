"""LayoutResolver — derive a concrete LayoutDefinition from a LayoutConfig.

Purely declarative and deterministic: ``resolve(base, config)`` returns a new,
immutable :class:`LayoutDefinition` that combines the base layout's structure
with the requested preferences. The base definition is never mutated.

Semantics
---------
* ``mode`` — ``single`` collapses to one full-width MAIN region (dropping any
  sidebar/secondary rail); ``two_column`` requires the base layout to already
  declare a MAIN plus a SIDEBAR or CUSTOM rail, and re-orders the two columns.
* ``sidebar`` — controls column ordering via region ``ordering`` (the DOM/grid
  order the TreeBuilder sorts by): ``left`` → rail before main, ``right`` →
  main before rail. Header/footer/full-width regions keep their position.
* ``ratio`` — stored *exactly* as ``(rail, main)`` fr units in
  ``GridConfig.column_ratios`` (e.g. ``35/65`` → ``(35, 65)``). The current
  renderer draws the 12-column integer-span grid, so the exact split is not
  yet visual; honoring ``column_ratios`` in CSS is a later (P3.3) step. The
  resolver never approximates a ratio to an integer span.
* ``gap`` — mapped to ``GridConfig.gap_mm`` (declarative; the renderer's CSS
  ``column-gap`` is not driven by it yet — later phase).
* ``density`` — preserved on the config only; the resolver does not change
  rendering behaviour.
* ``sections[].region`` — overrides the placement preference via
  ``PlacementRule.preferred_region``. The target region must exist in the
  resolved layout and must allow the section (``RegionDefinition.
  allowed_sections``); otherwise a :class:`LayoutResolverError` is raised.
  ``None`` (auto) leaves the base preference untouched.
* ``sections[].order`` — overrides ``PlacementRule.ordering``. Precedence:
  explicit ``LayoutConfig`` order wins over the base rule's ordering; content
  ``section_order`` only breaks ties between equal orderings.
* ``sections[].visible`` — **not applied**: the layout model has no hide
  mechanism, so the resolver neither drops the section nor pretends it can.
  Visibility is deferred to a later phase.
"""

from __future__ import annotations

from app.rendering.layout.layout_config import (
    ColumnRatio,
    GapSize,
    LayoutConfig,
    LayoutMode,
    SidebarSide,
)
from app.rendering.layout.layout_definition import GridConfig, LayoutDefinition
from app.rendering.layout.layout_regions import RegionType
from app.rendering.layout.placement_rules import PlacementRule

#: GapSize → ``GridConfig.gap_mm`` (millimetres).
_GAP_MM: dict[GapSize, float] = {
    GapSize.NONE: 0.0,
    GapSize.COMPACT: 4.0,
    GapSize.BALANCED: 8.0,
    GapSize.WIDE: 16.0,
}

#: ColumnRatio → exact ``(rail, main)`` fr split (rail = sidebar/secondary).
_RATIO_SPLIT: dict[ColumnRatio, tuple[int, int]] = {
    ColumnRatio.RATIO_30_70: (30, 70),
    ColumnRatio.RATIO_32_68: (32, 68),
    ColumnRatio.RATIO_35_65: (35, 65),
    ColumnRatio.RATIO_40_60: (40, 60),
}

#: Regions never collapsed away in single-column mode.
_STRUCTURAL_TYPES = (
    RegionType.HEADER,
    RegionType.FOOTER,
    RegionType.FULL_WIDTH,
    RegionType.MAIN,
)

#: A CUSTOM region may serve as the two-column rail (e.g. ``secondary``).
_RAIL_TYPES = (RegionType.SIDEBAR, RegionType.CUSTOM)


class LayoutResolverError(ValueError):
    """Raised when a LayoutConfig cannot be resolved against a layout."""


class LayoutResolver:
    """Pure resolver: ``base LayoutDefinition + LayoutConfig → LayoutDefinition``."""

    def resolve(
        self,
        base_layout: LayoutDefinition,
        config: LayoutConfig,
    ) -> LayoutDefinition:
        """Resolve ``config`` against ``base_layout`` (non-mutating)."""
        if config.mode is LayoutMode.SINGLE:
            regions, rules, grid = self._single_column(base_layout, config)
        else:
            regions, rules, grid = self._two_column(base_layout, config)

        rules = self._apply_section_overrides(regions, rules, config, base_layout.layout_id)
        capabilities = self._sync_capabilities(base_layout.capabilities, regions)
        metadata = self._sync_metadata(base_layout.metadata, capabilities)

        return LayoutDefinition(
            metadata=metadata,
            capabilities=capabilities,
            regions=regions,
            placement_rules=rules,
            grid=grid,
            page=base_layout.page,
            validation=base_layout.validation,
            theme_compatibility=base_layout.theme_compatibility,
        )

    # ── Mode resolution ──────────────────────────────────────────────────────

    def _single_column(
        self,
        base_layout: LayoutDefinition,
        config: LayoutConfig,
    ) -> tuple[tuple, tuple, GridConfig]:
        grid = base_layout.grid
        main = next(
            (region for region in base_layout.regions if region.region_type is RegionType.MAIN),
            None,
        )
        if main is None:
            raise LayoutResolverError(f"layout '{base_layout.layout_id}' has no MAIN region to resolve single-column")
        kept = tuple(region for region in base_layout.regions if region.region_type in _STRUCTURAL_TYPES)
        regions = tuple(
            region.model_copy(
                update={
                    "ordering": self._ordering_for(region),
                    **({"column_span": grid.columns} if region.region_type is RegionType.MAIN else {}),
                }
            )
            for region in kept
        )
        declared = {region.identifier for region in regions}
        rules = tuple(self._sanitize_rule(rule, declared, main.identifier) for rule in base_layout.placement_rules)
        resolved_grid = grid.model_copy(update={"gap_mm": _GAP_MM[config.gap], "column_ratios": None})
        return regions, rules, resolved_grid

    def _two_column(
        self,
        base_layout: LayoutDefinition,
        config: LayoutConfig,
    ) -> tuple[tuple, tuple, GridConfig]:
        main = next(
            (region for region in base_layout.regions if region.region_type is RegionType.MAIN),
            None,
        )
        rail = next(
            (region for region in base_layout.regions if region.region_type in _RAIL_TYPES),
            None,
        )
        if main is None or rail is None:
            raise LayoutResolverError(
                f"layout '{base_layout.layout_id}' has no main + sidebar/secondary pair and cannot resolve two_column"
            )
        ordering: dict[str, int] = {}
        for region in base_layout.regions:
            if region.identifier in (main.identifier, rail.identifier):
                continue
            ordering[region.identifier] = self._ordering_for(region)
        if config.sidebar is SidebarSide.LEFT:
            ordering[rail.identifier] = 1
            ordering[main.identifier] = 2
        else:
            ordering[main.identifier] = 1
            ordering[rail.identifier] = 2
        regions = tuple(
            region.model_copy(update={"ordering": ordering[region.identifier]}) for region in base_layout.regions
        )
        rail_pct, main_pct = _RATIO_SPLIT[config.ratio]
        resolved_grid = base_layout.grid.model_copy(
            update={
                "gap_mm": _GAP_MM[config.gap],
                "column_ratios": (rail_pct, main_pct),
            }
        )
        return regions, base_layout.placement_rules, resolved_grid

    # ── Section overrides ────────────────────────────────────────────────────

    def _apply_section_overrides(
        self,
        regions: tuple,
        rules: tuple,
        config: LayoutConfig,
        layout_id: str,
    ) -> tuple:
        rules = list(rules)
        for section_id, section_cfg in config.sections.items():
            if section_cfg.region is None and section_cfg.order is None:
                continue
            update: dict = {}
            if section_cfg.region is not None:
                target = self._region_of_type(regions, section_cfg.region)
                if target is None:
                    raise LayoutResolverError(
                        f"section '{section_id}' requested region "
                        f"'{section_cfg.region.value}' but layout '{layout_id}' "
                        "has no such region"
                    )
                if target.allowed_sections and section_id not in target.allowed_sections:
                    raise LayoutResolverError(
                        f"section '{section_id}' cannot be placed in region "
                        f"'{target.identifier}' of layout '{layout_id}' "
                        f"(allowed sections: {', '.join(target.allowed_sections)})"
                    )
                update["preferred_region"] = target.identifier
            if section_cfg.order is not None:
                update["ordering"] = section_cfg.order

            index = next(
                (i for i, rule in enumerate(rules) if rule.section == section_id),
                None,
            )
            if index is not None:
                rules[index] = rules[index].model_copy(update=update)
            else:
                rules.append(
                    PlacementRule(
                        section=section_id,
                        preferred_region=update.get("preferred_region"),
                        ordering=update.get("ordering", 0),
                    )
                )
        return tuple(rules)

    # ── Capability / metadata consistency ────────────────────────────────────

    @staticmethod
    def _sync_capabilities(base, regions) -> object:
        sidebar = any(region.region_type is RegionType.SIDEBAR for region in regions)
        multi_column = len(regions) > 1
        return base.model_copy(update={"sidebar": sidebar, "multi_column": multi_column})

    @staticmethod
    def _sync_metadata(base_metadata, capabilities) -> object:
        return base_metadata.model_copy(
            update={
                "supports_sidebar": capabilities.sidebar,
                "supports_multicolumn": capabilities.multi_column,
            }
        )

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _ordering_for(region) -> int:
        if region.region_type is RegionType.FOOTER:
            return 1000
        if region.region_type is RegionType.MAIN:
            return 1
        return 0

    @staticmethod
    def _sanitize_rule(rule: PlacementRule, declared: set[str], main_id: str) -> PlacementRule:
        preferred = rule.preferred_region if rule.preferred_region in declared else main_id
        fallback = rule.fallback_region if rule.fallback_region in declared else None
        allowed = tuple(region for region in rule.allowed_regions if region in declared)
        if preferred == fallback:
            fallback = None
        return rule.model_copy(
            update={
                "preferred_region": preferred,
                "fallback_region": fallback,
                "allowed_regions": allowed,
            }
        )

    @staticmethod
    def _region_of_type(regions: tuple, region_type: RegionType):
        for region in sorted(regions, key=lambda r: (r.ordering, r.identifier)):
            if region.region_type is region_type:
                return region
        return None


def resolve_layout(base_layout: LayoutDefinition, config: LayoutConfig) -> LayoutDefinition:
    """Convenience wrapper around :class:`LayoutResolver`."""
    return LayoutResolver().resolve(base_layout, config)
