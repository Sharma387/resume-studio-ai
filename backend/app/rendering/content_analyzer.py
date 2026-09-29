"""ContentAnalyzer — deterministic, render-independent per-section content size.

This module performs ANALYSIS ONLY. It measures the semantic content of a
:class:`ContentView` (which section has how many logical items and how much
text); it must never choose a layout, change spacing, render, or persist.

It is intentionally ignorant of templates, CSS/HTML/PDF, column geometry,
themes, density, and page dimensions. It depends only on the content models
and the shared section vocabulary so the future LayoutBalancer (P3.6) can
compare sections relatively without re-deriving these counts.

Measurement rules
-----------------
* ``item_count`` — one per *logical* semantic item: one experience entry, one
  education entry, one project, one certification record (grouped or
  individual), one skill GROUP, one award, one language, and one for the
  profile/summary blocks. Inline runs and grouped ``skills``/``values`` are
  NOT separate items.
* ``word_count``/``char_count`` — counted once over each item's single logical
  text string (all of its fields joined). A grouped skill
  (``"Project Management Lifecycle: SAFe, Agile, Waterfall"``) and a grouped
  certification (``"Category: value | value"``) are each counted as ONE text
  string, so the category is never duplicated and renderer runs are never
  re-counted.
* ``estimated_units`` — ``word_count``: deterministic, monotonic with content,
  cheap, and explainable. It approximates relative section size for P3.6 but
  deliberately does NOT predict lines or page counts.

``ContentView.content_hash`` is a stable identity hash and is deliberately not
re-interpreted as a size metric.
"""

from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, Field

from app.rendering.cert_grouping import group_certs
from app.rendering.common.section_types import SectionType
from app.rendering.content.models import ContentView


class SectionMetrics(BaseModel):
    """Content metrics for one present section of a ContentView."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    section_id: str
    item_count: int = Field(default=0, ge=0)
    word_count: int = Field(default=0, ge=0)
    char_count: int = Field(default=0, ge=0)
    estimated_units: int = Field(default=0, ge=0)


class ContentAnalysis(BaseModel):
    """Aggregate content-size analysis for a ContentView (analysis only)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sections: dict[str, SectionMetrics]
    total_word_count: int = 0
    total_char_count: int = 0


# ── Measurement helpers ───────────────────────────────────────────────────────


def _counted(text: str) -> tuple[int, int]:
    """Return (word_count, char_count) for one logical text string."""
    token_count = len(text.split()) if text.strip() else 0
    return token_count, len(text)


def _measure_profile(content: object) -> tuple[int, int, int]:
    profile = content
    fields = (
        profile.full_name,
        profile.professional_title,
        profile.location,
        profile.email,
        profile.phone,
        profile.linkedin,
        profile.github,
        profile.website,
    )
    words, chars = _counted(" ".join(value for value in fields if value))
    return 1, words, chars


def _measure_summary(content: object) -> tuple[int, int, int]:
    words, chars = _counted(str(content))
    return 1, words, chars


def _measure_experience(content: object) -> tuple[int, int, int]:
    items = content
    words = 0
    chars = 0
    for entry in items:
        fields = (
            entry.company,
            entry.title,
            entry.location,
            entry.start_date,
            entry.end_date,
            *entry.description,
        )
        w, c = _counted(" ".join(value for value in fields if value))
        words += w
        chars += c
    return len(items), words, chars


def _measure_education(content: object) -> tuple[int, int, int]:
    items = content
    words = 0
    chars = 0
    for entry in items:
        gpa = f"{entry.gpa:g}" if entry.gpa is not None else None
        fields = (
            entry.institution,
            entry.degree,
            entry.field,
            entry.start_date,
            entry.end_date,
            gpa,
            *entry.achievements,
        )
        w, c = _counted(" ".join(value for value in fields if value))
        words += w
        chars += c
    return len(items), words, chars


def _measure_skills(content: object) -> tuple[int, int, int]:
    groups = content
    words = 0
    chars = 0
    for group in groups:
        logical = f"{group.category}: {', '.join(group.skills)}"
        w, c = _counted(logical)
        words += w
        chars += c
    return len(groups), words, chars


def _measure_certifications(content: object) -> tuple[int, int, int]:
    records = content
    words = 0
    chars = 0
    # Measure the grouped slots, not the raw records, so the counts match the
    # text the renderer actually draws. A resume whose credentials arrive as one
    # record per item (the heading repeated on each) is measured once per
    # heading, not once per item.
    slots = group_certs(records)
    for slot in slots:
        w, c = _counted(slot.logical_text())
        words += w
        chars += c
    return len(slots), words, chars


def _measure_projects(content: object) -> tuple[int, int, int]:
    items = content
    words = 0
    chars = 0
    for project in items:
        fields = (
            project.name,
            project.description,
            project.url,
            *project.technologies,
        )
        w, c = _counted(" ".join(value for value in fields if value))
        words += w
        chars += c
    return len(items), words, chars


def _measure_awards(content: object) -> tuple[int, int, int]:
    items = content
    words = 0
    chars = 0
    for award in items:
        fields = (award.title, award.issuer, award.date)
        w, c = _counted(" ".join(value for value in fields if value))
        words += w
        chars += c
    return len(items), words, chars


def _measure_languages(content: object) -> tuple[int, int, int]:
    items = content
    words = 0
    chars = 0
    for language in items:
        fields = (language.name, language.proficiency)
        w, c = _counted(" ".join(value for value in fields if value))
        words += w
        chars += c
    return len(items), words, chars


#: Sections measured by the analyzer (canonical vocabulary ids → extractor).
_SECTION_EXTRACTORS: dict[str, Callable[[object], tuple[int, int, int]]] = {
    SectionType.PROFILE.value: _measure_profile,
    SectionType.SUMMARY.value: _measure_summary,
    SectionType.EXPERIENCE.value: _measure_experience,
    SectionType.EDUCATION.value: _measure_education,
    SectionType.SKILLS.value: _measure_skills,
    SectionType.CERTIFICATIONS.value: _measure_certifications,
    SectionType.PROJECTS.value: _measure_projects,
    SectionType.AWARDS.value: _measure_awards,
    SectionType.LANGUAGES.value: _measure_languages,
}

#: The canonical section ids measured by this analyzer (deterministic subset).
MEASURED_SECTIONS: frozenset[str] = frozenset(_SECTION_EXTRACTORS)


def analyze_content(cvm: ContentView) -> ContentAnalysis:
    """Analyze ``cvm``, returning metrics only for sections actually present.

    ``item_count`` counts logical semantic items (a grouped skill or grouped
    certification is ONE item). ``estimated_units`` equals ``word_count``.
    """
    sections: dict[str, SectionMetrics] = {}
    for section in cvm.present_sections():
        extractor = _SECTION_EXTRACTORS.get(section)
        content = cvm.section_content(section)
        if extractor is None or content is None:
            continue
        item_count, word_count, char_count = extractor(content)
        sections[section] = SectionMetrics(
            section_id=section,
            item_count=item_count,
            word_count=word_count,
            char_count=char_count,
            estimated_units=word_count,
        )
    return ContentAnalysis(
        sections=sections,
        total_word_count=sum(metrics.word_count for metrics in sections.values()),
        total_char_count=sum(metrics.char_count for metrics in sections.values()),
    )


class ContentAnalyzer:
    """Analyze a ContentView into deterministic per-section content metrics."""

    def analyze(self, cvm: ContentView) -> ContentAnalysis:
        return analyze_content(cvm)
