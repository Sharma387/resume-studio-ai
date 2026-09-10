"""Tests for the RenderTree → HTML renderer (Layout Engine, Phase 0).

Mandatory acceptance: the SAME CVM rendered through materially different
LayoutDefinitions must produce structurally different HTML while preserving
identical content.
"""

import ast
import importlib
import inspect
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

import pytest

from app.models.resume import Resume
from app.rendering.builder import TreeBuilder
from app.rendering.content import ContentView, Profile
from app.rendering.content.models import (
    AwardEntry,
    CertificationEntry,
    EducationEntry,
    ExperienceEntry,
    LanguageEntry,
    ProjectEntry,
    SkillGroup,
)
from app.rendering.context import RenderContext, RenderState
from app.rendering.layout.reference_layouts import (
    classic_layout,
    executive_layout,
    modern_layout,
    sidebar_layout,
)
from app.rendering.layout_html import default_component_registry, render_layout_html, render_resume_layout_html
from app.rendering.renderers.tree_html_renderer import RenderTreeHTMLRenderer
from app.rendering.theme.reference_themes import blue_theme, gold_theme
from app.rendering.tree import A4, NodeKind, PageMargins, RenderNode, TextData, TreeValidator
from app.rendering.tree.validator import TreeValidationError


def _cvm() -> ContentView:
    return ContentView(
        stable_id="resume.html",
        profile=Profile(full_name="Jane Doe", professional_title="Principal Engineer"),
        summary="Full-stack engineer with 8 years building platforms.",
        experience=(
            ExperienceEntry(company="Acme", title="Senior Engineer", start_date="2016", current=True),
            ExperienceEntry(company="Beta Inc", title="Engineer", start_date="2014", end_date="2016"),
            ExperienceEntry(company="Gamma", title="Junior Engineer", start_date="2012", end_date="2014"),
        ),
        education=(EducationEntry(institution="MIT", degree="B.Sc.", field="Computer Science"),),
        skills=(SkillGroup(category="Languages", skills=("Python", "Go")),),
        certifications=(CertificationEntry(name="AWS Certified", issuer="Amazon"),),
    )


# ── HTML structure introspection ──────────────────────────────────────────────


class _StructureParser(HTMLParser):
    _VOID = {"hr", "img", "br", "meta", "link", "input"}

    def __init__(self) -> None:
        super().__init__()
        self._stack: list[tuple[str, str | None]] = []
        self.section_regions: dict[str, str | None] = {}

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self._VOID:
            return
        attrs = dict(attrs)
        region = attrs.get("data-region") if tag == "div" else None
        self._stack.append((tag, region))
        if tag == "section":
            enclosing: str | None = None
            for _, region_id in reversed(self._stack[:-1]):
                if region_id:
                    enclosing = region_id
                    break
            self.section_regions[attrs.get("data-section")] = enclosing

    def handle_endtag(self, tag: str) -> None:
        if tag in self._VOID:
            return
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index][0] == tag:
                del self._stack[index:]
                return


def _section_regions(html: str) -> dict[str, str | None]:
    parser = _StructureParser()
    parser.feed(html)
    parser.close()
    return parser.section_regions


def _body_text(html: str) -> str:
    without_style = re.sub(r"<style.*?</style>", "", html, flags=re.S)
    stripped = re.sub(r"<[^>]+>", " ", without_style)
    return " ".join(stripped.split())


def _tokens(html: str) -> Counter:
    return Counter(_body_text(html).split())


# ── A/B: valid & deterministic ────────────────────────────────────────────────


class TestValidAndDeterministic:
    def test_valid_html_document(self):
        html = render_layout_html(_cvm(), executive_layout(), blue_theme())
        assert html.startswith("<!DOCTYPE html>")
        assert "<html" in html and "</html>" in html
        assert 'class="resume' in html
        assert 'data-region="main"' in html

    def test_deterministic(self):
        cvm = _cvm()
        a = render_layout_html(cvm, sidebar_layout(), blue_theme())
        b = render_layout_html(cvm, sidebar_layout(), blue_theme())
        assert a == b


