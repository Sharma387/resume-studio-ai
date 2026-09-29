"""Reference section components proving the ComponentRegistry contract.

These are lightweight but structured: each renders its section's CVM content
into distinct Render Tree nodes (title/company/location/dates/description,
degree/institution/gpa, grouped skills, certification/issuer/date) so the HTML
is genuinely readable. Real detailed section rendering can still expand later.
"""

from __future__ import annotations

from collections.abc import Mapping

from app.rendering.cert_grouping import CertificationSlot, group_certs
from app.rendering.common.section_types import SectionType
from app.rendering.components.base import (
    ComponentMetadata,
    ComponentValidationResult,
    SectionComponent,
    SectionContent,
)
from app.rendering.tree import BulletData, InlineRun, LinkData, NodeKind, ParagraphData, RenderNode, TextData, TimeData


def _get(value: object, key: str) -> object:
    if isinstance(value, Mapping):
        return value.get(key)
    return getattr(value, key, None)


def _text_str(value: object) -> str:
    return str(value).strip() if value is not None else ""


def _node(
    node_id: str,
    kind: NodeKind,
    region: str | None,
    content_ref: str,
    *,
    classes: tuple[str, ...] = (),
    children: tuple[RenderNode, ...] = (),
    data=None,
    order: int = 0,
) -> RenderNode:
    return RenderNode(
        id=node_id,
        kind=kind,
        region=region,
        content_ref=content_ref,
        classes=classes,
        children=children,
        data=data,
        order=order,
    )


def _text_unit(
    node_id: str, region: str | None, content_ref: str, text: str, classes: tuple[str, ...] = ()
) -> RenderNode:
    return _node(node_id, NodeKind.TEXT, region, content_ref, classes=classes, data=TextData(type="text", text=text))


def _paragraph(node_id: str, region: str | None, content_ref: str, text: str) -> RenderNode:
    return _node(node_id, NodeKind.PARAGRAPH, region, content_ref, data=ParagraphData(type="paragraph", text=text))


def _time_unit(
    node_id: str,
    region: str | None,
    content_ref: str,
    text: str,
    start: str | None,
    end: str | None,
    current: bool,
) -> RenderNode:
    return _node(
        node_id,
        NodeKind.TIME,
        region,
        content_ref,
        data=TimeData(type="time", text=text, start=start, end=end, current=current),
    )


def _bullet(node_id: str, region: str | None, content_ref: str, text: str) -> RenderNode:
    return _node(node_id, NodeKind.BULLET, region, content_ref, data=BulletData(type="bullet", text=text))


def _link(node_id: str, region: str | None, content_ref: str, url: str) -> RenderNode:
    return _node(node_id, NodeKind.LINK, region, content_ref, data=LinkData(type="link", text=url, url=url))


def _list(node_id: str, region: str | None, content_ref: str, bullets: tuple[RenderNode, ...]) -> RenderNode:
    blocks = tuple(
        _node(f"{node_id}-b{index}", NodeKind.BLOCK, region, content_ref, children=(bullet,))
        for index, bullet in enumerate(bullets)
    )
    return _node(node_id, NodeKind.LIST, region, content_ref, children=blocks)


def _section(node_id: str, region: str | None, order: int, children: tuple[RenderNode, ...]) -> RenderNode:
    return _node(
        node_id,
        NodeKind.SECTION,
        region,
        node_id.removeprefix("section-"),
        children=children,
        data=None,
        order=order,
    )


def _period(start: object, end: object, current: object) -> str:
    if not start and not end and not current:
        return ""
    if current or not end:
        return f"{_text_str(start)} – Present".strip()
    return f"{_text_str(start)} – {_text_str(end)}".strip(" –")


def _entries(content: SectionContent, key: str) -> list[object]:
    value = content.get(key)
    if isinstance(value, (tuple, list)):
        return list(value)
    return [value] if value is not None else []


class _PlaceholderComponent(SectionComponent):
    """Base for the reference components: identity + validation only."""

    _section_type: str = ""
    _name: str = ""
    _description: str = ""
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


