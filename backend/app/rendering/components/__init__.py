"""Section component registry — the TreeBuilder's extension point for resume sections."""

from app.rendering.components.base import (
    ComponentMetadata,
    ComponentValidationResult,
    SectionComponent,
    SectionContent,
)
from app.rendering.components.reference import (
    AwardsComponent,
    CertificationsComponent,
    EducationComponent,
    ExperienceComponent,
    LanguagesComponent,
    ProfileComponent,
    ProjectsComponent,
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
    "AwardsComponent",
    "CertificationsComponent",
    "EducationComponent",
    "ExperienceComponent",
    "LanguagesComponent",
    "ProfileComponent",
    "ProjectsComponent",
    "SectionComponent",
    "SectionContent",
    "SkillsComponent",
    "SummaryComponent",
]