# ── C/E/F: same CVM, different layouts → different HTML structure ─────────────


class TestSameCVMDifferentLayouts:
    def test_region_containers_differ(self):
        cvm = _cvm()
        exec_html = render_layout_html(cvm, executive_layout(), blue_theme())
        side_html = render_layout_html(cvm, sidebar_layout(), blue_theme())
        modern_html = render_layout_html(cvm, modern_layout(), blue_theme())

        assert 'data-region="main"' in exec_html and 'data-region="sidebar"' not in exec_html
        assert 'data-region="main"' in side_html and 'data-region="sidebar"' in side_html
        assert 'data-region="secondary"' in modern_html

    def test_section_placement_differs_by_layout(self):
        cvm = _cvm()
        exec_map = _section_regions(render_layout_html(cvm, executive_layout(), blue_theme()))
        side_map = _section_regions(render_layout_html(cvm, sidebar_layout(), blue_theme()))
        modern_map = _section_regions(render_layout_html(cvm, modern_layout(), blue_theme()))
        classic_map = _section_regions(render_layout_html(cvm, classic_layout(), blue_theme()))

        # Skills relocates: main (executive) → sidebar (sidebar) → secondary (modern).
        assert exec_map["skills"] == "main"
        assert side_map["skills"] == "sidebar"
        assert modern_map["skills"] == "secondary"
        assert classic_map["skills"] == "secondary"
        # Profile lives in the full-width header region (executive/modern) or on the
        # sidebar rail (sidebar) / inline in main for the headerless classic layout.
        assert exec_map["profile"] == "header"
        assert side_map["profile"] == "sidebar"
        assert modern_map["profile"] == "header"
        assert classic_map["profile"] == "main"
        # Summary and experience stay in main everywhere (content constant).
        for mapping in (exec_map, side_map, modern_map, classic_map):
            assert mapping["summary"] == "main"
            assert mapping["experience"] == "main"
        # Certifications follows the layout placement (sidebar/secondary vs main).
        assert exec_map["certifications"] == "main"
        assert side_map["certifications"] == "sidebar"
        assert modern_map["certifications"] == "secondary"


# ── D: content preservation ───────────────────────────────────────────────────


class TestContentPreservation:
    def test_content_identical_across_layouts(self):
        cvm = _cvm()
        layouts = (executive_layout(), sidebar_layout(), modern_layout(), classic_layout())
        counters = [_tokens(render_layout_html(cvm, layout, blue_theme())) for layout in layouts]
        assert counters[0] == counters[1] == counters[2] == counters[3]

    def test_substantive_content_present(self):
        html = render_layout_html(_cvm(), sidebar_layout(), blue_theme())
        body = _body_text(html)
        for expected in (
            "Jane Doe",
            "Principal Engineer",
            "Full-stack engineer with 8 years building platforms.",
            "Senior Engineer",
            "Acme",
            "2016 – Present",
            "Engineer",
            "Beta Inc",
            "2014 – 2016",
            "Junior Engineer",
            "Gamma",
            "2012 – 2014",
            "B.Sc. in Computer Science",
            "MIT",
            "Languages",
            "Python",
            "Go",
            "AWS Certified",
            "Amazon",
            "Experience",
            "Skills",
        ):
            assert expected in body

    def test_no_content_duplicated_by_region_flattening(self):
        cvm = _cvm()
        exec_html = render_layout_html(cvm, executive_layout(), blue_theme())
        side_html = render_layout_html(cvm, sidebar_layout(), blue_theme())
        # Each rendered text token appears exactly as often in both layouts.
        assert _tokens(exec_html)["Senior"] == _tokens(side_html)["Senior"] == 1