class ProfileComponent(_PlaceholderComponent):
    _section_type = SectionType.PROFILE.value
    _name = "Profile"
    _description = "Candidate identity section."
    _regions = ("main", "header")

    def build_render_nodes(self, content: SectionContent, *, region: str | None = None, order: int = 0) -> RenderNode:
        ref = self._section_type
        profile = content.get("profile")
        children: list[RenderNode] = []
        name = _text_str(_get(profile, "full_name"))
        if name:
            children.append(_text_unit(f"{ref}-name", region, ref, name, classes=("resume-name",)))
        title = _text_str(_get(profile, "professional_title"))
        if title:
            children.append(_text_unit(f"{ref}-title", region, ref, title, classes=("resume-muted",)))
        contact = " · ".join(
            part
            for part in (
                _text_str(_get(profile, "location")),
                _text_str(_get(profile, "email")),
                _text_str(_get(profile, "phone")),
            )
            if part
        )
        if contact:
            children.append(_text_unit(f"{ref}-contact", region, ref, contact, classes=("resume-muted",)))
        for key in ("linkedin", "github", "website"):
            url = _text_str(_get(profile, key))
            if url:
                children.append(_link(f"{ref}-{key}", region, ref, url))
        block = _node(f"{ref}-block", NodeKind.BLOCK, region, ref, children=tuple(children)) if children else None
        return _section(f"section-{ref}", region, order, (block,) if block else ())


class SummaryComponent(_PlaceholderComponent):
    _section_type = SectionType.SUMMARY.value
    _name = "Summary"
    _description = "Professional summary section."
    _regions = ("main",)

    def build_render_nodes(self, content: SectionContent, *, region: str | None = None, order: int = 0) -> RenderNode:
        ref = self._section_type
        text = _text_str(content.get("summary")) or _text_str(content.get("text"))
        paragraph = _paragraph(f"{ref}-text", region, ref, text) if text else None
        block = _node(f"{ref}-block", NodeKind.BLOCK, region, ref, children=(paragraph,)) if paragraph else None
        return _section(f"section-{ref}", region, order, (block,) if block else ())


class ExperienceComponent(_PlaceholderComponent):
    _section_type = SectionType.EXPERIENCE.value
    _name = "Experience"
    _description = "Work experience section."
    _regions = ("main", "sidebar")

    def build_render_nodes(self, content: SectionContent, *, region: str | None = None, order: int = 0) -> RenderNode:
        ref = self._section_type
        entries = _entries(content, ref) or [content]
        children: list[RenderNode] = []
        for index, entry in enumerate(entries):
            children.extend(self._entry_nodes(index, entry, region, ref))
        return _section(f"section-{ref}", region, order, tuple(children))

    def _entry_nodes(self, index: int, entry: object, region: str | None, ref: str) -> list[RenderNode]:
        prefix = f"{ref}-{index}"
        children: list[RenderNode] = []
        title = _text_str(_get(entry, "title"))
        if title:
            children.append(_text_unit(f"{prefix}-title", region, ref, title, classes=("resume-strong",)))
        meta = " · ".join(
            part for part in (_text_str(_get(entry, "company")), _text_str(_get(entry, "location"))) if part
        )
        if meta:
            children.append(_text_unit(f"{prefix}-meta", region, ref, meta, classes=("resume-muted",)))
        period = _period(_get(entry, "start_date"), _get(entry, "end_date"), _get(entry, "current"))
        if period:
            children.append(
                _time_unit(
                    f"{prefix}-time",
                    region,
                    ref,
                    period,
                    _text_str(_get(entry, "start_date")) or None,
                    _text_str(_get(entry, "end_date")) or None,
                    bool(_get(entry, "current")),
                )
            )
        block = _node(f"{prefix}-block", NodeKind.BLOCK, region, ref, children=tuple(children))
        nodes: list[RenderNode] = [block]
        description = _get(entry, "description")
        bullets = tuple(
            _bullet(f"{prefix}-d{i}", region, ref, _text_str(item))
            for i, item in enumerate(description or [])
            if _text_str(item)
        )
        if bullets:
            nodes.append(_list(f"{prefix}-desc", region, ref, bullets))
        return nodes


class EducationComponent(_PlaceholderComponent):
    _section_type = SectionType.EDUCATION.value
    _name = "Education"
    _description = "Education section."
    _regions = ("main", "sidebar")

    def build_render_nodes(self, content: SectionContent, *, region: str | None = None, order: int = 0) -> RenderNode:
        ref = self._section_type
        entries = _entries(content, ref) or [content]
        blocks = tuple(self._entry_block(index, entry, region, ref) for index, entry in enumerate(entries))
        return _section(f"section-{ref}", region, order, blocks)

    def _entry_block(self, index: int, entry: object, region: str | None, ref: str) -> RenderNode:
        prefix = f"{ref}-{index}"
        children: list[RenderNode] = []
        degree = _text_str(_get(entry, "degree"))
        field = _text_str(_get(entry, "field"))
        heading = degree + (f" in {field}" if field else "")
        if heading:
            children.append(_text_unit(f"{prefix}-degree", region, ref, heading, classes=("resume-strong",)))
        institution = _text_str(_get(entry, "institution"))
        if institution:
            children.append(_text_unit(f"{prefix}-institution", region, ref, institution, classes=("resume-muted",)))
        period = _period(_get(entry, "start_date"), _get(entry, "end_date"), _get(entry, "current"))
        if period:
            children.append(
                _time_unit(
                    f"{prefix}-time",
                    region,
                    ref,
                    period,
                    _text_str(_get(entry, "start_date")) or None,
                    _text_str(_get(entry, "end_date")) or None,
                    False,
                )
            )
        gpa = _get(entry, "gpa")
        if gpa is not None:
            children.append(_text_unit(f"{prefix}-gpa", region, ref, f"GPA: {gpa}", classes=("resume-muted",)))
        return _node(f"{prefix}-block", NodeKind.BLOCK, region, ref, children=tuple(children))


