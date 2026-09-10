"""Shared section vocabulary for Resume Studio AI (Layout Engine).

Single canonical source of truth for every resume section identifier used
across the rendering architecture: the Content View Model, ``LayoutConfig``
placement, the ``ComponentRegistry``, themes, and (future) plugins all key on
these identifiers. New section types are declared here — never as string
literals in two places.

Identifiers
-----------
* ``SectionType`` — the stable, canonical *section type* (e.g. ``"summary"``),
  the key used by placement, components, and layout configuration.
* ``stable_id`` — a permanent, versioned identity (e.g. ``section.summary.v1``).
  Stable ids never change; display names may.
* ``plugin_origin`` — ``"core"`` for built-ins; marketplace plugins provide
  their own origin identifier.

This is a **leaf module**: it must have zero dependencies on the rest of the
rendering subsystem (tree, layouts, themes, components, renderers, preview).
"""

from __future__ import annotations

import re
import threading
from collections.abc import Mapping
from enum import Enum
from types import MappingProxyType
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

#: Semantic version of this vocabulary — bump on backward-incompatible change.
VOCABULARY_VERSION = "1.0.0"

#: Origin marker for built-in (non-plugin) section definitions.
CORE_ORIGIN = "core"

#: Validator for plugin (extension) section type identifiers (dotted namespace).
_EXT_VALID = re.compile(r"^[a-z][a-z0-9]*(\.[a-z0-9]+)+$")


class SectionType(str, Enum):
    """Stable, canonical section types for the core vocabulary.

    These ids never change (semantic stability). Human-readable labels live in
    ``SectionDefinition.display_name`` and may change.
    """

    SUMMARY = "summary"
    PROFILE = "profile"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    PROJECTS = "projects"
    SKILLS = "skills"
    CERTIFICATIONS = "certifications"
    AWARDS = "awards"
    PUBLICATIONS = "publications"
    PATENTS = "patents"
    LANGUAGES = "languages"
    VOLUNTEER = "volunteer"
    INTERESTS = "interests"
    REFERENCES = "references"
    PORTFOLIO = "portfolio"
    HEADER = "header"
    FOOTER = "footer"
    COVER_LETTER = "cover_letter"
    CUSTOM = "custom"


#: Canonical string values of the core section types (round-trip friendly).
_CORE_VALUE_KEYS: frozenset[str] = frozenset(section.value for section in SectionType)


class SectionCategory(str, Enum):
    """Grouping metadata for a section."""

    HEADER = "header"
    MAIN = "main"
    SIDEBAR = "sidebar"
    FOOTER = "footer"


