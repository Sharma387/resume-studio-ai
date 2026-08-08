"""Layout regions — immutable region definitions."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.rendering.common.section_types import SECTION_REGISTRY


class RegionType(str, Enum):
    """Semantic role of a region within a layout."""

    HEADER = "header"
    MAIN = "main"
    SIDEBAR = "sidebar"
    FOOTER = "footer"
    FULL_WIDTH = "full_width"
    CUSTOM = "custom"


class RegionDefinition(BaseModel):
    """A named region of a layout (e.g. main column, sidebar)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    identifier: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    region_type: RegionType = RegionType.CUSTOM
    column_span: int = Field(default=1, ge=1)
    ordering: int = 0
    allowed_sections: tuple[str, ...] = ()
    required: bool = False
    repeatable: bool = False

    @model_validator(mode="after")
    def _validate_region(self) -> RegionDefinition:
        for section in self.allowed_sections:
            if not SECTION_REGISTRY.is_valid(section):
                raise ValueError(
                    f"region '{self.identifier}' references unknown section '{section}'"
                )
        return self