class SkillsComponent(_PlaceholderComponent):
    _section_type = SectionType.SKILLS.value
    _name = "Skills"
    _description = "Skills section."
    _regions = ("main", "sidebar")

    def build_render_nodes(self, content: SectionContent, *, region: str | None = None, order: int = 0) -> RenderNode:
        ref = self._section_type
        groups = _entries(content, ref) or [content]
        bullets: list[RenderNode] = []
        for index, group in enumerate(groups):
            bullets.extend(self._group_bullets(index, group, region, ref))
        if not bullets:
            return _section(f"section-{ref}", region, order, ())
        return _section(f"section-{ref}", region, order, (_list(f"{ref}-list", region, ref, tuple(bullets)),))

    def _group_bullets(self, index: int, group: object, region: str | None, ref: str) -> list[RenderNode]:
        prefix = f"{ref}-{index}"
        category = _text_str(_get(group, "category"))
        skills = _get(group, "skills")
        if skills:
            skills = tuple(item for item in skills if _text_str(item))
        if not category and not skills:
            return []
        if category and skills:
            join = ", ".join(skills)
            data = BulletData(
                type="bullet",
                text=f"{category}: {join}",
                runs=(InlineRun(text=f"{category}:", bold=True), InlineRun(text=f" {join}")),
            )
            return [_node(f"{prefix}-item", NodeKind.BULLET, region, ref, data=data)]
        return [_bullet(f"{prefix}-s{i}", region, ref, skill) for i, skill in enumerate(skills)]


class CertificationsComponent(_PlaceholderComponent):
    _section_type = SectionType.CERTIFICATIONS.value
    _name = "Certifications"
    _description = "Certifications section."
    _regions = ("main", "sidebar")

    def build_render_nodes(self, content: SectionContent, *, region: str | None = None, order: int = 0) -> RenderNode:
        ref = self._section_type
        certs = _entries(content, ref) or [content]
        children: list[RenderNode] = []
        bullets: list[RenderNode] = []
        for index, slot in enumerate(group_certs(certs)):
            if slot.is_card:
                if bullets:
                    children.append(_list(f"{ref}-grouped-{len(children)}", region, ref, tuple(bullets)))
                    bullets = []
                children.append(self._cert_block(index, slot.card, region, ref))
            else:
                bullets.append(self._group_bullet(index, slot, region, ref))
        if bullets:
            children.append(_list(f"{ref}-grouped-{len(children)}", region, ref, tuple(bullets)))
        return _section(f"section-{ref}", region, order, tuple(children))

    def _group_bullet(self, index: int, slot: CertificationSlot, region: str | None, ref: str) -> RenderNode:
        """One heading and its credentials as a single logical bullet."""
        prefix = f"{ref}-{index}"
        if not slot.values:
            return _bullet(f"{prefix}-heading", region, ref, slot.category)
        join = " | ".join(slot.values)
        data = BulletData(
            type="bullet",
            text=f"{slot.category}: {join}",
            runs=(InlineRun(text=f"{slot.category}:", bold=True), InlineRun(text=f" {join}")),
        )
        return _node(f"{prefix}-grouped", NodeKind.BULLET, region, ref, data=data)

    def _cert_block(self, index: int, cert: object, region: str | None, ref: str) -> RenderNode:
        prefix = f"{ref}-{index}"
        children: list[RenderNode] = []
        name = _text_str(_get(cert, "name"))
        if name:
            children.append(_text_unit(f"{prefix}-name", region, ref, name, classes=("resume-strong",)))
        meta = " · ".join(part for part in (_text_str(_get(cert, "issuer")), _text_str(_get(cert, "date"))) if part)
        if meta:
            children.append(_text_unit(f"{prefix}-meta", region, ref, meta, classes=("resume-muted",)))
        return _node(f"{prefix}-block", NodeKind.BLOCK, region, ref, children=tuple(children))