# ── G: theme separation ───────────────────────────────────────────────────────


class TestThemeSeparation:
    def test_theme_changes_tokens_not_structure(self):
        cvm = _cvm()
        blue = render_layout_html(cvm, sidebar_layout(), blue_theme())
        gold = render_layout_html(cvm, sidebar_layout(), gold_theme())

        assert _section_regions(blue) == _section_regions(gold)
        assert "--primary: #2563eb" in blue
        assert "--primary: #b98a2f" in gold

    def test_layout_change_changes_structure_not_content(self):
        cvm = _cvm()
        # Sidebar + Theme B vs Executive + Theme B: same theme, different layout.
        sidebar_gold = render_layout_html(cvm, sidebar_layout(), gold_theme())
        exec_gold = render_layout_html(cvm, executive_layout(), gold_theme())

        assert _section_regions(sidebar_gold)["skills"] == "sidebar"
        assert _section_regions(exec_gold)["skills"] == "main"
        assert 'data-region="sidebar"' in sidebar_gold
        assert 'data-region="sidebar"' not in exec_gold
        # Same visual tokens, identical content, different structure.
        assert "--primary: #b98a2f" in sidebar_gold and "--primary: #b98a2f" in exec_gold
        assert _tokens(sidebar_gold) == _tokens(exec_gold)


# ── H: invalid tree ───────────────────────────────────────────────────────────


class TestInvalidTree:
    def test_invalid_tree_rejected(self):
        # Model-valid but TreeValidator-invalid: a text node without content_ref.
        text = RenderNode(id="t1", kind=NodeKind.TEXT, data=TextData(type="text", text="x"))
        block = RenderNode(id="b1", kind=NodeKind.BLOCK, region="main", children=(text,))
        section = RenderNode(id="s1", kind=NodeKind.SECTION, content_ref="summary", region="main", children=(block,))
        region = RenderNode(id="r1", kind=NodeKind.REGION, region="main", children=(section,))
        page = RenderNode(id="p1", kind=NodeKind.PAGE, page_size=A4, margins=PageMargins(), children=(region,))
        invalid = RenderNode(id="doc", kind=NodeKind.DOCUMENT, children=(page,))
        with pytest.raises(TreeValidationError):
            RenderTreeHTMLRenderer().render(invalid)


# ── I: empty sections ─────────────────────────────────────────────────────────


class TestEmptySections:
    def test_empty_sections_not_rendered(self):
        cvm = ContentView(
            stable_id="resume.e",
            profile=Profile(full_name="Empty"),
            summary="Only a summary.",
        )
        html = render_layout_html(cvm, executive_layout(), blue_theme())
        assert 'data-section="summary"' in html
        assert 'data-section="skills"' not in html
        assert 'data-section="experience"' not in html


# ── Orchestration: Resume → CVM → … → HTML ───────────────────────────────────


class TestOrchestration:
    def test_render_resume_layout_html(self):
        resume = Resume(
            user_id="u1",
            full_name="Jane Doe",
            email="jane@test.com",
            summary="Full-stack engineer.",
            experience=[{"company": "Acme", "title": "Engineer"}],
        )
        html = render_resume_layout_html(resume, sidebar_layout(), blue_theme(), stable_id="r1")
        assert 'data-region="sidebar"' in html
        assert "Full-stack engineer." in _body_text(html)
        assert "Engineer" in _body_text(html)


# ── Structured component output ───────────────────────────────────────────────


def _structured_cvm() -> ContentView:
    return ContentView(
        stable_id="resume.structured",
        profile=Profile(full_name="Jane Doe", professional_title="Principal Engineer"),
        summary="Backend engineer focused on distributed systems.",
        experience=(
            ExperienceEntry(
                company="Acme Corp",
                title="Senior Engineer",
                location="Boston, MA",
                start_date="2021",
                end_date="2024",
                description=("Led the platform team", "Cut p99 latency by 40%"),
            ),
        ),
        education=(
            EducationEntry(
                institution="MIT", degree="M.S.", field="Computer Science", start_date="2014", end_date="2016", gpa=3.9
            ),
        ),
        skills=(SkillGroup(category="Languages", skills=("Python", "Go")),),
        certifications=(CertificationEntry(name="AWS Certified", issuer="Amazon", date="2022"),),
    )


