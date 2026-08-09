"""Tests for the RenderTree → PDF renderer (Layout Engine)."""

import ast
import importlib
import inspect
from collections import Counter
from pathlib import Path

import pytest
from pypdf import PdfReader

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
from app.rendering.layout.reference_layouts import classic_layout, executive_layout, modern_layout, sidebar_layout
from app.rendering.layout_html import render_layout_pdf
from app.rendering.renderers.tree_pdf_renderer import RenderTreePDFRenderer
from app.rendering.theme.reference_themes import blue_theme, gold_theme
from app.rendering.tree import NodeKind, RenderNode
from app.rendering.tree.validator import TreeValidationError


def _comprehensive_cvm() -> ContentView:
    return ContentView(
        stable_id="resume.pdf",
        profile=Profile(
            full_name="Sharma Rajasekar",
            professional_title="Senior Transformation & Infrastructure Leader",
            email="sharma@test.com",
            phone="+1-555-0100",
            location="Auckland, New Zealand",
            linkedin="https://linkedin.com/in/sharma",
            website="https://sharma.dev",
        ),
        summary="Transformation leader focused on distributed systems, streaming pipelines, and reliability.",
        experience=(
            ExperienceEntry(company="Acme Corporation International", title="Senior Software Engineering Lead",
                            location="San Francisco, CA", start_date="2021", current=True,
                            description=("Led a 12-engineer platform organization", "Designed multi-region streaming")),
            ExperienceEntry(company="Beta Inc", title="Transformation Programme Manager",
                            start_date="2018", end_date="2021", description=("Built a distributed scheduler",)),
            ExperienceEntry(company="Gamma Labs", title="Senior Software Engineer",
                            start_date="2016", end_date="2018", description=("Developed observability tooling",)),
        ),
        education=(
            EducationEntry(institution="Carnegie Mellon University", degree="Master of Science", field="Computer Science", gpa=3.9),
            EducationEntry(institution="University of Auckland", degree="Bachelor of Engineering", field="Software", gpa=3.6),
        ),
        skills=(
            SkillGroup(category="Languages", skills=("Python", "Go", "Rust")),
            SkillGroup(category="Cloud", skills=("AWS", "Azure", "Kubernetes")),
        ),
        certifications=(
            CertificationEntry(name="AWS Solutions Architect", issuer="Amazon Web Services", date="2022"),
            CertificationEntry(name="PMP", issuer="PMI", date="2021"),
        ),
        projects=(
            ProjectEntry(name="Project Alpha", description="Distributed scheduler", technologies=("Go", "PostgreSQL")),
            ProjectEntry(name="Project Beta", description="Streaming reliability platform", url="https://github.com/example/beta", technologies=("Rust", "Kafka")),
            ProjectEntry(name="Project Gamma", description="Observability platform", technologies=("Python", "ClickHouse")),
        ),
        awards=(
            AwardEntry(title="Transformation Excellence Award", issuer="Acme Corporation", date="2023-06"),
            AwardEntry(title="Innovation Leadership Award", issuer="Industry Forum", date="2022-11"),
        ),
        languages=(
            LanguageEntry(name="English", proficiency="Native"),
            LanguageEntry(name="Tamil", proficiency="Native"),
            LanguageEntry(name="French", proficiency="Professional"),
        ),
    )