class SectionDefinition(BaseModel):
    """Immutable metadata describing one section type.

    ``section_type`` is the canonical type: a :class:`SectionType` member for
    core sections, or a validated dotted string for plugin sections.
    ``stable_id`` is the permanent, globally unique identity.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    section_type: SectionType | str
    stable_id: str = ""
    display_name: str = Field(min_length=1)
    category: SectionCategory = SectionCategory.MAIN
    version: str = "1.0.0"
    default_order: int = 100
    ats_priority: int = 50
    visible_by_default: bool = True
    supports_sidebar: bool = False
    supports_timeline: bool = False
    supports_metrics: bool = False
    supports_photo: bool = False
    supports_badges: bool = False
    supports_multicolumn: bool = False
    supports_multiple: bool = False
    plugin_origin: str = CORE_ORIGIN

    @model_validator(mode="after")
    def _validate_definition(self) -> SectionDefinition:
        if not self.stable_id:
            stable_id = _type_key(self.section_type)
            if not stable_id:
                raise ValueError("stable_id must not be empty")
            object.__setattr__(self, "stable_id", f"section.{stable_id}.v1")
        if not isinstance(self.section_type, SectionType):
            key = self.section_type
            if key not in _CORE_VALUE_KEYS and not _EXT_VALID.match(key):
                raise ValueError(f"invalid plugin section_type '{key}' (expected dotted namespace)")
        if not self.stable_id.strip():
            raise ValueError("stable_id must not be empty")
        return self

    @property
    def canonical_id(self) -> str:
        """The canonical section-type string (``"summary"``, not the stable id)."""
        return _type_key(self.section_type)


def _type_key(section_type: SectionType | str) -> str:
    return section_type.value if isinstance(section_type, SectionType) else section_type


# ── Core definitions ──────────────────────────────────────────────────────────


def _core_def(section: SectionType, **overrides: Any) -> SectionDefinition:
    base: dict[str, Any] = {
        "display_name": _LABELS[section],
        "category": _CATEGORIES[section],
        "default_order": _ORDER.get(section, 100),
        "ats_priority": _ATS_PRIORITY.get(section, 50),
        "supports_sidebar": _SIDEBAR.get(section, False),
        "supports_timeline": section is SectionType.EXPERIENCE,
        "supports_metrics": section in {SectionType.EXPERIENCE, SectionType.PROJECTS},
        "supports_badges": section is SectionType.SKILLS,
        "supports_multicolumn": section in {SectionType.SKILLS, SectionType.PROJECTS},
        "supports_multiple": section
        in {
            SectionType.EXPERIENCE,
            SectionType.PROJECTS,
            SectionType.CERTIFICATIONS,
            SectionType.AWARDS,
            SectionType.PUBLICATIONS,
            SectionType.PATENTS,
            SectionType.VOLUNTEER,
        },
        "plugin_origin": CORE_ORIGIN,
    }
    base.update(overrides)
    return SectionDefinition(section_type=section, **base)


_LABELS: dict[SectionType, str] = {
    SectionType.SUMMARY: "Professional Summary",
    SectionType.PROFILE: "Profile",
    SectionType.EXPERIENCE: "Experience",
    SectionType.EDUCATION: "Education",
    SectionType.PROJECTS: "Projects",
    SectionType.SKILLS: "Skills",
    SectionType.CERTIFICATIONS: "Certifications",
    SectionType.AWARDS: "Awards",
    SectionType.PUBLICATIONS: "Publications",
    SectionType.PATENTS: "Patents",
    SectionType.LANGUAGES: "Languages",
    SectionType.VOLUNTEER: "Volunteer",
    SectionType.INTERESTS: "Interests",
    SectionType.REFERENCES: "References",
    SectionType.PORTFOLIO: "Portfolio",
    SectionType.HEADER: "Header",
    SectionType.FOOTER: "Footer",
    SectionType.COVER_LETTER: "Cover Letter",
    SectionType.CUSTOM: "Custom",
}


_CATEGORIES: dict[SectionType, SectionCategory] = {
    SectionType.HEADER: SectionCategory.HEADER,
    SectionType.FOOTER: SectionCategory.FOOTER,
    SectionType.PROFILE: SectionCategory.HEADER,
    SectionType.SUMMARY: SectionCategory.MAIN,
    SectionType.EXPERIENCE: SectionCategory.MAIN,
    SectionType.EDUCATION: SectionCategory.MAIN,
    SectionType.PROJECTS: SectionCategory.MAIN,
    SectionType.PUBLICATIONS: SectionCategory.MAIN,
    SectionType.PORTFOLIO: SectionCategory.MAIN,
    SectionType.PATENTS: SectionCategory.MAIN,
    SectionType.VOLUNTEER: SectionCategory.MAIN,
    SectionType.COVER_LETTER: SectionCategory.MAIN,
    SectionType.CUSTOM: SectionCategory.MAIN,
    SectionType.SKILLS: SectionCategory.SIDEBAR,
    SectionType.CERTIFICATIONS: SectionCategory.SIDEBAR,
    SectionType.AWARDS: SectionCategory.SIDEBAR,
    SectionType.LANGUAGES: SectionCategory.SIDEBAR,
    SectionType.INTERESTS: SectionCategory.SIDEBAR,
    SectionType.REFERENCES: SectionCategory.SIDEBAR,
}


_ORDER: dict[SectionType, int] = {
    SectionType.HEADER: 0,
    SectionType.PROFILE: 5,
    SectionType.SUMMARY: 10,
    SectionType.EXPERIENCE: 20,
    SectionType.PROJECTS: 30,
    SectionType.PORTFOLIO: 35,
    SectionType.PUBLICATIONS: 40,
    SectionType.PATENTS: 45,
    SectionType.EDUCATION: 50,
    SectionType.CERTIFICATIONS: 60,
    SectionType.AWARDS: 70,
    SectionType.VOLUNTEER: 80,
    SectionType.SKILLS: 90,
    SectionType.LANGUAGES: 100,
    SectionType.INTERESTS: 110,
    SectionType.REFERENCES: 120,
    SectionType.CUSTOM: 500,
    SectionType.COVER_LETTER: 200,
    SectionType.FOOTER: 1000,
}


_ATS_PRIORITY: dict[SectionType, int] = {
    SectionType.HEADER: 0,
    SectionType.PROFILE: 20,
    SectionType.SUMMARY: 100,
    SectionType.EXPERIENCE: 90,
    SectionType.SKILLS: 80,
    SectionType.PROJECTS: 75,
    SectionType.EDUCATION: 70,
    SectionType.CERTIFICATIONS: 60,
    SectionType.PUBLICATIONS: 50,
    SectionType.CUSTOM: 10,
    SectionType.FOOTER: 0,
}


_SIDEBAR: dict[SectionType, bool] = {
    SectionType.SKILLS: True,
    SectionType.CERTIFICATIONS: True,
    SectionType.AWARDS: True,
    SectionType.LANGUAGES: True,
    SectionType.INTERESTS: True,
    SectionType.REFERENCES: True,
}


_CORE: tuple[SectionDefinition, ...] = tuple(_core_def(section) for section in SectionType)

_CORE_STABLE_IDS: frozenset[str] = frozenset(definition.stable_id for definition in _CORE)
_CORE_TYPE_KEYS: frozenset[str] = frozenset(_type_key(section) for section in SectionType)


# ── Extension id validation (future plugin sections) ─────────────────────────


class SectionUnknownError(KeyError):
    """Raised when an unregistered section identifier is resolved."""


class SectionRegistrationError(ValueError):
    """Raised when a section definition cannot be registered."""


class SectionRegistry:
    """Thread-safe registry of section definitions (core + plugin extensions).

    Core definitions are immutable and cannot be replaced. Plugins add new
    section types without modifying core code.
    """

    def __init__(self, allow_replacement: bool = False) -> None:
        self._allow_replacement = allow_replacement
        self._by_stable_id: dict[str, SectionDefinition] = {}
        self._by_type: dict[str, SectionDefinition] = {}
        self._lock = threading.RLock()
        for definition in _CORE:
            self._by_stable_id[definition.stable_id] = definition
            self._by_type[definition.canonical_id] = definition

    # Registration lifecycle
    def register(self, definition: SectionDefinition, allow_replacement: bool | None = None) -> None:
        if not isinstance(definition, SectionDefinition):
            raise SectionRegistrationError(f"definition must be a SectionDefinition, got {type(definition).__name__}")
        canonical = definition.canonical_id
        if not canonical or not definition.stable_id:
            raise SectionRegistrationError("section_type and stable_id must not be empty")
        if canonical in _CORE_TYPE_KEYS or definition.stable_id in _CORE_STABLE_IDS:
            raise SectionRegistrationError(f"core section '{canonical}' cannot be replaced")
        effective = self._allow_replacement if allow_replacement is None else allow_replacement
        with self._lock:
            if canonical in self._by_type and not effective:
                raise SectionRegistrationError(f"section_type '{canonical}' already registered")
            if definition.stable_id in self._by_stable_id and not effective:
                raise SectionRegistrationError(f"stable_id '{definition.stable_id}' already registered")
            self._by_stable_id[definition.stable_id] = definition
            self._by_type[canonical] = definition

    # Lookup
    def lookup(self, section_type: SectionType | str) -> SectionDefinition:
        """Resolve by section type (enum member or its value string)."""
        key = _type_key(section_type)
        with self._lock:
            definition = self._by_type.get(key)
        if definition is None:
            raise SectionUnknownError(f"unknown section type '{key}'")
        return definition

    def lookup_by_id(self, stable_id: str) -> SectionDefinition:
        """Resolve by permanent stable id (e.g. ``section.summary.v1``)."""
        with self._lock:
            definition = self._by_stable_id.get(stable_id)
        if definition is None:
            raise SectionUnknownError(f"unknown stable id '{stable_id}'")
        return definition

    def get(self, section_type: SectionType | str) -> SectionDefinition | None:
        try:
            return self.lookup(section_type)
        except SectionUnknownError:
            return None

    def get_by_id(self, stable_id: str) -> SectionDefinition | None:
        try:
            return self.lookup_by_id(stable_id)
        except SectionUnknownError:
            return None

    def contains(self, section_type: SectionType | str) -> bool:
        return self.get(section_type) is not None

    def contains_stable_id(self, stable_id: str) -> bool:
        return self.get_by_id(stable_id) is not None

    def is_valid(self, section_type: SectionType | str) -> bool:
        return self.contains(section_type)

    def validate(self, section_type: SectionType | str) -> None:
        self.lookup(section_type)

    # Listing / ordering
    def list(self) -> tuple[str, ...]:
        """Stable ids in canonical order (core then registered plugins)."""
        with self._lock:
            return tuple(self._by_stable_id.keys())

    def definitions(self) -> tuple[SectionDefinition, ...]:
        with self._lock:
            return tuple(self._by_stable_id.values())

    def ordered(self) -> tuple[SectionDefinition, ...]:
        """Definitions ordered by ``default_order`` (stable for ties)."""
        with self._lock:
            return tuple(
                sorted(
                    self._by_stable_id.values(),
                    key=lambda d: (d.default_order, d.canonical_id),
                )
            )

    def core_ids(self) -> tuple[str, ...]:
        return tuple(section.value for section in SectionType)

    def metadata_map(self) -> Mapping[str, SectionDefinition]:
        with self._lock:
            return MappingProxyType(dict(self._by_stable_id))

    def __len__(self) -> int:
        with self._lock:
            return len(self._by_stable_id)

    def __contains__(self, section_type: object) -> bool:
        return isinstance(section_type, (SectionType, str)) and self.contains(section_type)

    def __iter__(self):
        with self._lock:
            return iter(tuple(self._by_stable_id.keys()))


#: Process-wide singleton, preloaded with the core section vocabulary.
SECTION_REGISTRY = SectionRegistry()