class TestStructuredComponents:
    def test_experience_is_structured(self):
        html = render_layout_html(_structured_cvm(), sidebar_layout(), blue_theme())
        body = _body_text(html)
        assert "Senior Engineer" in body  # title
        assert "Acme Corp · Boston, MA" in body  # company · location
        assert "2021 – 2024" in body  # period
        assert "Led the platform team" in body  # description bullet
        assert "Cut p99 latency by 40%" in body
        assert '<ul class="resume-list">' in html
        assert html.count("<li>") >= 2  # two description bullets

    def test_education_is_structured(self):
        html = render_layout_html(_structured_cvm(), sidebar_layout(), blue_theme())
        body = _body_text(html)
        assert "M.S. in Computer Science" in body
        assert "MIT" in body
        assert "2014 – 2016" in body
        assert "GPA: 3.9" in body

    def test_skills_are_grouped(self):
        html = render_layout_html(_structured_cvm(), sidebar_layout(), blue_theme())
        body = _body_text(html)
        assert "Languages" in body
        assert "Python" in body and "Go" in body
        assert '<ul class="resume-list">' in html

    def test_grouped_skill_is_single_li_with_bold_category(self):
        html = render_layout_html(_structured_cvm(), sidebar_layout(), blue_theme())
        section = re.search(r'<section class="resume-section resume-section-skills".*?</section>', html, re.S).group(0)
        lis = re.findall(r"<li>.*?</li>", section, re.S)
        assert len(lis) == 1
        assert lis[0] == "<li><strong>Languages:</strong> Python, Go</li>"
        assert '<ul class="resume-list">' in section

    def test_grouped_skills_no_middot_no_duplicated_category(self):
        html = render_layout_html(_structured_cvm(), sidebar_layout(), blue_theme())
        section = re.search(r'<section class="resume-section resume-section-skills".*?</section>', html, re.S).group(0)
        assert "\u00b7" not in section
        assert section.count("Languages") == 1

    def test_multiple_skill_groups_each_render_single_li(self):
        cvm = ContentView(
            stable_id="resume.multi-skills",
            profile=Profile(full_name="Jane Doe", professional_title="Engineer"),
            skills=(
                SkillGroup(category="Languages", skills=("Python", "Go")),
                SkillGroup(category="Cloud", skills=("AWS", "Azure")),
            ),
        )
        html = render_layout_html(cvm, sidebar_layout(), blue_theme())
        section = re.search(r'<section class="resume-section resume-section-skills".*?</section>', html, re.S).group(0)
        lis = re.findall(r"<li>.*?</li>", section, re.S)
        assert lis == [
            "<li><strong>Languages:</strong> Python, Go</li>",
            "<li><strong>Cloud:</strong> AWS, Azure</li>",
        ]

    def test_skills_ats_single_logical_unit(self):
        context = RenderContext(layout=sidebar_layout(), theme=blue_theme(), state=RenderState())
        tree = TreeBuilder(default_component_registry()).build(_structured_cvm(), context)
        spans = TreeValidator().extract_text(tree)
        skill_texts = [span.text for span in spans if span.content_ref == "skills"]
        assert skill_texts == ["Languages: Python, Go"]

    def test_certifications_are_structured(self):
        html = render_layout_html(_structured_cvm(), sidebar_layout(), blue_theme())
        body = _body_text(html)
        assert "AWS Certified" in body
        assert "Amazon" in body
        assert "2022" in body

    def test_grouped_certification_is_single_li_with_bold_category(self):
        cvm = ContentView(
            stable_id="resume.grouped-certs",
            profile=Profile(full_name="Jane Doe", professional_title="Engineer"),
            certifications=(
                CertificationEntry(
                    category="Professional Credentials",
                    values=("PRINCE2 Practitioner", "Certified Scrum Master (CSM)", "ITIL Foundation Certificate"),
                ),
            ),
        )
        html = render_layout_html(cvm, sidebar_layout(), blue_theme())
        section = re.search(
            r'<section class="resume-section resume-section-certifications".*?</section>', html, re.S
        ).group(0)
        lis = re.findall(r"<li>.*?</li>", section, re.S)
        assert lis == [
            "<li><strong>Professional Credentials:</strong> "
            "PRINCE2 Practitioner | Certified Scrum Master (CSM) | ITIL Foundation Certificate</li>"
        ]
        assert "|" in lis[0]

    def test_grouped_certification_no_duplication(self):
        cvm = ContentView(
            stable_id="resume.grouped-certs-dup",
            profile=Profile(full_name="Jane Doe", professional_title="Engineer"),
            certifications=(
                CertificationEntry(category="AI & Emerging Technologies", values=("GitHub Copilot", "Claude")),
            ),
        )
        html = render_layout_html(cvm, sidebar_layout(), blue_theme())
        section = re.search(
            r'<section class="resume-section resume-section-certifications".*?</section>', html, re.S
        ).group(0)
        assert section.count("AI &amp; Emerging Technologies") == 1
        assert section.count("GitHub Copilot") == 1

    def test_multiple_grouped_certifications_each_single_li(self):
        cvm = ContentView(
            stable_id="resume.multi-grouped-certs",
            profile=Profile(full_name="Jane Doe", professional_title="Engineer"),
            certifications=(
                CertificationEntry(category="Professional Credentials", values=("PRINCE2 Practitioner",)),
                CertificationEntry(category="AI & Emerging Technologies", values=("Claude", "RAG")),
                CertificationEntry(category="Enterprise Platforms & DevOps", values=("ServiceNow", "Azure DevOps")),
            ),
        )
        html = render_layout_html(cvm, sidebar_layout(), blue_theme())
        section = re.search(
            r'<section class="resume-section resume-section-certifications".*?</section>', html, re.S
        ).group(0)
        lis = re.findall(r"<li>.*?</li>", section, re.S)
        assert lis == [
            "<li><strong>Professional Credentials:</strong> PRINCE2 Practitioner</li>",
            "<li><strong>AI &amp; Emerging Technologies:</strong> Claude | RAG</li>",
            "<li><strong>Enterprise Platforms &amp; DevOps:</strong> ServiceNow | Azure DevOps</li>",
        ]

    def test_individual_certification_card_preserved(self):
        cvm = ContentView(
            stable_id="resume.individual-cert",
            profile=Profile(full_name="Jane Doe", professional_title="Engineer"),
            certifications=(CertificationEntry(name="PMP", issuer="Project Management Institute", date="2025"),),
        )
        html = render_layout_html(cvm, sidebar_layout(), blue_theme())
        section = re.search(
            r'<section class="resume-section resume-section-certifications".*?</section>', html, re.S
        ).group(0)
        assert '<div class="resume-block">' in section
        assert '<p class="resume-text resume-strong">PMP</p>' in section
        assert '<p class="resume-text resume-muted">Project Management Institute · 2025</p>' in section
        assert "<li>" not in section

    def test_mixed_certifications_use_correct_renderer(self):
        cvm = ContentView(
            stable_id="resume.mixed-certs",
            profile=Profile(full_name="Jane Doe", professional_title="Engineer"),
            certifications=(
                CertificationEntry(category="Professional Credentials", values=("PRINCE2 Practitioner",)),
                CertificationEntry(name="PMP", issuer="PMI", date="2025"),
                CertificationEntry(category="AI & Emerging Technologies", values=("Claude",)),
                CertificationEntry(name="AWS Certified", issuer="Amazon", date="2022"),
            ),
        )
        html = render_layout_html(cvm, sidebar_layout(), blue_theme())
        section = re.search(
            r'<section class="resume-section resume-section-certifications".*?</section>', html, re.S
        ).group(0)
        lis = re.findall(r"<li>.*?</li>", section, re.S)
        assert lis == [
            "<li><strong>Professional Credentials:</strong> PRINCE2 Practitioner</li>",
            "<li><strong>AI &amp; Emerging Technologies:</strong> Claude</li>",
        ]
        assert '<p class="resume-text resume-strong">PMP</p>' in section
        assert '<p class="resume-text resume-muted">PMI · 2025</p>' in section
        assert '<p class="resume-text resume-strong">AWS Certified</p>' in section
        assert '<p class="resume-text resume-muted">Amazon · 2022</p>' in section
        assert section.index("Professional Credentials") < section.index("PMP")
        assert section.index("PMP") < section.index("AI &amp; Emerging Technologies")

    def test_grouped_certification_ats_single_logical_unit(self):
        cvm = ContentView(
            stable_id="resume.grouped-certs-ats",
            profile=Profile(full_name="Jane Doe", professional_title="Engineer"),
            certifications=(
                CertificationEntry(
                    category="Professional Credentials",
                    values=("PRINCE2 Practitioner", "Certified Scrum Master (CSM)", "ITIL Foundation Certificate"),
                ),
            ),
        )
        context = RenderContext(layout=sidebar_layout(), theme=blue_theme(), state=RenderState())
        tree = TreeBuilder(default_component_registry()).build(cvm, context)
        spans = TreeValidator().extract_text(tree)
        cert_texts = [span.text for span in spans if span.content_ref == "certifications"]
        assert cert_texts == [
            "Professional Credentials: PRINCE2 Practitioner | Certified Scrum Master (CSM) | ITIL Foundation Certificate"
        ]


