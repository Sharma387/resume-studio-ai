"""Reference layouts — data-only layouts validating the registry and the
structural identities of the layout engine.

Six visually distinct compositions (the visual layer is applied by the
HTML/PDF renderer via the ``layout-<id>`` document class):

- Executive: full-width serif header + single main column (Executive Luxe).
- Sidebar:   true sidebar composition — light-tint sidebar holds profile and
             supporting sections, main column holds the narrative.
- Modern:    editorial grid — wide story column + narrow supporting rail.
- Classic:   symmetric two-column creative grid (main + secondary).
- Timeline:  single column with a chronological rail treatment.
- Minimal:   single column, typography + whitespace only.
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


def _header() -> RegionDefinition:
    return RegionDefinition(
        identifier="header",
        display_name="Header",
        region_type=RegionType.HEADER,
        column_span=12,
        ordering=0,
        allowed_sections=("profile",),
        required=True,
    )


def _sidebar(*, span: int = 4, allowed: tuple[str, ...] = ()) -> RegionDefinition:
    return RegionDefinition(
        identifier="sidebar",
        display_name="Sidebar",
        region_type=RegionType.SIDEBAR,
        column_span=span,
        ordering=1,
        allowed_sections=allowed or ("profile", "skills", "certifications", "awards", "languages", "interests"),
    )


def _secondary(*, span: int = 3, allowed: tuple[str, ...] = ()) -> RegionDefinition:
    return RegionDefinition(
        identifier="secondary",
        display_name="Secondary",
        region_type=RegionType.CUSTOM,
        column_span=span,
        ordering=1,
        allowed_sections=allowed or ("skills", "certifications", "languages"),
    )


def _build(
    name: str,
    *,
    display_name: str,
    description: str,
    regions: tuple[RegionDefinition, ...],
    capabilities: LayoutCapabilities,
    placement: tuple[PlacementRule, ...],
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
    """Executive Luxe — full-width serif header + dominant single-column body."""
    return _build(
        "executive",
        display_name="Executive Luxe",
        description="Serif-led single-column authority with generous whitespace and restrained hairlines.",
        regions=(_header(), _main()),
        capabilities=LayoutCapabilities(multi_column=True),
        placement=(
            PlacementRule(section="profile", preferred_region="header", required=True, ordering=-10),
            PlacementRule(section="summary", preferred_region="main", required=True, ordering=0),
            PlacementRule(section="experience", preferred_region="main", ordering=10),
            PlacementRule(section="education", preferred_region="main", ordering=20),
            PlacementRule(section="projects", preferred_region="main", ordering=30),
            PlacementRule(section="certifications", preferred_region="main", ordering=40),
            PlacementRule(section="skills", preferred_region="main", ordering=50),
            PlacementRule(section="awards", preferred_region="main", ordering=60),
            PlacementRule(section="languages", preferred_region="main", ordering=70),
        ),
        recommended=("summary", "experience", "education", "projects"),
        ats_score=85,
        ats_safe=True,
    )


def modern_layout() -> LayoutDefinition:
    """Editorial — full-width masthead + wide story column + narrow supporting rail."""
    return _build(
        "modern",
        display_name="Editorial",
        description="Asymmetric editorial grid: wide main column with a narrow supporting rail.",
        regions=(
            _header(),
            _main(span=9, allowed=("summary", "experience", "projects")),
            _secondary(
                span=3,
                allowed=("skills", "certifications", "education", "languages", "awards"),
            ),
        ),
        capabilities=LayoutCapabilities(multi_column=True),
        placement=(
            PlacementRule(section="profile", preferred_region="header", required=True, ordering=-10),
            PlacementRule(section="summary", preferred_region="main", required=True, ordering=0),
            PlacementRule(section="experience", preferred_region="main", ordering=10),
            PlacementRule(section="projects", preferred_region="main", ordering=20),
            PlacementRule(section="skills", preferred_region="secondary", ordering=30),
            PlacementRule(section="certifications", preferred_region="secondary", ordering=40),
            PlacementRule(section="education", preferred_region="secondary", ordering=50),
            PlacementRule(section="languages", preferred_region="secondary", ordering=60),
            PlacementRule(section="awards", preferred_region="secondary", ordering=70),
        ),
        recommended=("summary", "experience", "projects", "skills"),
        ats_score=75,
    )


def sidebar_layout() -> LayoutDefinition:
    """Modern Two-Column — light-tint sidebar (profile + context) beside the main column."""
    return _build(
        "sidebar",
        display_name="Modern Two-Column",
        description="Approximately 28/72 light-tint sidebar with the identity and supporting sections on the rail.",
        regions=(
            _main(span=8, allowed=("summary", "experience", "education", "projects")),
            _sidebar(),
        ),
        capabilities=LayoutCapabilities(sidebar=True, multi_column=True),
        placement=(
            PlacementRule(section="profile", preferred_region="sidebar", required=True, ordering=-10),
            PlacementRule(section="summary", preferred_region="main", required=True, ordering=0),
            PlacementRule(section="experience", preferred_region="main", ordering=10),
            PlacementRule(section="education", preferred_region="main", ordering=20),
            PlacementRule(section="projects", preferred_region="main", ordering=30),
            PlacementRule(section="skills", preferred_region="sidebar", ordering=40),
            PlacementRule(section="certifications", preferred_region="sidebar", ordering=50),
            PlacementRule(section="languages", preferred_region="sidebar", ordering=60),
            PlacementRule(section="awards", preferred_region="sidebar", ordering=70),
        ),
        recommended=("summary", "experience", "education", "skills"),
        ats_score=78,
    )


def timeline_layout() -> LayoutDefinition:
    """Career Timeline — single column with timeline-style experience and metrics."""
    return _build(
        "timeline",
        display_name="Career Timeline",
        description="Chronological career rail: dates, subtle vertical timeline, node indicators.",
        regions=(_main(),),
        capabilities=LayoutCapabilities(timeline=True, metrics=True),
        placement=(
            PlacementRule(section="profile", preferred_region="main", required=True, ordering=-10),
            PlacementRule(section="summary", preferred_region="main", required=True),
            PlacementRule(section="experience", preferred_region="main", default_variant="timeline"),
        ),
        recommended=("summary", "experience", "education"),
        ats_score=72,
    )


def classic_layout() -> LayoutDefinition:
    """Creative Professional — symmetric two-column grid with oversized name typography."""
    return _build(
        "classic",
        display_name="Creative Professional",
        description="Symmetric two-column creative grid: experience/education left, supporting sections right.",
        regions=(
            _main(span=6),
            _secondary(
                span=6,
                allowed=("skills", "certifications", "awards", "languages", "interests"),
            ),
        ),
        capabilities=LayoutCapabilities(multi_column=True),
        placement=(
            PlacementRule(section="profile", preferred_region="main", required=True, ordering=-10),
            PlacementRule(section="summary", preferred_region="main", required=True, ordering=0),
            PlacementRule(section="experience", preferred_region="main", ordering=10),
            PlacementRule(section="education", preferred_region="main", ordering=20),
            PlacementRule(section="projects", preferred_region="main", ordering=30),
            PlacementRule(section="skills", preferred_region="secondary", ordering=40),
            PlacementRule(section="certifications", preferred_region="secondary", ordering=50),
            PlacementRule(section="awards", preferred_region="secondary", ordering=60),
            PlacementRule(section="languages", preferred_region="secondary", ordering=70),
        ),
        recommended=("summary", "experience", "education", "skills"),
        ats_score=80,
        ats_safe=True,
    )


def minimal_layout() -> LayoutDefinition:
    """Nordic Minimal — single column, typography + whitespace as the design."""
    return _build(
        "minimal",
        display_name="Nordic Minimal",
        description="Typography and whitespace only; muted secondary text, no decorative blocks.",
        regions=(_main(),),
        capabilities=LayoutCapabilities(),
        placement=(
            PlacementRule(section="profile", preferred_region="main", required=True, ordering=-10),
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