class ProjectsComponent(_PlaceholderComponent):
    _section_type = SectionType.PROJECTS.value
    _name = "Projects"
    _description = "Projects section."
    _regions = ("main", "sidebar")

    def build_render_nodes(self, content: SectionContent, *, region: str | None = None, order: int = 0) -> RenderNode:
        ref = self._section_type
        projects = _entries(content, ref) or [content]
        children: list[RenderNode] = []
        for index, project in enumerate(projects):
            children.extend(self._project_nodes(index, project, region, ref))
        return _section(f"section-{ref}", region, order, tuple(children))

    def _project_nodes(self, index: int, project: object, region: str | None, ref: str) -> list[RenderNode]:
        prefix = f"{ref}-{index}"
        block_children: list[RenderNode] = []
        name = _text_str(_get(project, "name"))
        if name:
            block_children.append(_text_unit(f"{prefix}-name", region, ref, name, classes=("resume-strong",)))
        url = _text_str(_get(project, "url"))
        if url:
            block_children.append(_link(f"{prefix}-url", region, ref, url))
        block = _node(f"{prefix}-block", NodeKind.BLOCK, region, ref, children=tuple(block_children))
        nodes: list[RenderNode] = [block]

        description = _text_str(_get(project, "description"))
        if description:
            lines = [line.strip() for line in description.split("\n") if line.strip()]
            if len(lines) > 1:
                bullets = tuple(_bullet(f"{prefix}-d{i}", region, ref, line) for i, line in enumerate(lines))
                nodes.append(_list(f"{prefix}-desc", region, ref, bullets))
            else:
                paragraph = _paragraph(f"{prefix}-desc", region, ref, lines[0])
                nodes.append(_node(f"{prefix}-desc-block", NodeKind.BLOCK, region, ref, children=(paragraph,)))

        technologies = tuple(_text_str(tech) for tech in (_get(project, "technologies") or []) if _text_str(tech))
        if technologies:
            tech_line = "Technologies: " + " · ".join(technologies)
            nodes.append(
                _node(
                    f"{prefix}-tech-block",
                    NodeKind.BLOCK,
                    region,
                    ref,
                    children=(_text_unit(f"{prefix}-tech", region, ref, tech_line, classes=("resume-muted",)),),
                )
            )
        return nodes


class AwardsComponent(_PlaceholderComponent):
    _section_type = SectionType.AWARDS.value
    _name = "Awards"
    _description = "Awards section."
    _regions = ("main", "sidebar")

    def build_render_nodes(self, content: SectionContent, *, region: str | None = None, order: int = 0) -> RenderNode:
        ref = self._section_type
        awards = _entries(content, ref) or [content]
        blocks = tuple(self._award_block(index, award, region, ref) for index, award in enumerate(awards))
        return _section(f"section-{ref}", region, order, blocks)

    def _award_block(self, index: int, award: object, region: str | None, ref: str) -> RenderNode:
        prefix = f"{ref}-{index}"
        children: list[RenderNode] = []
        title = _text_str(_get(award, "title"))
        if title:
            children.append(_text_unit(f"{prefix}-title", region, ref, title, classes=("resume-strong",)))
        issuer = _text_str(_get(award, "issuer"))
        if issuer:
            children.append(_text_unit(f"{prefix}-issuer", region, ref, issuer, classes=("resume-muted",)))
        date = _text_str(_get(award, "date"))
        if date:
            children.append(_time_unit(f"{prefix}-date", region, ref, date, date, None, False))
        return _node(f"{prefix}-block", NodeKind.BLOCK, region, ref, children=tuple(children))


class LanguagesComponent(_PlaceholderComponent):
    _section_type = SectionType.LANGUAGES.value
    _name = "Languages"
    _description = "Languages section."
    _regions = ("main", "sidebar")

    def build_render_nodes(self, content: SectionContent, *, region: str | None = None, order: int = 0) -> RenderNode:
        ref = self._section_type
        languages = _entries(content, ref) or [content]
        bullets: list[RenderNode] = []
        for index, language in enumerate(languages):
            name = _text_str(_get(language, "name"))
            if not name:
                continue
            proficiency = _text_str(_get(language, "proficiency"))
            bullets.append(_bullet(f"{ref}-{index}", region, ref, f"{name} — {proficiency}" if proficiency else name))
        section = _section(f"section-{ref}", region, order, ())
        if bullets:
            return section.model_copy(update={"children": (_list(f"{ref}-list", region, ref, tuple(bullets)),)})
        return section
