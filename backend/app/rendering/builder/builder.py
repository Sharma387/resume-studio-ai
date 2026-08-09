"""TreeBuilder — assembles a validated RenderTree from CVM + resolved layout.

The TreeBuilder is the L6 orchestrator. It consumes the resolved
:class:`RenderContext` (layout structure + content reference) and the
:class:`ContentView`, resolves each placed section through the
:class:`ComponentRegistry`, and assembles a ``RenderDocument`` validated by the
:class:`TreeValidator`.

It never hardcodes layout knowledge and never contains section-specific logic:
section placement comes from ``LayoutDefinition.regions`` + placement rules,
and section construction is delegated to components.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.rendering.components.registry import ComponentRegistry
from app.rendering.content.models import ContentView
from app.rendering.context.render_context import RenderContext
from app.rendering.layout.layout_definition import LayoutDefinition
from app.rendering.layout.layout_regions import RegionDefinition
from app.rendering.layout.placement_rules import PlacementRule
from app.rendering.tree import A4, LETTER, NodeKind, PageMargins, PageSize, RenderNode
from app.rendering.tree.validator import TreeValidator

_PAGE_SIZES: dict[str, PageSize] = {"A4": A4, "Letter": LETTER}

#: Ordering assigned to sections with no explicit placement rule (placed after
#: rule-ordered sections, then by content order).
_UNRULED_ORDER = 1_000_000


class TreeBuilderError(ValueError):
    """Raised when a render tree cannot be built."""


class TreeBuilder:
    """Assembles a validated render document from content and a resolved layout."""

    def __init__(
        self,
        component_registry: ComponentRegistry,
        *,
        validator: TreeValidator | None = None,
    ) -> None:
        self._components = component_registry
        self._validator = validator or TreeValidator()

    # ── Public API ────────────────────────────────────────────────────────────

    def build(self, cvm: ContentView, context: RenderContext) -> RenderNode:
        """Build and validate a render document for ``cvm`` under ``context``."""
        self._check_content_reference(cvm, context)
        layout = context.layout

        page_children = tuple(
            self._build_region(layout, cvm, region)
            for region in sorted(layout.regions, key=lambda r: (r.ordering, r.identifier))
        )
        page = RenderNode(
            id="page-1",
            kind=NodeKind.PAGE,
            page_size=self._page_size(layout),
            margins=self._margins(layout),
            children=page_children,
        )
        document = RenderNode(
            id=f"doc-{cvm.stable_id}",
            kind=NodeKind.DOCUMENT,
            children=(page,),
        )
        self._validator.assert_valid(document)
        return document

    # ── Region / section assembly ─────────────────────────────────────────────

    def _build_region(self, layout: LayoutDefinition, cvm: ContentView, region: RegionDefinition) -> RenderNode:
        children: list[RenderNode] = []
        for section_id, order in self._sections_for_region(layout, cvm, region):
            component = self._components.get(section_id)
            if component is None:
                # No component registered yet for this section type — omit it.
                continue
            content = cvm.section_content(section_id)
            children.append(
                component.build_render_nodes(
                    self._content_mapping(section_id, content),
                    region=region.identifier,
                    order=order,
                )
            )
        return RenderNode(
            id=f"region-{region.identifier}",
            kind=NodeKind.REGION,
            region=region.identifier,
            span=region.column_span,
            order=region.ordering,
            children=tuple(children),
        )

    def _sections_for_region(self, layout: LayoutDefinition, cvm: ContentView, region: RegionDefinition) -> list[tuple[str, int]]:
        content_position = {section: index for index, section in enumerate(cvm.section_order)}
        candidates: list[tuple[str, int, int]] = []
        for section_id in cvm.present_sections():
            target = self._resolve_region(layout, section_id)
            if target is None or target.identifier != region.identifier:
                continue
            rule = self._placement_rule(layout, section_id)
            rule_order = rule.ordering if rule is not None else _UNRULED_ORDER
            position = content_position.get(section_id, 10**9)
            candidates.append((section_id, rule_order, position))
        candidates.sort(key=lambda item: (item[1], item[2]))
        return [(section_id, index) for index, (section_id, _, _) in enumerate(candidates)]

    # ── Placement resolution ──────────────────────────────────────────────────

    def _placement_rule(self, layout: LayoutDefinition, section_id: str) -> PlacementRule | None:
        for rule in layout.placement_rules:
            if rule.section == section_id:
                return rule
        return None

    def _resolve_region(self, layout: LayoutDefinition, section_id: str) -> RegionDefinition | None:
        rule = self._placement_rule(layout, section_id)
        regions = {region.identifier: region for region in layout.regions}

        def accepts(region: RegionDefinition) -> bool:
            return not region.allowed_sections or section_id in region.allowed_sections

        candidates: list[str] = []
        if rule is not None:
            if rule.preferred_region:
                candidates.append(rule.preferred_region)
            if rule.fallback_region:
                candidates.append(rule.fallback_region)
            candidates.extend(rule.allowed_regions)
        candidates.extend(regions.keys())

        for region_id in candidates:
            region = regions.get(region_id)
            if region is not None and accepts(region):
                return region
        return None

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _content_mapping(section_id: str, content: object | None) -> Mapping[str, Any]:
        if isinstance(content, Mapping):
            return content
        return {section_id: content}

    @staticmethod
    def _check_content_reference(cvm: ContentView, context: RenderContext) -> None:
        reference = context.content_ref
        if reference is None:
            return
        if reference.stable_id != cvm.stable_id:
            raise TreeBuilderError(
                f"content ref stable id '{reference.stable_id}' does not match CVM '{cvm.stable_id}'"
            )
        if reference.content_hash != cvm.content_hash:
            raise TreeBuilderError("content ref hash does not match CVM content")

    @staticmethod
    def _page_size(layout: LayoutDefinition) -> PageSize:
        return _PAGE_SIZES[layout.page.page_size]

    @staticmethod
    def _margins(layout: LayoutDefinition) -> PageMargins:
        margins = layout.page.margins
        return PageMargins(
            top_mm=margins.top_mm,
            right_mm=margins.right_mm,
            bottom_mm=margins.bottom_mm,
            left_mm=margins.left_mm,
        )
