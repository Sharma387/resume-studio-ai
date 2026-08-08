"""Layout metadata — immutable, versioned identity and descriptive data."""

from __future__ import annotations

from functools import total_ordering

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.rendering.common.section_types import SECTION_REGISTRY

#: Origin marker for built-in (non-plugin) layouts.
CORE_ORIGIN = "core"


@total_ordering
class LayoutVersion(BaseModel):
    """Semantic version (major.minor.patch)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    major: int = Field(ge=0)
    minor: int = Field(ge=0)
    patch: int = Field(ge=0)

    @classmethod
    def parse(cls, value: str) -> LayoutVersion:
        """Parse a ``"major.minor.patch"`` string."""
        parts = value.strip().split(".")
        if len(parts) != 3 or not all(part.isdigit() for part in parts):
            raise ValueError(f"invalid semantic version '{value}'")
        return cls(major=int(parts[0]), minor=int(parts[1]), patch=int(parts[2]))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, LayoutVersion):
            return NotImplemented
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)


class LayoutMetadata(BaseModel):
    """Immutable metadata for a layout definition.

    ``layout_id`` is the canonical registry key (e.g. ``"executive"``).
    ``stable_id`` is the permanent, versioned identity (e.g.
    ``layout.executive.v1``) that never changes; display names may.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    layout_id: str = Field(min_length=1)
    stable_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    description: str = ""
    version: LayoutVersion
    api_version: LayoutVersion
    engine_version: LayoutVersion
    author: str = "RSAI"
    plugin_origin: str = CORE_ORIGIN
    tags: tuple[str, ...] = ()
    industry: tuple[str, ...] = ()
    experience_level: tuple[str, ...] = ()
    ats_score: int = Field(default=70, ge=0, le=100)
    ats_safe: bool = True
    supports_sidebar: bool = False
    supports_photo: bool = False
    supports_timeline: bool = False
    supports_metrics: bool = False
    supports_badges: bool = False
    supports_qrcode: bool = False
    supports_multicolumn: bool = False
    supports_multiple_pages: bool = True
    recommended_sections: tuple[str, ...] = ()
    deprecated: bool = False
    experimental: bool = False

    @model_validator(mode="after")
    def _validate_metadata(self) -> LayoutMetadata:
        for section in self.recommended_sections:
            if not SECTION_REGISTRY.is_valid(section):
                raise ValueError(f"recommended section '{section}' is not a known section type")
        return self
