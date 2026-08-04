"""Section component contract for the resume rendering engine.

A :class:`SectionComponent` is the single extension point the TreeBuilder uses
to turn resume content into Render Tree nodes. The TreeBuilder never contains
section-specific logic: it resolves the component for a section type via the
:class:`~app.rendering.components.registry.ComponentRegistry` and delegates.

The contract is renderer-independent — components emit Render Tree nodes only.
No HTML, CSS, Jinja, or PDF logic belongs here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.rendering.tree import RenderNode

#: Input payload for a section component. A plain mapping today; the Content
#: View Model unit will refine this type without changing the contract shape.
SectionContent = Mapping[str, Any]


class ComponentMetadata(BaseModel):
    """Immutable metadata describing a section component."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    section_type: str = Field(min_length=1)
    name: str = Field(min_length=1)
    version: str = "1.0.0"
    description: str = ""
    ats_safe: bool = True
    supported_regions: tuple[str, ...] = ("main", "sidebar")


class ComponentValidationResult(BaseModel):
    """Outcome of validating a section component's input."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    valid: bool
    errors: list[str] = Field(default_factory=list)


class SectionComponent(ABC):
    """Base contract for a renderable resume section."""

    @abstractmethod
    def metadata(self) -> ComponentMetadata:
        """Return immutable metadata describing this component."""

    def section_type(self) -> str:
        """The unique section type this component handles."""
        return self.metadata().section_type

    @abstractmethod
    def validate_input(self, content: SectionContent) -> ComponentValidationResult:
        """Validate ``content`` before building render nodes."""

    @abstractmethod
    def build_render_nodes(
        self,
        content: SectionContent,
        *,
        region: str | None = None,
        order: int = 0,
    ) -> RenderNode:
        """Build the Render Tree subtree for ``content``.

        Components emit Render Tree nodes only; they never decide column
        placement or theme. The returned node is a ``SECTION`` whose subtree is
        valid at the model level; the TreeBuilder supplies region/order context.
        """