# ── Long-content robustness ───────────────────────────────────────────────────


def _long_cvm() -> ContentView:
    companies = [f"Company {i} International Solutions Group" for i in range(6)]
    jobs = tuple(
        ExperienceEntry(
            company=companies[i],
            title=f"Senior Principal Engineering Manager {i}",
            location=f"City {i}, State",
            start_date=f"20{10 + i}",
            end_date=None if i == 5 else f"20{15 + i}",
            current=i == 5,
            description=(
                "Led a distributed team across three regions and multiple time zones",
                "Designed and shipped a multi-tenant streaming platform serving millions of users",
                "Reduced infrastructure cost by 35% through workload consolidation",
            ),
        )
        for i in range(6)
    )
    return ContentView(
        stable_id="resume.long",
        profile=Profile(full_name="Alexandra Rivera", professional_title="Distinguished Platform Engineer"),
        summary="Very long professional summary that keeps going across multiple lines of text " * 4,
        experience=jobs,
        education=tuple(
            EducationEntry(
                institution=f"University {i}",
                degree="Ph.D.",
                field="Computer Science",
                start_date="2008",
                end_date="2012",
                gpa=3.9,
            )
            for i in range(3)
        ),
        skills=(
            SkillGroup(
                category="Languages", skills=("Python", "Go", "Rust", "TypeScript", "Java", "C++", "C#", "Ruby")
            ),
            SkillGroup(
                category="Infrastructure",
                skills=("Kubernetes", "Docker", "AWS", "Terraform", "Kafka", "PostgreSQL", "Redis", "gRPC"),
            ),
        ),
        certifications=tuple(
            CertificationEntry(name=f"Certification {i}", issuer="Major Vendor", date="2022") for i in range(4)
        ),
        projects=tuple(
            ProjectEntry(
                name=f"Large Scale Distributed Project {i}",
                description="A very long project description spanning multiple lines of substantive engineering detail",
                url="https://github.com/example/long-project",
                technologies=("Go", "Rust", "Kafka", "PostgreSQL"),
            )
            for i in range(3)
        ),
        awards=(
            AwardEntry(title="Distinguished Engineering Award", issuer="Major Organization", date="2023"),
            AwardEntry(title="Best Platform Initiative", issuer="Industry Forum", date="2022"),
        ),
        languages=(
            LanguageEntry(name="English", proficiency="Native"),
            LanguageEntry(name="German", proficiency="Professional"),
            LanguageEntry(name="Spanish", proficiency="Conversational"),
        ),
    )


