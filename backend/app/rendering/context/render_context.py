"""RenderContext — the immutable execution context for one rendering operation.

RenderContext is a **data bag** of already-resolved inputs. It performs no
lookup and holds no registries: the Layout Registry resolves the
:class:`LayoutDefinition`, the Theme Registry resolves the :class:`ThemePalette`,
and the resulting objects are passed in. It is not a service locator, DI
container, or business-logic engine.

The Content View Model does not exist yet. ``content_ref`` is the narrowest
serialization-safe reference (stable id + content hash); the future CVM will
flow into the builder separately without forcing a premature CVM interface
here.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.rendering.context.context_state import RenderState
from app.rendering.context.context_validation import (
    SemanticVersion,
    validate_resolved_context,
)
from app.rendering.layout.layout_definition import LayoutDefinition
from app.rendering.theme.theme_palette import ThemePalette

_CONTENT_HASH = r"^[0-9a-fA-F]{16,}$"


class ContentReference(BaseModel):
    """A stable, serialization-safe reference to resume content.

    This is a reference, not the Content View Model itself. Resume business
    data never lives in the render context.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    stable_id: str = Field(min_length=1)
    content_hash: str = Field(pattern=_CONTENT_HASH)


class RenderContext(BaseModel):
    """The resolved, immutable inputs for a single rendering/build operation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    content_ref: ContentReference | None = None
    layout: LayoutDefinition
    theme: ThemePalette
    state: RenderState = Field(default_factory=RenderState)
    engine_version: SemanticVersion | None = None

    @model_validator(mode="after")
    def _validate_context(self) -> RenderContext:
        validate_resolved_context(
            layout=self.layout,
            theme=self.theme,
            content_ref=self.content_ref,
            engine_version=self.engine_version,
        )
        return self

    # Convenience accessors (immutable — resolve nothing, look nothing up).
    @property
    def layout_stable_id(self) -> str:
        return self.layout.stable_id

    @property
    def theme_stable_id(self) -> str:
        return self.theme.stable_id
