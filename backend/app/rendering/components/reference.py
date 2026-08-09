"""Reference section components proving the ComponentRegistry contract.

These are intentionally lightweight placeholders. They demonstrate
registration, resolution, and node building end-to-end; real section logic
ships with the TreeBuilder and Content View Model units.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from app.rendering.common.section_types import SectionType
from app.rendering.components.base import (
    ComponentMetadata,
    ComponentValidationResult,
    SectionComponent,
    SectionContent,
)
from app.rendering.tree import NodeKind, RenderNode, TextData

_TEXT_FIELDS = (
    "title", "company", "name", "category", "institution", "degree",
    "full_name", "summary", "text",
)


def _coerce_text(value: Any) -> str | None:
    """Coerce a CVM section value into a short display string (placeholder)."""
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, (tuple, list)):
        for item in value:
            text = _coerce_text(item)
            if text:
                return text
        return None
    if isinstance(value, Mapping):
        for key in _TEXT_FIELDS:
            if key in value:
                text = _coerce_text(value[key])
                if text:
                    return text
        return None
    if isinstance(value, BaseModel):
        for field in _TEXT_FIELDS:
            if hasattr(value, field):
                text = _coerce_text(getattr(value, field))
                if text:
                    return text
        return None
    return None


def _extract_text(content: SectionContent, keys: tuple[str, ...]) -> str:
    for key in keys:
        text = _coerce_text(content.get(key))
        if text:
            return text
    return ""


def _placeholder_section(
    section_type: str,
    text: str,
    *,
    region: str | None,
    order: int,
) -> RenderNode:
    node_id = f"section-{section_type}"
    return RenderNode(
        id=node_id,
        kind=NodeKind.SECTION,
        content_ref=section_type,
        region=region,
        order=order,
        children=(
            RenderNode(
                id=f"{node_id}-block",
                kind=NodeKind.BLOCK,
                region=region,
                children=(
                    RenderNode(
                        id=f"{node_id}-text",
                        kind=NodeKind.TEXT,
                        content_ref=section_type,
                        region=region,
                        data=TextData(type="text", text=text),
                    ),
                ),
            ),
        ),
    )


class _PlaceholderComponent(SectionComponent):
    """Shared placeholder implementation for the reference components."""

    _section_type: str = ""
    _name: str = ""
    _description: str = ""
    _text_keys: tuple[str, ...] = ()
    _regions: tuple[str, ...] = ("main",)

    def metadata(self) -> ComponentMetadata:
        return ComponentMetadata(
            section_type=self._section_type,
            name=self._name,
            description=self._description,
            ats_safe=True,
            supported_regions=self._regions,
        )

    def validate_input(self, content: SectionContent) -> ComponentValidationResult:
        return ComponentValidationResult(valid=True)

    def build_render_nodes(
        self,
        content: SectionContent,
        *,
        region: str | None = None,
        order: int = 0,
    ) -> RenderNode:
        return _placeholder_section(
            self._section_type,
            _extract_text(content, self._text_keys),
            region=region,
            order=order,
        )


class SummaryComponent(_PlaceholderComponent):
    _section_type = SectionType.SUMMARY.value
    _name = "Summary"
    _description = "Professional summary section."
    _text_keys = ("summary", "text")
    _regions = ("main",)


class ExperienceComponent(_PlaceholderComponent):
    _section_type = SectionType.EXPERIENCE.value
    _name = "Experience"
    _description = "Work experience section."
    _text_keys = ("experience", "title", "company", "text")
    _regions = ("main", "sidebar")


class EducationComponent(_PlaceholderComponent):
    _section_type = SectionType.EDUCATION.value
    _name = "Education"
    _description = "Education section."
    _text_keys = ("education", "degree", "institution", "text")
    _regions = ("main", "sidebar")


class SkillsComponent(_PlaceholderComponent):
    _section_type = SectionType.SKILLS.value
    _name = "Skills"
    _description = "Skills section."
    _text_keys = ("skills", "category", "skills", "text")
    _regions = ("main", "sidebar")
