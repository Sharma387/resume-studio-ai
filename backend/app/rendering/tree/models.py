"""Render Tree — the intermediate, format-agnostic rendering document.

The Render Tree is the single source of truth for resume *structure* (ADR-3.0-01).
It decouples the Layout Engine's output from any concrete format (HTML, PDF,
DOCX, PPTX, PNG, JSON). Layouts compose components into a tree; format renderers
consume the tree.

Model conventions
-----------------
* A tree is a hierarchy of :class:`RenderNode` objects rooted at a node whose
  ``kind`` is :attr:`NodeKind.DOCUMENT`.
* **Structural** kinds own child nodes and never carry ``data``:
  ``document → page → region → section → block`` (block may itself be a
  container: ``grid`` / ``row`` / ``list`` / ``timeline`` of blocks).
* **Leaf** (unit) kinds carry a typed ``data`` payload and never have children.
* ``classes`` hold structural, non-visual hooks only. ``token_keys`` reference
  theme tokens by name so themes never influence structure.
* Cross-node invariants (unique ids, region reference integrity, ATS text
  order, span sums) are enforced by the TreeValidator, not by this model.

This module is purely additive and changes nothing in the existing rendering
subsystem.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class NodeKind(str, Enum):
    """Every node kind expressible in a render tree."""

    # Structural
    DOCUMENT = "document"
    PAGE = "page"
    REGION = "region"
    SECTION = "section"
    BLOCK = "block"
    GRID = "grid"
    ROW = "row"
    LIST = "list"
    TIMELINE = "timeline"
    # Leaf units
    TEXT = "text"
    PARAGRAPH = "paragraph"
    BULLET = "bullet"
    LINK = "link"
    TIME = "time"
    ICON = "icon"
    BADGE = "badge"
    METRIC = "metric"
    IMAGE = "image"
    QR_CODE = "qr_code"
    DIVIDER = "divider"
    SPACER = "spacer"
    PAGE_BREAK = "page_break"


# ── Page geometry ─────────────────────────────────────────────────────────────


class PageSize(BaseModel):
    """A physical page size in millimetres."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    width_mm: float = Field(gt=0)
    height_mm: float = Field(gt=0)


A4 = PageSize(id="A4", width_mm=210.0, height_mm=297.0)
LETTER = PageSize(id="Letter", width_mm=215.9, height_mm=279.4)


class PageMargins(BaseModel):
    """Page margins in millimetres."""

    model_config = ConfigDict(extra="forbid")

    top_mm: float = Field(default=14.0, ge=0)
    right_mm: float = Field(default=14.0, ge=0)
    bottom_mm: float = Field(default=14.0, ge=0)
    left_mm: float = Field(default=14.0, ge=0)


# ── Leaf unit payloads ────────────────────────────────────────────────────────


class InlineRun(BaseModel):
    """A styled inline fragment inside a text unit.

    When ``runs`` is present on a unit, renderers MUST emit the runs and MUST
    ignore the unit's plain ``text`` for presentation; ``text`` remains the
    concatenation of the runs and is the ATS/plain-text representation.
    """

    model_config = ConfigDict(extra="forbid")

    text: str
    bold: bool = False
    italic: bool = False


class TextData(BaseModel):
    """Plain text unit."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["text"]
    text: str
    runs: tuple[InlineRun, ...] = Field(default=())


class ParagraphData(TextData):
    type: Literal["paragraph"]


class BulletData(TextData):
    type: Literal["bullet"]


class LinkData(BaseModel):
    """Hyperlink unit."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["link"]
    text: str
    url: str


class TimeData(BaseModel):
    """A date/period unit (e.g. an employment period)."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["time"]
    text: str
    start: str | None = None
    end: str | None = None
    current: bool = False


class IconData(BaseModel):
    """An icon reference (resolved by the theme/renderer)."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["icon"]
    name: str
    label: str | None = None


class BadgeData(BaseModel):
    """A chip/label unit (e.g. a skill badge)."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["badge"]
    text: str


class MetricData(BaseModel):
    """A quantified metric unit (value + optional label)."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["metric"]
    value: str
    label: str | None = None


class ImageData(BaseModel):
    """A raster/vector image unit."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["image"]
    src: str
    alt: str | None = None


class QrCodeData(BaseModel):
    """A QR-code unit (e.g. a link or vCard)."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["qr_code"]
    value: str
    label: str | None = None


class DividerData(BaseModel):
    """A horizontal rule unit."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["divider"]


class SpacerData(BaseModel):
    """A vertical spacer unit."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["spacer"]
    size: int = Field(default=1, ge=0)