class TestLongContent:
    def test_all_long_content_present_no_clipping(self):
        cvm = _long_cvm()
        html = render_layout_html(cvm, sidebar_layout(), blue_theme())
        body = _body_text(html)
        assert len(cvm.experience) == 6
        for company in [f"Company {i} International Solutions Group" for i in range(6)]:
            assert company in body
        assert "Distinguished Platform Engineer" in body
        assert "Python" in body and "gRPC" in body
        assert "Certification 3" in body
        assert "Large Scale Distributed Project 2" in body
        assert "Distinguished Engineering Award" in body
        assert "German — Professional" in body
        # No fixed-height clipping: the renderer never emits inline or px heights.
        assert 'style="height:' not in html
        assert re.search(r"height:\s*\d+px", html) is None

    def test_long_content_same_across_layouts(self):
        cvm = _long_cvm()
        layouts = (executive_layout(), sidebar_layout(), modern_layout(), classic_layout())
        counters = [_tokens(render_layout_html(cvm, layout, blue_theme())) for layout in layouts]
        assert counters[0] == counters[1] == counters[2] == counters[3]

    def test_comprehensive_sections_survive_all_layouts(self):
        cvm = _long_cvm()
        layouts = (executive_layout(), sidebar_layout(), modern_layout(), classic_layout())
        for layout in layouts:
            body = _body_text(render_layout_html(cvm, layout, blue_theme()))
            assert "Alexandra Rivera" in body
            assert "Company 5 International Solutions Group" in body  # 6th job
            assert "Large Scale Distributed Project 2" in body  # 3rd project
            assert "Best Platform Initiative" in body  # 2nd award
            assert "Spanish — Conversational" in body  # 3rd language


