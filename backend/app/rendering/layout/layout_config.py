"""Layout configuration — declarative, per-resume/per-variant layout preferences.

Configuration only: carries *preferences* (``mode``, ``sidebar``, ``ratio``,
``gap``, ``density`` and per-section placement/order/visibility) that the
future ``LayoutResolver`` (P3.2) will consume to derive a concrete
:class:`LayoutDefinition`. Nothing here touches the rendering pipeline.

Every value is a safe, constrained choice (enums / bounded ints) — never raw
CSS. ``None`` section fields mean "inherit the layout default" (auto).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.rendering.common.section_types import SECTION_REGISTRY
from app.rendering.layout.layout_regions import RegionType


class LayoutMode(str, Enum):
    """Overall column structure of the layout."""

    SINGLE = "single"
    TWO_COLUMN = "two_column"


class SidebarSide(str, Enum):
    """Which side the supporting rail (sidebar) sits on."""

    LEFT = "left"
    RIGHT = "right"


class ColumnRatio(str, Enum):
    """Main-column / supporting-rail width ratio (two-column modes only)."""

    RATIO_30_70 = "30/70"
    RATIO_32_68 = "32/68"
    RATIO_35_65 = "35/65"
    RATIO_40_60 = "40/60"


class GapSize(str, Enum):
    """Gutter scale between layout regions."""

    NONE = "none"
    COMPACT = "compact"
    BALANCED = "balanced"
    WIDE = "wide"


class Density(str, Enum):
    """Vertical spacing density (mirrors theme ``SpacingTokens.density``)."""

    COMPACT = "compact"
    NORMAL = "normal"
    SPACIOUS = "spacious"


class SectionLayoutConfig(BaseModel):
    """Per-section override.

    Every field is optional; ``None`` inherits the layout's default.
    ``region`` reuses :class:`RegionType` — ``None`` means "auto".
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    region: RegionType | None = None
    order: int | None = Field(default=None, ge=0)
    visible: bool | None = None


class LayoutConfig(BaseModel):
    """Per-resume/per-variant layout preferences (configuration only)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: LayoutMode = LayoutMode.SINGLE
    sidebar: SidebarSide = SidebarSide.LEFT
    ratio: ColumnRatio = ColumnRatio.RATIO_35_65
    gap: GapSize = GapSize.BALANCED
    density: Density = Density.NORMAL
    sections: dict[str, SectionLayoutConfig] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate(self) -> LayoutConfig:
        for section in self.sections:
            if not SECTION_REGISTRY.is_valid(section):
                raise ValueError(f"layout config references unknown section '{section}'")
        return self
