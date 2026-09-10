"""Placement rules — how sections may be placed within a layout.

Placement rules are declarative constraints only. They carry no rendering
logic; the TreeBuilder consumes them later.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.rendering.common.section_types import SECTION_REGISTRY


class PlacementRule(BaseModel):
    """A per-section-type placement rule within a layout."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    section: str
    allowed_regions: tuple[str, ...] = ()
    preferred_region: str | None = None
    fallback_region: str | None = None
    required: bool = False
    min_occurrences: int = Field(default=0, ge=0)
    max_occurrences: int | None = Field(default=None, ge=1)
    ordering: int = 0
    default_variant: str = "default"
    options: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_rule(self) -> PlacementRule:
        if not SECTION_REGISTRY.is_valid(self.section):
            raise ValueError(f"placement references unknown section '{self.section}'")
        if self.max_occurrences is not None and self.min_occurrences > self.max_occurrences:
            raise ValueError(f"placement for '{self.section}' min_occurrences exceeds max_occurrences")
        return self
