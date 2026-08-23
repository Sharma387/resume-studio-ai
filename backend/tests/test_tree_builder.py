"""Tests for the TreeBuilder (Layout Engine, Phase 0).

The acceptance criterion: the SAME ContentView rendered through materially
different LayoutDefinitions must produce DIFFERENT render structures while
preserving identical content.
"""

import ast
import concurrent.futures
import importlib
import inspect
from collections import Counter
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.rendering.builder import TreeBuilder, TreeBuilderError
from app.rendering.components import (
    CertificationsComponent,
    ComponentRegistry,
    EducationComponent,
    ExperienceComponent,
    ProfileComponent,
    SkillsComponent,
    SummaryComponent,
)
from app.rendering.content import ContentView, Profile
from app.rendering.content.models import (
    CertificationEntry,
    EducationEntry,
    ExperienceEntry,
    LanguageEntry,
    SkillGroup,
)
from app.rendering.context import ContentReference, RenderContext
from app.rendering.layout.layout_metadata import LayoutVersion
from app.rendering.layout.reference_layouts import (
    classic_layout,
    executive_layout,
    modern_layout,
    sidebar_layout,
)
from app.rendering.theme.reference_themes import blue_theme
from app.rendering.tree import NodeKind, RenderNode
from app.rendering.tree.validator import TreeValidator


def _registry() -> ComponentRegistry:
    registry = ComponentRegistry()
    for component in (
        ProfileComponent(),
        SummaryComponent(),
        ExperienceComponent(),
        EducationComponent(),
        SkillsComponent(),
        CertificationsComponent(),
    ):
        registry.register(component)
    return registry


def _cvm() -> ContentView:
    return ContentView(
        stable_id="resume.accept",
        profile=Profile(full_name="Jane Doe", professional_title="Principal Engineer"),
        summary="Full-stack engineer with 8 years building platforms.",
        experience=(
            ExperienceEntry(company="Acme", title="Senior Engineer", start_date="2016", current=True, description=("Led platform",)),
            ExperienceEntry(company="Beta Inc", title="Engineer", start_date="2014", end_date="2016", description=("Built APIs",)),
            ExperienceEntry(company="Gamma", title="Junior Engineer", start_date="2012", end_date="2014", description=("Shipped features",)),
        ),
        education=(EducationEntry(institution="MIT", degree="B.Sc.", field="Computer Science", gpa=3.8),),
        skills=(SkillGroup(category="Languages", skills=("Python", "Go")),),
        certifications=(CertificationEntry(name="AWS Certified", issuer="Amazon"),),
    )


def _context(cvm: ContentView, layout) -> RenderContext:
    return RenderContext(
        content_ref=ContentReference(stable_id=cvm.stable_id, content_hash=cvm.content_hash),
        layout=layout,
        theme=blue_theme(),
    )


def _region_sections(root: RenderNode) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for page in root.children:
        for region in page.children:
            if region.kind is NodeKind.REGION:
                result[region.region] = [
                    section.content_ref
                    for section in region.children
                    if section.kind is NodeKind.SECTION
                ]
    return result


def _text_counter(root: RenderNode) -> Counter:
    validator = TreeValidator()
    return Counter((span.content_ref, span.text) for span in validator.extract_text(root))


# ── STRICT ACCEPTANCE: same CVM, materially different layouts ─────────────────


class TestStructuralLayoutAcceptance:
    def test_same_cvm_different_layouts_different_structures(self):
        builder = TreeBuilder(_registry())
        cvm = _cvm()

        exec_doc = builder.build(cvm, _context(cvm, executive_layout()))
        side_doc = builder.build(cvm, _context(cvm, sidebar_layout()))
        modern_doc = builder.build(cvm, _context(cvm, modern_layout()))
        classic_doc = builder.build(cvm, _context(cvm, classic_layout()))

        exec_map = _region_sections(exec_doc)
        side_map = _region_sections(side_doc)
        modern_map = _region_sections(modern_doc)
        classic_map = _region_sections(classic_doc)

        # Region composition differs by layout.
        assert set(exec_map) == {"header", "main"}
        assert set(side_map) == {"main", "sidebar"}
        assert set(modern_map) == {"header", "main", "secondary"}
        assert set(classic_map) == {"main", "secondary"}

        # Same CVM, materially different section→region placement.
        assert exec_map == {
            "header": ["profile"],
            "main": ["summary", "experience", "education", "certifications", "skills"],
        }
        assert side_map == {
            "main": ["summary", "experience", "education"],
            "sidebar": ["profile", "skills", "certifications"],
        }
        assert modern_map == {
            "header": ["profile"],
            "main": ["summary", "experience"],
            "secondary": ["skills", "certifications", "education"],
        }
        assert classic_map == {
            "main": ["profile", "summary", "experience", "education"],
            "secondary": ["skills", "certifications"],
        }

        # Skills relocates (structure), summary stays in main (content constant).
        assert "skills" in exec_map["main"]
        assert "skills" not in side_map["main"] and "skills" in side_map["sidebar"]
        assert "skills" not in modern_map["main"] and "skills" in modern_map["secondary"]
        for mapping in (exec_map, side_map, modern_map, classic_map):
            assert "summary" in mapping["main"]

    def test_content_identical_across_layouts(self):
        builder = TreeBuilder(_registry())
        cvm = _cvm()
        layouts = (executive_layout(), sidebar_layout(), modern_layout(), classic_layout())

        counters = [_text_counter(builder.build(cvm, _context(cvm, layout))) for layout in layouts]
        assert counters[0] == counters[1] == counters[2] == counters[3]

        summary = ("summary", "Full-stack engineer with 8 years building platforms.")
        assert all(counter[summary] == 1 for counter in counters)
        # All three jobs survive as structured fields (title/company/period).
        assert len(cvm.experience) == 3
        for counter in counters:
            assert counter[("experience", "Senior Engineer")] == 1
            assert counter[("experience", "Acme")] == 1
            assert counter[("experience", "2016 – Present")] == 1
            assert counter[("experience", "Engineer")] == 1
            assert counter[("experience", "Beta Inc")] == 1
            assert counter[("experience", "2014 – 2016")] == 1
            assert counter[("experience", "Junior Engineer")] == 1
            assert counter[("experience", "Gamma")] == 1
            assert counter[("experience", "2012 – 2014")] == 1
            assert counter[("profile", "Jane Doe")] == 1
            assert counter[("profile", "Principal Engineer")] == 1
            assert counter[("certifications", "AWS Certified")] == 1
            assert counter[("certifications", "Amazon")] == 1

    def test_cvm_unchanged_across_layouts(self):
        builder = TreeBuilder(_registry())
        cvm = _cvm()
        hash_before = cvm.content_hash
        for layout in (executive_layout(), sidebar_layout(), modern_layout()):
            builder.build(cvm, _context(cvm, layout))
        assert cvm.content_hash == hash_before
        assert len(cvm.experience) == 3


