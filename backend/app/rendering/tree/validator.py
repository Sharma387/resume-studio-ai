"""Cross-node validation for the Render Tree.

The Render Tree model (:mod:`app.rendering.tree.models`) enforces local,
per-node structural invariants eagerly at construction. The
:class:`TreeValidator` enforces the global, cross-node invariants required for
a well-formed render document:

- the tree is rooted at a ``DOCUMENT`` node
- node ids are unique across the whole tree
- every ``REGION`` declares an id and region ids are unique within a page
- any ``region`` reference resolves to a declared region, and ``SECTION`` /
  ``BLOCK`` nodes under a region declare that region (region integrity)
- ``SECTION`` nodes carry a content reference
- text-bearing leaves (text / paragraph / bullet / link / time) carry a
  content reference and non-empty text (ATS provenance)
- horizontal containers (a page's regions, ``grid`` / ``row`` blocks) respect
  the span budget (each child span and the running total ≤ configured columns)

The validator also exposes deterministic text extraction in tree (render)
order — the canonical artifact for ATS-order testing and downstream renderers.

This module is purely additive; it does not change existing rendering
behaviour.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.rendering.tree.models import NodeKind, RenderNode

TEXT_BEARING_KINDS = {
    NodeKind.TEXT,
    NodeKind.PARAGRAPH,
    NodeKind.BULLET,
    NodeKind.LINK,
    NodeKind.TIME,
}

REGION_REQUIRED_KINDS = {NodeKind.SECTION, NodeKind.BLOCK}

SPAN_CONTAINER_KINDS = {NodeKind.PAGE, NodeKind.GRID, NodeKind.ROW}


class TextSpan(BaseModel):
    """A single extracted text span, in tree (render) order."""

    model_config = ConfigDict(extra="forbid")

    node_id: str
    content_ref: str | None = None
    kind: NodeKind
    text: str


class TreeValidationResult(BaseModel):
    """Outcome of a full-tree validation."""

    model_config = ConfigDict(extra="forbid")

    valid: bool
    errors: list[str] = Field(default_factory=list)
    node_count: int = 0
    text: list[TextSpan] = Field(default_factory=list)


class TreeValidationError(ValueError):
    """Raised by :meth:`TreeValidator.assert_valid` on a failed tree."""


class TreeValidator:
    """Validates global invariants across a render tree."""

    def __init__(self, columns: int = 12) -> None:
        if columns < 1:
            raise ValueError("columns must be >= 1")
        self._columns = columns

    # ── Public API ────────────────────────────────────────────────────────────

    def validate(self, root: RenderNode) -> TreeValidationResult:
        """Validate ``root`` and return the outcome with text extraction."""
        errors: list[str] = []
        text: list[TextSpan] = []
        seen_ids: set[str] = set()
        region_ids = self._collect_region_ids(root)
        page_region_ids: set[str] = set()

        if root.kind is not NodeKind.DOCUMENT:
            errors.append(f"root must be a document node, got '{root.kind.value}'")

        node_count = self._walk(
            root,
            current_region=None,
            seen_ids=seen_ids,
            region_ids=region_ids,
            page_region_ids=page_region_ids,
            errors=errors,
            text=text,
        )
        return TreeValidationResult(
            valid=not errors,
            errors=errors,
            node_count=node_count,
            text=text,
        )

    def is_valid(self, root: RenderNode) -> bool:
        """Return True when ``root`` satisfies every invariant."""
        return self.validate(root).valid

    def assert_valid(self, root: RenderNode) -> None:
        """Raise :class:`TreeValidationError` when ``root`` is invalid."""
        result = self.validate(root)
        if not result.valid:
            raise TreeValidationError("; ".join(result.errors))

    def extract_text(self, root: RenderNode) -> list[TextSpan]:
        """Return text spans in tree (render) order."""
        return self.validate(root).text

    # ── Internals ─────────────────────────────────────────────────────────────

    def _collect_region_ids(self, root: RenderNode) -> set[str]:
        region_ids: set[str] = set()

        def visit(node: RenderNode) -> None:
            if node.kind is NodeKind.REGION and node.region:
                region_ids.add(node.region)
            for child in node.children:
                visit(child)

        visit(root)
        return region_ids

    def _walk(
        self,
        node: RenderNode,
        current_region: str | None,
        seen_ids: set[str],
        region_ids: set[str],
        page_region_ids: set[str],
        errors: list[str],
        text: list[TextSpan],
    ) -> int:
        count = 1

        if node.id in seen_ids:
            errors.append(f"duplicate node id '{node.id}'")
        else:
            seen_ids.add(node.id)

        if node.kind is NodeKind.PAGE:
            page_region_ids.clear()

        if node.kind is NodeKind.REGION:
            self._validate_region(node, page_region_ids, errors)
            next_region = node.region
        else:
            next_region = current_region
            self._validate_region_reference(node, current_region, region_ids, errors)

        if node.kind is NodeKind.SECTION:
            self._validate_section(node, errors)

        if node.kind in TEXT_BEARING_KINDS:
            self._validate_text_leaf(node, errors)
            if node.data is not None:
                text.append(
                    TextSpan(
                        node_id=node.id,
                        content_ref=node.content_ref,
                        kind=node.kind,
                        text=node.data.text,
                    )
                )

        if node.kind in SPAN_CONTAINER_KINDS:
            self._validate_span_budget(node, errors)

        for child in node.children:
            count += self._walk(
                child,
                next_region,
                seen_ids,
                region_ids,
                page_region_ids,
                errors,
                text,
            )
        return count

    def _validate_region(
        self,
        node: RenderNode,
        page_region_ids: set[str],
        errors: list[str],
    ) -> None:
        if not node.region:
            errors.append(f"region node '{node.id}' must declare a region id")
        elif node.region in page_region_ids:
            errors.append(f"region id '{node.region}' is duplicated within a page")
        else:
            page_region_ids.add(node.region)

    def _validate_region_reference(
        self,
        node: RenderNode,
        current_region: str | None,
        region_ids: set[str],
        errors: list[str],
    ) -> None:
        if node.region is None:
            if current_region is not None and node.kind in REGION_REQUIRED_KINDS:
                errors.append(
                    f"node '{node.id}' under region '{current_region}' must declare its region"
                )
            return
        if node.region not in region_ids:
            errors.append(f"node '{node.id}' references unknown region '{node.region}'")
        elif current_region is not None and node.region != current_region:
            errors.append(
                f"node '{node.id}' declares region '{node.region}' "
                f"but sits under region '{current_region}'"
            )

    def _validate_section(self, node: RenderNode, errors: list[str]) -> None:
        if not node.content_ref:
            errors.append(f"section node '{node.id}' must declare a content reference")

    def _validate_text_leaf(self, node: RenderNode, errors: list[str]) -> None:
        if not node.content_ref:
            errors.append(f"text node '{node.id}' must declare a content reference")
        if node.data is not None and not node.data.text.strip():
            errors.append(f"text node '{node.id}' must not be empty")

    def _validate_span_budget(self, node: RenderNode, errors: list[str]) -> None:
        span_children = [
            child
            for child in node.children
            if child.kind is NodeKind.REGION or child.kind is NodeKind.BLOCK
        ]
        # Full-width children (span == budget) occupy their own row; only the
        # remaining children must fit the column budget.
        partial_total = sum(
            child.span for child in span_children if child.span < self._columns
        )
        for child in span_children:
            if child.span > self._columns:
                errors.append(
                    f"node '{child.id}' span {child.span} exceeds column budget {self._columns}"
                )
        if partial_total > self._columns:
            errors.append(
                f"node '{node.id}' children span sum {partial_total} exceeds column budget {self._columns}"
            )