# ── Projects / Awards / Languages coverage ────────────────────────────────────


def _comprehensive_cvm() -> ContentView:
    return ContentView(
        stable_id="resume.comprehensive",
        profile=Profile(full_name="Jane Doe", professional_title="Senior Project Manager"),
        summary="Backend platform engineer focused on distributed systems.",
        experience=(
            ExperienceEntry(
                company="Acme Corp",
                title="Senior Engineer",
                location="Boston, MA",
                start_date="2021",
                end_date="2024",
                description=("Led the platform team", "Cut latency"),
            ),
            ExperienceEntry(company="Beta Inc", title="Engineer", start_date="2018", end_date="2021"),
        ),
        education=(EducationEntry(institution="MIT", degree="M.S.", field="Computer Science", gpa=3.9),),
        skills=(SkillGroup(category="Languages", skills=("Python", "Go")),),
        certifications=(CertificationEntry(name="AWS Certified", issuer="Amazon", date="2022"),),
        projects=(
            ProjectEntry(
                name="Orbit Scheduler",
                description="Distributed task scheduler\nMulti-tenant workload isolation\nSub-second scheduling",
                url="https://github.com/example/orbit",
                technologies=("Go", "PostgreSQL"),
            ),
        ),
        awards=(AwardEntry(title="Employee of the Year", issuer="Acme", date="2023"),),
        languages=(
            LanguageEntry(name="English", proficiency="Native"),
            LanguageEntry(name="German", proficiency="Professional"),
        ),
    )


