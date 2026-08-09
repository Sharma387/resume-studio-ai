"""Reference layouts — lightweight data-only layouts validating the registry.

These exist purely to exercise the Layout Registry. They contain no rendering
logic; real archetypes ship in a later phase.
"""

from __future__ import annotations

from app.rendering.layout.layout_capabilities import LayoutCapabilities
from app.rendering.layout.layout_definition import LayoutDefinition
from app.rendering.layout.layout_metadata import LayoutMetadata, LayoutVersion
from app.rendering.layout.layout_regions import RegionDefinition, RegionType
from app.rendering.layout.placement_rules import PlacementRule


def _main(span: int = 12, *, allowed: tuple[str, ...] = ()) -> RegionDefinition:
    return RegionDefinition(
        identifier="main",
        display_name="Main",
        region_type=RegionType.MAIN,
        column_span=span,
        ordering=0,
        allowed_sections=allowed,
        required=True,
    )


#: Candidate identity/header section — placed first in the main region.
_PROFILE_RULE = PlacementRule(section="profile", preferred_region="main", ordering=-10, required=True)


def _build(
    name: str,
    *,
    display_name: str,
    description: str,
    regions: tuple[RegionDefinition, ...],
    capabilities: LayoutCapabilities,
    placement: tuple[PlacementRule, ...] = (),
    recommended: tuple[str, ...] = (),
    ats_score: int = 70,
    ats_safe: bool = True,
) -> LayoutDefinition:
    metadata = LayoutMetadata(
        layout_id=name,
        stable_id=f"layout.{name}.v1",
        display_name=display_name,
        description=description,
        version=LayoutVersion(major=1, minor=0, patch=0),
        api_version=LayoutVersion(major=1, minor=0, patch=0),
        engine_version=LayoutVersion(major=1, minor=0, patch=0),
        supports_sidebar=capabilities.sidebar,
        supports_photo=capabilities.photo,
        supports_timeline=capabilities.timeline,
        supports_metrics=capabilities.metrics,
        supports_badges=capabilities.badges,
        supports_qrcode=capabilities.qr_code,
        supports_multicolumn=capabilities.multi_column,
        supports_multiple_pages=capabilities.multi_page,
        ats_score=ats_score,
        ats_safe=ats_safe,
        recommended_sections=recommended,
    )
    return LayoutDefinition(
        metadata=metadata,
        capabilities=capabilities,
        regions=regions,
        placement_rules=placement,
    )


def executive_layout() -> LayoutDefinition:
    """Single full-width main column; classic executive presentation."""
    return _build(
        "executive",
        display_name="Executive",
        description="Full-width header and clean single-column sections.",
        regions=(_main(),),
        capabilities=LayoutCapabilities(),
        placement=(
            _PROFILE_RULE,
            PlacementRule(section="summary", preferred_region="main", required=True, ordering=0),
            PlacementRule(section="experience", preferred_region="main", ordering=10),
            PlacementRule(section="education", preferred_region="main", ordering=20),
        ),
        recommended=("summary", "experience", "education"),
        ats_score=85,
        ats_safe=True,
    )


def modern_layout() -> LayoutDefinition:
    """Balanced two-column layout."""
    return _build(
        "modern",
        display_name="Modern",
        description="Balanced two-column layout with a secondary column.",
        regions=(
            _main(span=6, allowed=("profile", "summary", "experience", "education")),
            RegionDefinition(
                identifier="secondary",
                display_name="Secondary",
                region_type=RegionType.CUSTOM,
                column_span=6,
                ordering=1,
                allowed_sections=("skills", "certifications", "languages"),
            ),
        ),
        capabilities=LayoutCapabilities(multi_column=True),
        placement=(
            _PROFILE_RULE,
            PlacementRule(section="summary", preferred_region="main", required=True),
            PlacementRule(section="experience", preferred_region="main"),
            PlacementRule(section="skills", preferred_region="secondary"),
        ),
        recommended=("summary", "experience", "skills", "education"),
        ats_score=75,
    )


def sidebar_layout() -> LayoutDefinition:
    """Asymmetric main + sidebar layout."""
    return _build(
        "sidebar",
        display_name="Sidebar",
        description="Main column with a narrow sidebar for skills and contact.",
        regions=(
            _main(span=7, allowed=("profile", "summary", "experience", "education", "projects")),
            RegionDefinition(
                identifier="sidebar",
                display_name="Sidebar",
                region_type=RegionType.SIDEBAR,
                column_span=5,
                ordering=1,
                allowed_sections=("skills", "certifications", "languages", "interests"),
            ),
        ),
        capabilities=LayoutCapabilities(sidebar=True, multi_column=True),
        placement=(
            _PROFILE_RULE,
            PlacementRule(section="summary", preferred_region="main", required=True),
            PlacementRule(section="experience", preferred_region="main"),
            PlacementRule(section="skills", preferred_region="sidebar", fallback_region="main"),
        ),
        recommended=("summary", "experience", "education", "skills"),
        ats_score=78,
    )


def timeline_layout() -> LayoutDefinition:
    """Single column with timeline-style experience and metrics."""
    return _build(
        "timeline",
        display_name="Timeline",
        description="Chronological timeline experience with metric emphasis.",
        regions=(_main(),),
        capabilities=LayoutCapabilities(timeline=True, metrics=True),
        placement=(
            _PROFILE_RULE,
            PlacementRule(section="summary", preferred_region="main", required=True),
            PlacementRule(section="experience", preferred_region="main", default_variant="timeline"),
        ),
        recommended=("summary", "experience", "education"),
        ats_score=72,
    )


def classic_layout() -> LayoutDefinition:
    """Traditional single-column, ATS-first layout."""
    return _build(
        "classic",
        display_name="Classic",
        description="Traditional single-column, ATS-first layout.",
        regions=(_main(),),
        capabilities=LayoutCapabilities(),
        placement=(
            _PROFILE_RULE,
            PlacementRule(section="summary", preferred_region="main", required=True),
            PlacementRule(section="experience", preferred_region="main"),
            PlacementRule(section="education", preferred_region="main"),
            PlacementRule(section="skills", preferred_region="main"),
        ),
        recommended=("summary", "experience", "education", "skills"),
        ats_score=92,
        ats_safe=True,
    )


def minimal_layout() -> LayoutDefinition:
    """Minimal single-column layout with a restrained palette footprint."""
    return _build(
        "minimal",
        display_name="Minimal",
        description="Minimal single-column layout with clean typography.",
        regions=(_main(),),
        capabilities=LayoutCapabilities(),
        placement=(
            _PROFILE_RULE,
            PlacementRule(section="summary", preferred_region="main", required=True),
            PlacementRule(section="experience", preferred_region="main"),
        ),
        recommended=("summary", "experience"),
        ats_score=88,
        ats_safe=True,
    )


REFERENCE_LAYOUTS: tuple[LayoutDefinition, ...] = (
    executive_layout(),
    modern_layout(),
    sidebar_layout(),
    timeline_layout(),
    classic_layout(),
    minimal_layout(),
)