def _long_cvm() -> ContentView:
    return ContentView(
        stable_id="resume.long",
        profile=Profile(full_name="Alexandra Rivera", professional_title="Distinguished Platform Engineer"),
        summary="Very long professional summary that keeps going across multiple lines of text " * 4,
        experience=tuple(
            ExperienceEntry(
                company=f"Company {i} International Solutions Group",
                title=f"Senior Principal Engineering Manager {i}",
                start_date=f"20{10 + i}",
                end_date=None if i == 5 else f"20{15 + i}",
                current=i == 5,
                description=("Led distributed teams across regions", "Designed streaming platforms", "Reduced costs by 35%"),
            )
            for i in range(6)
        ),
        education=tuple(EducationEntry(institution=f"University {i}", degree="Ph.D.", field="Computer Science") for i in range(3)),
        skills=tuple(SkillGroup(category=f"Group {i}", skills=("Python", "Go", "Rust", "AWS", "Kubernetes", "Kafka", "Docker", "Terraform")) for i in range(2)),
        certifications=tuple(CertificationEntry(name=f"Certification {i}", issuer="Vendor", date="2022") for i in range(4)),
        projects=tuple(ProjectEntry(name=f"Project {i}", description="A long project description across multiple lines", technologies=("Go", "Rust")) for i in range(3)),
        awards=tuple(AwardEntry(title=f"Award {i}", issuer="Org", date="2023") for i in range(2)),
        languages=tuple(LanguageEntry(name=f"Language {i}", proficiency="Native") for i in range(3)),
    )


def _compact_cvm() -> ContentView:
    """A single-page resume used for structural (x-position) comparisons."""
    return ContentView(
        stable_id="resume.compact",
        profile=Profile(full_name="Jane Doe", professional_title="Senior Engineer"),
        summary="Platform engineer.",
        experience=(ExperienceEntry(company="Acme", title="Senior Engineer", start_date="2021", current=True),),
        education=(EducationEntry(institution="MIT", degree="M.S.", field="CS"),),
        skills=(SkillGroup(category="Languages", skills=("Python", "Go")),),
        certifications=(CertificationEntry(name="AWS Certified", issuer="Amazon"),),
    )


def _pdf_text(reader: PdfReader) -> str:
    return " ".join((page.extract_text() or "") for page in reader.pages)


def _tokens(text: str) -> Counter:
    return Counter(text.split())


def _x_positions(reader: PdfReader, targets: tuple[str, ...]) -> dict[str, float]:
    page = reader.pages[0]
    found: dict[str, float] = {}
    positions: list[tuple[float, str]] = []

    def cb(text: str, cm, tm, font, size):
        positions.append((tm[4], text.strip()))

    page.extract_text(visitor_text=cb)
    for x, word in positions:
        for target in targets:
            if target in word and target not in found:
                found[target] = round(x, 1)
    return found


# ── 1/2: valid & readable PDF ─────────────────────────────────────────────────


class TestValidPDF:
    def test_signature_and_readability(self):
        pdf = render_layout_pdf(_comprehensive_cvm(), executive_layout(), blue_theme())
        assert pdf[:5] == b"%PDF-"
        reader = PdfReader(io_bytes(pdf))
        assert len(reader.pages) >= 1
        assert "Sharma Rajasekar" in _pdf_text(reader)


def io_bytes(data: bytes):
    from io import BytesIO

    return BytesIO(data)


# ── substantive content preservation ──────────────────────────────────────────


class TestContentPreservation:
    def test_all_sections_and_values_present(self):
        pdf = render_layout_pdf(_comprehensive_cvm(), executive_layout(), blue_theme())
        text = _pdf_text(PdfReader(io_bytes(pdf)))
        for expected in (
            "Sharma Rajasekar",
            "Senior Transformation",
            "Infrastructure Leader",
            "Acme Corporation International",
            "Senior Software Engineering Lead",
            "Transformation Programme Manager",
            "Carnegie Mellon University",
            "Master of Science",
            "AWS",
            "Azure",
            "Kubernetes",
            "AWS Solutions Architect",
            "PMP",
            "Project Alpha",
            "Project Beta",
            "Project Gamma",
            "Transformation Excellence Award",
            "Innovation Leadership Award",
            "English",
            "Tamil",
            "French",
            "Native",
            "Professional",
            "sharma@test.com",
        ):
            assert expected in text, expected

    def test_projects_awards_languages_professional_title(self):
        text = _pdf_text(PdfReader(io_bytes(render_layout_pdf(_comprehensive_cvm(), sidebar_layout(), blue_theme()))))
        assert "Project Alpha" in text and "Project Beta" in text and "Project Gamma" in text
        assert "Transformation Excellence Award" in text and "Innovation Leadership Award" in text
        assert "English" in text and "Tamil" in text and "French" in text
        assert "Senior Transformation" in text