class TestProjectsAwardsLanguages:
    def test_projects_structured(self):
        html = render_layout_html(_comprehensive_cvm(), executive_layout(), blue_theme())
        body = _body_text(html)
        assert "Orbit Scheduler" in body
        assert "Distributed task scheduler" in body
        assert "Multi-tenant workload isolation" in body
        assert "Sub-second scheduling" in body
        assert "Go" in body and "PostgreSQL" in body
        assert "https://github.com/example/orbit" in body
        assert html.count("<li>") >= 3  # description lines + technologies

    def test_awards_structured(self):
        html = render_layout_html(_comprehensive_cvm(), sidebar_layout(), blue_theme())
        body = _body_text(html)
        assert "Employee of the Year" in body
        assert "Acme" in body
        assert "2023" in body

    def test_languages_structured(self):
        html = render_layout_html(_comprehensive_cvm(), sidebar_layout(), blue_theme())
        body = _body_text(html)
        assert "English — Native" in body
        assert "German — Professional" in body
        assert '<ul class="resume-list">' in html

    def test_all_three_survive_every_layout(self):
        cvm = _comprehensive_cvm()
        layouts = (executive_layout(), sidebar_layout(), modern_layout(), classic_layout())
        for layout in layouts:
            body = _body_text(render_layout_html(cvm, layout, blue_theme()))
            assert "Orbit Scheduler" in body
            assert "Employee of the Year" in body
            assert "English — Native" in body

    def test_comprehensive_content_identical_across_layouts(self):
        cvm = _comprehensive_cvm()
        layouts = (executive_layout(), sidebar_layout(), modern_layout(), classic_layout())
        counters = [_tokens(render_layout_html(cvm, layout, blue_theme())) for layout in layouts]
        assert counters[0] == counters[1] == counters[2] == counters[3]

    def test_new_components_resolve_through_registry(self):
        from app.rendering.components import (
            AwardsComponent,
            ComponentRegistry,
            LanguagesComponent,
            ProjectsComponent,
        )

        registry = ComponentRegistry()
        registry.register(ProjectsComponent())
        registry.register(AwardsComponent())
        registry.register(LanguagesComponent())
        assert isinstance(registry.resolve("projects"), ProjectsComponent)
        assert isinstance(registry.resolve("awards"), AwardsComponent)
        assert isinstance(registry.resolve("languages"), LanguagesComponent)


# ── J + architecture: renderer independence ───────────────────────────────────


def _module_imports(dotted: str) -> set[str]:
    module = importlib.import_module(dotted)
    path = Path(inspect.getsourcefile(module))
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
    return imports


def _imports_package(imports: set[str], package: str) -> bool:
    prefix = package + "."
    return any(item == package or item.startswith(prefix) for item in imports)


class TestRendererIndependence:
    def test_renderer_consumes_tree_and_theme_only(self):
        imports = _module_imports("app.rendering.renderers.tree_html_renderer")
        assert _imports_package(imports, "app.rendering.tree")
        assert _imports_package(imports, "app.rendering.theme")
        assert _imports_package(imports, "app.rendering.common")
        for forbidden in (
            "app.rendering.content",
            "app.rendering.components",
            "app.rendering.layout",
            "app.rendering.preview",
            "app.rendering.registry",
            "app.rendering.builder",
            "app.models",
            "app.services",
        ):
            assert not _imports_package(imports, forbidden), forbidden

    def test_orchestration_avoids_legacy_and_preview(self):
        imports = _module_imports("app.rendering.layout_html")
        assert not _imports_package(imports, "app.rendering.preview")
        assert not _imports_package(imports, "app.rendering.registry")
        assert not _imports_package(imports, "app.rendering.renderers.html_renderer")
        assert not _imports_package(imports, "app.services")

    def test_legacy_renderer_untouched(self):
        imports = _module_imports("app.rendering.renderers.tree_html_renderer")
        assert not _imports_package(imports, "app.rendering.registry")
