"""Validation rules — declarative constraints for a layout definition."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ValidationRules(BaseModel):
    """Declarative structural constraints applied to a layout definition."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    min_regions: int = Field(default=1, ge=0)
    max_regions: int | None = Field(default=None, ge=1)
    require_main_region: bool = True
    allow_empty_placement: bool = True
    max_sections: int | None = Field(default=None, ge=1)
    max_placements: int | None = Field(default=None, ge=1)