# ── all four layouts: same content, different structure ───────────────────────


class TestFourLayouts:
    def test_same_content_across_layouts(self):
        cvm = _comprehensive_cvm()
        counters = []
        for layout in (executive_layout(), sidebar_layout(), modern_layout(), classic_layout()):
            reader = PdfReader(io_bytes(render_layout_pdf(cvm, layout, blue_theme())))
            counters.append(_tokens(_pdf_text(reader)))
        assert counters[0] == counters[1] == counters[2] == counters[3]

    def test_layout_structure_differs(self):
        cvm = _compact_cvm()
        # Sidebar places skills in the right rail: different x than main.
        side = PdfReader(io_bytes(render_layout_pdf(cvm, sidebar_layout(), blue_theme())))
        exec_pdf = PdfReader(io_bytes(render_layout_pdf(cvm, executive_layout(), blue_theme())))
        side_x = _x_positions(side, ("SKILLS", "SUMMARY"))
        exec_x = _x_positions(exec_pdf, ("SKILLS", "SUMMARY"))
        # In the sidebar layout skills sit well to the right of summary.
        assert side_x.get("SKILLS", 0) > side_x.get("SUMMARY", 99999) + 50
        # In the executive (single column) layout they share the same x.
        assert abs(exec_x.get("SKILLS", -1) - exec_x.get("SUMMARY", -2)) < 30


# ── multi-page ────────────────────────────────────────────────────────────────


class TestMultiPage:
    def test_long_resume_spans_pages_with_all_content(self):
        pdf = render_layout_pdf(_long_cvm(), sidebar_layout(), blue_theme())
        reader = PdfReader(io_bytes(pdf))
        assert len(reader.pages) >= 2
        text = _pdf_text(reader)
        assert "Company 5 International Solutions Group" in text  # 6th job
        assert "Project 2" in text
        assert "Award 1" in text
        assert "Language 2" in text
        assert "Certification 3" in text


# ── links ─────────────────────────────────────────────────────────────────────


class TestLinks:
    def test_link_text_present(self):
        text = _pdf_text(PdfReader(io_bytes(render_layout_pdf(_comprehensive_cvm(), sidebar_layout(), blue_theme()))))
        assert "https://github.com/example/beta" in text
        assert "https://linkedin.com/in/sharma" in text

    def test_links_are_annotations(self):
        reader = PdfReader(io_bytes(render_layout_pdf(_comprehensive_cvm(), sidebar_layout(), blue_theme())))
        total_annots = 0
        for page in reader.pages:
            annots = page.get("/Annots")
            if annots:
                total_annots += len(annots)
        assert total_annots >= 1


# ── theme / layout separation ─────────────────────────────────────────────────


class TestThemeLayoutSeparation:
    def test_theme_changes_tokens_not_content(self):
        cvm = _comprehensive_cvm()
        blue_text = _pdf_text(PdfReader(io_bytes(render_layout_pdf(cvm, sidebar_layout(), blue_theme()))))
        gold_text = _pdf_text(PdfReader(io_bytes(render_layout_pdf(cvm, sidebar_layout(), gold_theme()))))
        assert _tokens(blue_text) == _tokens(gold_text)
        assert "Sharma Rajasekar" in blue_text and "Sharma Rajasekar" in gold_text

    def test_layout_changes_structure_not_content(self):
        cvm = _compact_cvm()
        side = PdfReader(io_bytes(render_layout_pdf(cvm, sidebar_layout(), gold_theme())))
        exec_pdf = PdfReader(io_bytes(render_layout_pdf(cvm, executive_layout(), gold_theme())))
        side_x = _x_positions(side, ("SKILLS", "SUMMARY"))
        exec_x = _x_positions(exec_pdf, ("SKILLS", "SUMMARY"))
        assert side_x.get("SKILLS", 0) > side_x.get("SUMMARY", 99999) + 50
        assert abs(exec_x.get("SKILLS", -1) - exec_x.get("SUMMARY", -2)) < 30
        assert _tokens(_pdf_text(side)) == _tokens(_pdf_text(exec_pdf))


