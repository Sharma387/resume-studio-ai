"""Render context state — strongly typed, immutable rendering state.

The state identifies *what* is being produced (output format, page, mode), not
*how*. It deliberately contains no renderer-specific implementation details
(no HTML documents, CSS, Jinja environments, PDF canvases, or browser pages).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OutputFormat(str, Enum):
    """The requested output format for a rendering operation."""

    HTML = "html"
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    PNG = "png"
    JSON = "json"


class RenderMode(str, Enum):
    """Whether the output is a preview or a production artifact."""

    PREVIEW = "preview"
    PRODUCTION = "production"


class RenderState(BaseModel):
    """Immutable state for one rendering operation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    output_format: OutputFormat = OutputFormat.HTML
    mode: RenderMode = RenderMode.PRODUCTION
    page_number: int = Field(default=1, ge=1)
    page_count: int | None = Field(default=None, ge=1)
    locale: str = "en-US"
    timezone: str = "UTC"
    accessibility_mode: bool = False
    ats_mode: bool = False
    deterministic: bool = True

    @model_validator(mode="after")
    def _validate_state(self) -> RenderState:
        if self.page_count is not None and self.page_number > self.page_count:
            raise ValueError(
                f"page_number {self.page_number} exceeds page_count {self.page_count}"
            )
        return self
