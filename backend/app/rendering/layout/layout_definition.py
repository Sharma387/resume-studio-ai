"""Layout definition — the declarative, immutable composition of a layout."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.rendering.layout.layout_capabilities import LayoutCapabilities
from app.rendering.layout.layout_metadata import LayoutMetadata
from app.rendering.layout.layout_regions import RegionDefinition, RegionType
from app.rendering.layout.layout_validation import ValidationRules
from app.rendering.layout.placement_rules import PlacementRule

# metadata.supports_*  ↔  capabilities.* consistency map
_CAPABILITY_SYNC: tuple[tuple[str, str], ...] = (
    ("supports_sidebar", "sidebar"),
    ("supports_photo", "photo"),
    ("supports_timeline", "timeline"),
    ("supports_metrics", "metrics"),
    ("supports_badges", "badges"),
    ("supports_qrcode", "qr_code"),
    ("supports_multicolumn", "multi_column"),
    ("supports_multiple_pages", "multi_page"),
)


class GridConfig(BaseModel):
    """Declarative grid configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    columns: int = Field(default=12, ge=1, le=24)
    template_areas: tuple[str, ...] = ()
    gap_mm: float = Field(default=0, ge=0)
    max_content_width_mm: float | None = Field(default=None, gt=0)


class PageMargins(BaseModel):
    """Page margins in millimetres (top, right, bottom, left)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    top_mm: float = Field(default=14.0, ge=0)
    right_mm: float = Field(default=14.0, ge=0)
    bottom_mm: float = Field(default=14.0, ge=0)
    left_mm: float = Field(default=14.0, ge=0)


class PageOptions(BaseModel):
    """Page-level configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    page_size: Literal["A4", "Letter"] = "A4"
    margins: PageMargins = Field(default_factory=PageMargins)


class ThemeCompatibility(BaseModel):
    """Which themes a layout is compatible with."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    supported_theme_ids: tuple[str, ...] = ()
    supports_any_theme: bool = True


class LayoutDefinition(BaseModel):
    """The complete, immutable, declarative description of a layout.

    Combines metadata, capabilities, regions, placement rules, grid, page
    options, and validation rules. Purely data — no rendering behaviour.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    metadata: LayoutMetadata
    capabilities: LayoutCapabilities
    regions: tuple[RegionDefinition, ...]
    placement_rules: tuple[PlacementRule, ...] = ()
    grid: GridConfig = Field(default_factory=GridConfig)
    page: PageOptions = Field(default_factory=PageOptions)
    validation: ValidationRules = Field(default_factory=ValidationRules)
    theme_compatibility: ThemeCompatibility = Field(default_factory=ThemeCompatibility)

    @property
    def layout_id(self) -> str:
        return self.metadata.layout_id

    @property
    def stable_id(self) -> str:
        return self.metadata.stable_id

    @model_validator(mode="after")
    def _validate_definition(self) -> LayoutDefinition:
        metadata = self.metadata
        if not self.regions:
            raise ValueError("layout must declare at least one region")

        # Region structural checks: full-width regions (span == columns) occupy
        # their own grid row; the remaining regions must fit the column budget.
        region_ids = [region.identifier for region in self.regions]
        if len(region_ids) != len(set(region_ids)):
            raise ValueError("region identifiers must be unique")
        if len(self.regions) > self.grid.columns:
            raise ValueError("more regions than grid columns")
        partial_span = sum(
            region.column_span for region in self.regions if region.column_span < self.grid.columns
        )
        if partial_span > self.grid.columns:
            raise ValueError(
                f"region column spans sum {partial_span} exceeds grid columns {self.grid.columns}"
            )
        for region in self.regions:
            if region.column_span > self.grid.columns:
                raise ValueError(f"region '{region.identifier}' column span exceeds grid columns")

        if self.validation.require_main_region:
            if not any(region.region_type is RegionType.MAIN for region in self.regions):
                raise ValueError("layout requires a MAIN region")
        if len(self.regions) < self.validation.min_regions:
            raise ValueError("layout has fewer regions than validation.min_regions")
        if self.validation.max_regions is not None and len(self.regions) > self.validation.max_regions:
            raise ValueError("layout has more regions than validation.max_regions")

        # Capability consistency
        for meta_field, cap_field in _CAPABILITY_SYNC:
            if getattr(metadata, meta_field) != getattr(self.capabilities, cap_field):
                raise ValueError(
                    f"capability conflict: metadata.{meta_field} != capabilities.{cap_field}"
                )
        if any(region.region_type is RegionType.SIDEBAR for region in self.regions):
            if not self.capabilities.sidebar:
                raise ValueError("layout has a SIDEBAR region but capabilities.sidebar is false")
        if len(self.regions) > 1 and not self.capabilities.multi_column:
            raise ValueError("multiple regions require capabilities.multi_column")

        # Placement rules
        if not self.placement_rules and not self.validation.allow_empty_placement:
            raise ValueError("layout disallows empty placement but defines no placement rules")
        if self.validation.max_placements is not None:
            if len(self.placement_rules) > self.validation.max_placements:
                raise ValueError("layout exceeds validation.max_placements")
        if self.validation.max_sections is not None:
            distinct = {rule.section for rule in self.placement_rules}
            if len(distinct) > self.validation.max_sections:
                raise ValueError("layout exceeds validation.max_sections")

        for rule in self.placement_rules:
            declared = set(region_ids)
            for region in rule.allowed_regions:
                if region not in declared:
                    raise ValueError(
                        f"placement for '{rule.section}' references unknown region '{region}'"
                    )
            for region in (rule.preferred_region, rule.fallback_region):
                if region is not None and region not in declared:
                    raise ValueError(
                        f"placement for '{rule.section}' references unknown region '{region}'"
                    )

        return self
