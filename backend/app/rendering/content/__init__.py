"""Content View Model — layout-independent, renderer-independent resume content."""

from app.rendering.content.builders import cvm_from_resume
from app.rendering.content.models import (
    AwardEntry,
    CertificationEntry,
    ContentView,
    EducationEntry,
    ExperienceEntry,
    LanguageEntry,
    Profile,
    ProjectEntry,
    SkillGroup,
)

__all__ = [
    "AwardEntry",
    "CertificationEntry",
    "ContentView",
    "EducationEntry",
    "ExperienceEntry",
    "LanguageEntry",
    "Profile",
    "ProjectEntry",
    "SkillGroup",
    "cvm_from_resume",
]
