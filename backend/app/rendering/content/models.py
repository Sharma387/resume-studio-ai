"""Content View Model — layout-independent, renderer-independent resume content.

The CVM is the pure representation of candidate content. It knows nothing about
layouts, themes, renderers, or preview services: the same CVM instance can be
supplied to materially different LayoutDefinitions to produce different render
structures without any content change.

This module depends only on the shared section vocabulary (canonical ids); it
must not import layout, theme, context, component, tree, or business/service
modules.
"""

from __future__ import annotations

import hashlib

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.rendering.common.section_types import SECTION_REGISTRY, SectionType


class Profile(BaseModel):
    """Candidate identity and contact information."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    full_name: str = Field(min_length=1)
    professional_title: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    linkedin: str | None = None
    github: str | None = None
    website: str | None = None


class ExperienceEntry(BaseModel):
    """A single work-experience position."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    company: str = Field(min_length=1)
    title: str = Field(min_length=1)
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    current: bool = False
    description: tuple[str, ...] = ()


class EducationEntry(BaseModel):
    """A single education entry."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    institution: str = Field(min_length=1)
    degree: str = Field(min_length=1)
    field: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    gpa: float | None = Field(default=None, ge=0.0, le=4.0)
    achievements: tuple[str, ...] = ()


class SkillGroup(BaseModel):
    """A categorized group of skills."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    category: str = Field(min_length=1)
    skills: tuple[str, ...] = ()


class CertificationEntry(BaseModel):
    """A single certification card or a grouped professional-development record.

    ``category`` present → grouped record (rendered as one logical bullet);
    ``category`` absent → individual certification card.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str | None = Field(default=None, min_length=1)
    issuer: str | None = None
    date: str | None = None
    url: str | None = None
    category: str | None = Field(default=None, min_length=1)
    values: tuple[str, ...] = ()


class ProjectEntry(BaseModel):
    """A single project."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    description: str | None = None
    url: str | None = None
    technologies: tuple[str, ...] = ()


class AwardEntry(BaseModel):
    """A single award or honour."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str = Field(min_length=1)
    issuer: str | None = None
    date: str | None = None


class LanguageEntry(BaseModel):
    """A language with optional proficiency."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    proficiency: str | None = None


#: Content-view section ids → model field names.
_SECTION_FIELDS: dict[str, str] = {
    SectionType.PROFILE.value: "profile",
    SectionType.SUMMARY.value: "summary",
    SectionType.EXPERIENCE.value: "experience",
    SectionType.EDUCATION.value: "education",
    SectionType.SKILLS.value: "skills",
    SectionType.PROJECTS.value: "projects",
    SectionType.CERTIFICATIONS.value: "certifications",
    SectionType.AWARDS.value: "awards",
    SectionType.LANGUAGES.value: "languages",
}


class ContentView(BaseModel):
    """Layout-independent content for one candidate/resume.

    ``section_order`` is *content* ordering (which sections exist and their
    natural order), never layout placement — layouts reorder via their own
    placement rules. When omitted it is derived from present sections using the
    section vocabulary's default order.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    stable_id: str = Field(min_length=1)
    profile: Profile | None = None
    summary: str | None = None
    experience: tuple[ExperienceEntry, ...] = ()
    education: tuple[EducationEntry, ...] = ()
    skills: tuple[SkillGroup, ...] = ()
    certifications: tuple[CertificationEntry, ...] = ()
    projects: tuple[ProjectEntry, ...] = ()
    awards: tuple[AwardEntry, ...] = ()
    languages: tuple[LanguageEntry, ...] = ()
    section_order: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _validate(self) -> ContentView:
        if self.section_order:
            for section in self.section_order:
                if section not in _SECTION_FIELDS:
                    raise ValueError(f"section_order references unknown section '{section}'")
        else:
            object.__setattr__(self, "section_order", self._default_order())
        return self

    # ── Content access (for future TreeBuilder/components) ───────────────────

    def has_section(self, section: str) -> bool:
        """True when ``section`` has content in this view."""
        field = _SECTION_FIELDS.get(section)
        if field is None:
            return False
        return getattr(self, field) not in (None, ())

    def present_sections(self) -> tuple[str, ...]:
        """Present section ids, in canonical vocabulary default order."""
        return tuple(
            sorted(
                (section for section in _SECTION_FIELDS if self.has_section(section)),
                key=lambda s: SECTION_REGISTRY.lookup(s).default_order,
            )
        )

    def section_content(self, section: str) -> object | None:
        """Return the raw content for ``section`` (None when absent/unknown)."""
        field = _SECTION_FIELDS.get(section)
        if field is None:
            return None
        return getattr(self, field)

    def _default_order(self) -> tuple[str, ...]:
        return self.present_sections()

    # ── Stable identity ───────────────────────────────────────────────────────

    @property
    def content_hash(self) -> str:
        """Deterministic SHA-256 over the content (stable id excluded)."""
        payload = self.model_dump_json(exclude={"stable_id"})
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