# ── Basic build behaviour ─────────────────────────────────────────────────────


class TestBuild:
    def test_build_produces_valid_document(self):
        builder = TreeBuilder(_registry())
        cvm = _cvm()
        document = builder.build(cvm, _context(cvm, executive_layout()))
        assert document.kind is NodeKind.DOCUMENT
        assert TreeValidator().is_valid(document)
        page = document.children[0]
        assert page.kind is NodeKind.PAGE
        assert page.page_size.id == "A4"

    def test_sections_without_component_are_omitted(self):
        cvm = ContentView(
            stable_id="resume.min",
            profile=Profile(full_name="No Skills"),
            languages=(LanguageEntry(name="English", proficiency="Native"),),
        )
        builder = TreeBuilder(_registry())
        document = builder.build(cvm, _context(cvm, sidebar_layout()))
        assert "languages" not in _region_sections(document)["sidebar"]

    def test_deterministic_build(self):
        builder = TreeBuilder(_registry())
        cvm = _cvm()
        a = builder.build(cvm, _context(cvm, sidebar_layout()))
        b = builder.build(cvm, _context(cvm, sidebar_layout()))
        assert a.model_dump_json() == b.model_dump_json()

    def test_build_is_thread_safe(self):
        builder = TreeBuilder(_registry())
        cvm = _cvm()

        def build(_: int) -> str:
            return builder.build(cvm, _context(cvm, sidebar_layout())).model_dump_json()

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(build, range(16)))
        assert len(set(results)) == 1

    def test_context_not_mutated_by_build(self):
        cvm = _cvm()
        context = _context(cvm, sidebar_layout())
        before = context.model_dump_json()
        TreeBuilder(_registry()).build(cvm, context)
        assert context.model_dump_json() == before


# ── Invalid / incompatible layout ─────────────────────────────────────────────


class TestInvalidLayout:
    def test_incompatible_layout_rejected_cleanly(self):
        # A layout requiring a newer engine than the context target is rejected
        # at RenderContext construction, so the builder never sees it.
        layout = executive_layout().model_copy(
            update={
                "metadata": executive_layout().metadata.model_copy(
                    update={"engine_version": LayoutVersion(major=2, minor=0, patch=0)}
                )
            }
        )
        with pytest.raises(ValidationError):
            RenderContext(layout=layout, theme=blue_theme(), engine_version=(1, 0, 0))


# ── Content reference consistency ─────────────────────────────────────────────


class TestContentReferenceConsistency:
    def test_stable_id_mismatch_rejected(self):
        builder = TreeBuilder(_registry())
        cvm = _cvm()
        context = RenderContext(
            content_ref=ContentReference(stable_id="resume.other", content_hash=cvm.content_hash),
            layout=executive_layout(),
            theme=blue_theme(),
        )
        with pytest.raises(TreeBuilderError):
            builder.build(cvm, context)

    def test_hash_mismatch_rejected(self):
        builder = TreeBuilder(_registry())
        cvm = _cvm()
        context = RenderContext(
            content_ref=ContentReference(stable_id=cvm.stable_id, content_hash="f" * 64),
            layout=executive_layout(),
            theme=blue_theme(),
        )
        with pytest.raises(TreeBuilderError):
            builder.build(cvm, context)

    def test_no_content_ref_allowed(self):
        builder = TreeBuilder(_registry())
        cvm = _cvm()
        context = RenderContext(layout=executive_layout(), theme=blue_theme())
        document = builder.build(cvm, context)
        assert document.kind is NodeKind.DOCUMENT


# ── Architecture: builder is not coupled to renderers/preview ─────────────────


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


class TestArchitectureIndependence:
    def test_builder_does_not_import_renderers_or_preview(self):
        imports = _module_imports("app.rendering.builder.builder")
        assert not _imports_package(imports, "app.rendering.renderers")
        assert not _imports_package(imports, "app.rendering.preview")
        assert not _imports_package(imports, "app.rendering.theme.theme_registry")

    def test_builder_is_composition_point(self):
        imports = _module_imports("app.rendering.builder.builder")
        assert _imports_package(imports, "app.rendering.components")
        assert _imports_package(imports, "app.rendering.content")
        assert _imports_package(imports, "app.rendering.context")
        assert _imports_package(imports, "app.rendering.layout")
        assert _imports_package(imports, "app.rendering.tree")
