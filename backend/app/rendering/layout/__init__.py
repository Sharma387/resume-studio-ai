"""Layout Registry — declarative, immutable source of truth for resume layouts."""

from app.rendering.layout.layout_balancer import (
    CandidateScore,
    LayoutBalancer,
    LayoutBalanceResult,
)
from app.rendering.layout.layout_capabilities import LayoutCapabilities, LayoutCapability
from app.rendering.layout.layout_config import (
    ColumnRatio,
    Density,
    GapSize,
    LayoutConfig,
    LayoutMode,
    SectionLayoutConfig,
    SidebarSide,
)
from app.rendering.layout.layout_definition import (
    GridConfig,
    LayoutDefinition,
    PageMargins,
    PageOptions,
    ThemeCompatibility,
)
from app.rendering.layout.layout_metadata import CORE_ORIGIN, LayoutMetadata, LayoutVersion
from app.rendering.layout.layout_regions import RegionDefinition, RegionType
from app.rendering.layout.layout_registry import (
    LayoutLookupError,
    LayoutRegistrationError,
    LayoutRegistry,
    LayoutRegistryError,
)
from app.rendering.layout.layout_resolver import LayoutResolver, LayoutResolverError, resolve_layout
from app.rendering.layout.layout_validation import ValidationRules
from app.rendering.layout.placement_rules import PlacementRule
from app.rendering.layout.reference_layouts import REFERENCE_LAYOUTS

__all__ = [
    "CORE_ORIGIN",
    "CandidateScore",
    "ColumnRatio",
    "Density",
    "GapSize",
    "GridConfig",
    "LayoutCapabilities",
    "LayoutCapability",
    "LayoutConfig",
    "LayoutDefinition",
    "LayoutBalanceResult",
    "LayoutBalancer",
    "LayoutLookupError",
    "LayoutMetadata",
    "LayoutMode",
    "LayoutRegistrationError",
    "LayoutRegistry",
    "LayoutRegistryError",
    "LayoutResolver",
    "LayoutResolverError",
    "LayoutVersion",
    "PageMargins",
    "PageOptions",
    "PlacementRule",
    "REFERENCE_LAYOUTS",
    "RegionDefinition",
    "RegionType",
    "SectionLayoutConfig",
    "SidebarSide",
    "ThemeCompatibility",
    "ValidationRules",
    "resolve_layout",
]
