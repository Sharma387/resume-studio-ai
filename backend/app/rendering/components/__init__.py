"""Section component registry — the TreeBuilder's extension point for resume sections."""

from app.rendering.components.base import (
    ComponentMetadata,
    ComponentValidationResult,
    SectionComponent,
    SectionContent,
)
from app.rendering.components.reference import (
    CertificationsComponent,
    EducationComponent,
    ExperienceComponent,
    ProfileComponent,
    SkillsComponent,
    SummaryComponent,
)
from app.rendering.components.registry import (
    ComponentLookupError,
    ComponentRegistrationError,
    ComponentRegistry,
    ComponentRegistryError,
)

__all__ = [
    "ComponentLookupError",
    "ComponentMetadata",
    "ComponentRegistrationError",
    "ComponentRegistry",
    "ComponentRegistryError",
    "ComponentValidationResult",
    "CertificationsComponent",
    "EducationComponent",
    "ExperienceComponent",
    "ProfileComponent",
    "SectionComponent",
    "SectionContent",
    "SkillsComponent",
    "SummaryComponent",
]
