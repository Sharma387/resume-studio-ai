"""Theme metadata — immutable, versioned identity and descriptive data."""

from __future__ import annotations

from functools import total_ordering
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

#: Origin marker for built-in (non-plugin) themes.
CORE_ORIGIN = "core"


@total_ordering
class ThemeVersion(BaseModel):
    """Semantic version (major.minor.patch) for a theme."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    major: int = Field(ge=0)
    minor: int = Field(ge=0)
    patch: int = Field(ge=0)

    @classmethod
    def parse(cls, value: str) -> ThemeVersion:
        parts = value.strip().split(".")
        if len(parts) != 3 or not all(part.isdigit() for part in parts):
            raise ValueError(f"invalid semantic version '{value}'")
        return cls(major=int(parts[0]), minor=int(parts[1]), patch=int(parts[2]))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, ThemeVersion):
            return NotImplemented
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)


class ThemeMetadata(BaseModel):
    """Immutable metadata for a theme palette.

    ``theme_id`` is the canonical registry key (e.g. ``"blue"``). ``stable_id``
    is the permanent, versioned identity (e.g. ``theme.blue.v1``) that never
    changes; display names may.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    theme_id: str = Field(min_length=1)
    stable_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    description: str = ""
    version: ThemeVersion
    api_version: ThemeVersion
    engine_version: ThemeVersion
    author: str = "RSAI"
    plugin_origin: str = CORE_ORIGIN
    tags: tuple[str, ...] = ()
    style: Literal["minimal", "professional", "bold", "elegant", "modern"] = "professional"
    dark_mode: bool = False
    deprecated: bool = False
    experimental: bool = False