# ── determinism ───────────────────────────────────────────────────────────────


class TestDeterminism:
    def test_same_content_across_runs(self):
        cvm = _comprehensive_cvm()
        a = _pdf_text(PdfReader(io_bytes(render_layout_pdf(cvm, sidebar_layout(), blue_theme()))))
        b = _pdf_text(PdfReader(io_bytes(render_layout_pdf(cvm, sidebar_layout(), blue_theme()))))
        assert _tokens(a) == _tokens(b)


# ── error handling ────────────────────────────────────────────────────────────


class TestErrors:
    def test_invalid_tree_rejected(self):
        from app.rendering.tree import A4, PageMargins, TextData

        # Model-valid but TreeValidator-invalid: a text node without content_ref.
        text = RenderNode(id="t1", kind=NodeKind.TEXT, data=TextData(type="text", text="x"))
        block = RenderNode(id="b1", kind=NodeKind.BLOCK, region="main", children=(text,))
        section = RenderNode(id="s1", kind=NodeKind.SECTION, content_ref="summary", region="main", children=(block,))
        region = RenderNode(id="r1", kind=NodeKind.REGION, region="main", children=(section,))
        page = RenderNode(id="p1", kind=NodeKind.PAGE, page_size=A4, margins=PageMargins(), children=(region,))
        invalid = RenderNode(id="doc", kind=NodeKind.DOCUMENT, children=(page,))
        with pytest.raises(TreeValidationError):
            RenderTreePDFRenderer().render(invalid)

    def test_special_characters_rendered_as_text(self):
        cvm = ContentView(
            stable_id="resume.special",
            profile=Profile(full_name="A & B <script>alert(1)</script>", professional_title="Engineer \"Q\" 'A'"),
            summary="Dangerous <b> & \" ' content",
        )
        pdf = render_layout_pdf(cvm, classic_layout(), blue_theme())
        text = _pdf_text(PdfReader(io_bytes(pdf)))
        # The literal characters survive as safe text; no markup is executed.
        assert "A & B" in text
        assert "<script>alert(1)</script>" in text  # preserved literally, not as an element
        assert 'Engineer' in text
        assert "Dangerous" in text


# ── orchestration end-to-end ──────────────────────────────────────────────────


class TestOrchestration:
    def test_render_layout_pdf(self):
        cvm = _comprehensive_cvm()
        pdf = render_layout_pdf(cvm, sidebar_layout(), blue_theme())
        assert pdf[:5] == b"%PDF-"
        text = _pdf_text(PdfReader(io_bytes(pdf)))
        assert "Sharma Rajasekar" in text


# ── renderer import isolation ─────────────────────────────────────────────────


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


class TestImportIsolation:
    def test_pdf_renderer_is_pure_render_tree_consumer(self):
        imports = _module_imports("app.rendering.renderers.tree_pdf_renderer")
        assert _imports_package(imports, "app.rendering.tree")
        assert _imports_package(imports, "app.rendering.theme")
        assert _imports_package(imports, "app.rendering.renderers")
        for forbidden in (
            "app.rendering.content",
            "app.rendering.components",
            "app.rendering.layout",
            "app.rendering.preview",
            "app.rendering.registry",
            "app.rendering.builder",
            "app.services",
            "app.models",
        ):
            assert not _imports_package(imports, forbidden), forbidden
