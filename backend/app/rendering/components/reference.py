"""Reference section components proving the ComponentRegistry contract.

These are intentionally lightweight placeholders. They demonstrate
registration, resolution, and node building end-to-end and emit deterministic
per-item content from CVM-shaped input so the generated RenderTree carries the
substantive resume content; real detailed section rendering ships later.
"""

from __future__ import annotations

from collections.abc import Mapping

from app.rendering.common.section_types import SectionType
from app.rendering.components.base import (
    ComponentMetadata,
    ComponentValidationResult,
    SectionComponent,
    SectionContent,
)
from app.rendering.tree import NodeKind, RenderNode, TextData


def _get(value: object, key: str) -> object:
    if isinstance(value, Mapping):
        return value.get(key)
    return getattr(value, key, None)


def _format_entry(value: object) -> str | None:
    """Format a CVM entry into a substantive one-line string (placeholder)."""
    if isinstance(value, str):
        return value.strip() or None

    title = _get(value, "title")
    company = _get(value, "company")
    institution = _get(value, "institution")
    degree = _get(value, "degree")
    field = _get(value, "field")
    category = _get(value, "category")
    skills = _get(value, "skills")
    name = _get(value, "name")
    issuer = _get(value, "issuer")
    full_name = _get(value, "full_name")
    prof_title = _get(value, "professional_title")
    start = _get(value, "start_date")
    end = _get(value, "end_date")
    current = _get(value, "current")

    parts: list[str] = []
    if title and company:
        parts.append(f"{title} — {company}")
    elif title:
        parts.append(str(title))
    elif degree:
        base = str(degree)
        if field:
            base += f" in {field}"
        if institution:
            base += f" — {institution}"
        parts.append(base)
    elif category:
        base = str(category)
        if skills:
            base += f": {', '.join(str(skill) for skill in skills)}"
        parts.append(base)
    elif name:
        base = str(name)
        if issuer:
            base += f" — {issuer}"
        parts.append(base)
    elif full_name:
        base = str(full_name)
        if prof_title:
            base += f" — {prof_title}"
        parts.append(base)

    if not parts:
        return None

    result = " | ".join(parts)
    if start or end or current:
        period = f"{start or ''} – Present" if (current or not end) else f"{start or ''} – {end}"
        result += f" ({period.strip()})"
    return result or None


def _coerce_items(value: object) -> list[str]:
    """Coerce a CVM section value into one display string per item."""
    if isinstance(value, (tuple, list)):
        items: list[str] = []
        for item in value:
            text = _format_entry(item)
            if text:
                items.append(text)
        return items
    text = _format_entry(value)
    return [text] if text else []


def _extract_items(content: SectionContent, keys: tuple[str, ...]) -> list[str]:
    for key in keys:
        items = _coerce_items(content.get(key))
        if items:
            return items
    return []


def _placeholder_section(
    section_type: str,
    items: list[str],
    *,
    region: str | None,
    order: int,
) -> RenderNode:
    node_id = f"section-{section_type}"
    blocks = tuple(
        RenderNode(
            id=f"{node_id}-block-{index}",
            kind=NodeKind.BLOCK,
            region=region,
            children=(
                RenderNode(
                    id=f"{node_id}-text-{index}",
                    kind=NodeKind.TEXT,
                    content_ref=section_type,
                    region=region,
                    data=TextData(type="text", text=item),
                ),
            ),
        )
        for index, item in enumerate(items)
    )
    return RenderNode(
        id=node_id,
        kind=NodeKind.SECTION,
        content_ref=section_type,
        region=region,
        order=order,
        children=blocks,
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
            _extract_items(content, self._text_keys),
            region=region,
            order=order,
        )


class ProfileComponent(_PlaceholderComponent):
    _section_type = SectionType.PROFILE.value
    _name = "Profile"
    _description = "Candidate identity section."
    _text_keys = ("profile", "full_name", "name")
    _regions = ("main", "header")


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


class CertificationsComponent(_PlaceholderComponent):
    _section_type = SectionType.CERTIFICATIONS.value
    _name = "Certifications"
    _description = "Certifications section."
    _text_keys = ("certifications", "name", "issuer")
    _regions = ("main", "sidebar")