class PageBreakData(BaseModel):
    """A hard page-break unit."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["page_break"]


RenderUnitData = Annotated[
    TextData
    | ParagraphData
    | BulletData
    | LinkData
    | TimeData
    | IconData
    | BadgeData
    | MetricData
    | ImageData
    | QrCodeData
    | DividerData
    | SpacerData
    | PageBreakData,
    Field(discriminator="type"),
]


# ── Structural rules ──────────────────────────────────────────────────────────


_STRUCTURAL_KINDS = {
    NodeKind.DOCUMENT,
    NodeKind.PAGE,
    NodeKind.REGION,
    NodeKind.SECTION,
    NodeKind.BLOCK,
    NodeKind.GRID,
    NodeKind.ROW,
    NodeKind.LIST,
    NodeKind.TIMELINE,
}

_LEAF_KINDS = set(NodeKind) - _STRUCTURAL_KINDS

# Kinds that require a unit payload.
_REQUIRES_DATA = {
    NodeKind.TEXT,
    NodeKind.PARAGRAPH,
    NodeKind.BULLET,
    NodeKind.LINK,
    NodeKind.TIME,
    NodeKind.ICON,
    NodeKind.BADGE,
    NodeKind.METRIC,
    NodeKind.IMAGE,
    NodeKind.QR_CODE,
}

# The unit payload ``type`` expected for each leaf kind.
_DATA_TYPE_BY_KIND = {
    NodeKind.TEXT: "text",
    NodeKind.PARAGRAPH: "paragraph",
    NodeKind.BULLET: "bullet",
    NodeKind.LINK: "link",
    NodeKind.TIME: "time",
    NodeKind.ICON: "icon",
    NodeKind.BADGE: "badge",
    NodeKind.METRIC: "metric",
    NodeKind.IMAGE: "image",
    NodeKind.QR_CODE: "qr_code",
    NodeKind.DIVIDER: "divider",
    NodeKind.SPACER: "spacer",
    NodeKind.PAGE_BREAK: "page_break",
}

# Which child kinds each structural kind may contain.
_ALLOWED_CHILDREN: dict[NodeKind, set[NodeKind]] = {
    NodeKind.DOCUMENT: {NodeKind.PAGE},
    NodeKind.PAGE: {NodeKind.REGION, NodeKind.PAGE_BREAK},
    NodeKind.REGION: {NodeKind.SECTION, NodeKind.PAGE_BREAK},
    NodeKind.SECTION: {NodeKind.BLOCK, NodeKind.GRID, NodeKind.ROW, NodeKind.LIST, NodeKind.TIMELINE},
    NodeKind.BLOCK: _LEAF_KINDS,
    NodeKind.GRID: {NodeKind.BLOCK},
    NodeKind.ROW: {NodeKind.BLOCK},
    NodeKind.LIST: {NodeKind.BLOCK},
    NodeKind.TIMELINE: {NodeKind.BLOCK},
}


class RenderNode(BaseModel):
    """A single node in the render tree.

    Structural kinds own ``children``; leaf kinds own a typed ``data`` payload.
    Structural invariants are validated eagerly on construction.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    kind: NodeKind
    content_ref: str | None = None
    region: str | None = None
    span: int = Field(default=1, ge=1)
    column_index: int | None = Field(default=None, ge=1)
    order: int = Field(default=0)
    classes: tuple[str, ...] = Field(default_factory=tuple)
    token_keys: dict[str, str] = Field(default_factory=dict)
    page_size: PageSize | None = None
    margins: PageMargins | None = None
    column_ratios: tuple[int, int] | None = None
    gap_mm: float | None = None
    children: tuple[RenderNode, ...] = Field(default_factory=tuple)
    data: RenderUnitData | None = None

    @property
    def is_leaf(self) -> bool:
        """True when this node is a leaf unit (no children allowed)."""
        return self.kind in _LEAF_KINDS

    @model_validator(mode="after")
    def _validate_structure(self) -> RenderNode:
        if self.is_leaf:
            if self.children:
                raise ValueError(f"Leaf node kind '{self.kind.value}' cannot have children")
            if self.data is None and self.kind in _REQUIRES_DATA:
                raise ValueError(f"Node kind '{self.kind.value}' requires unit data")
            if self.data is not None:
                expected = _DATA_TYPE_BY_KIND[self.kind]
                if self.data.type != expected:
                    raise ValueError(
                        f"Node kind '{self.kind.value}' expects data type '{expected}', got '{self.data.type}'"
                    )
        else:
            if self.data is not None:
                raise ValueError(f"Structural node kind '{self.kind.value}' cannot carry unit data")
            allowed = _ALLOWED_CHILDREN.get(self.kind, set())
            for child in self.children:
                if child.kind not in allowed:
                    raise ValueError(f"Node kind '{self.kind.value}' cannot contain child kind '{child.kind.value}'")

        if self.kind is NodeKind.PAGE:
            if self.page_size is None or self.margins is None:
                raise ValueError("Page node requires page_size and margins")
        elif self.page_size is not None or self.margins is not None:
            raise ValueError("Only page nodes may set page_size and margins")

        return self


RenderNode.model_rebuild()
