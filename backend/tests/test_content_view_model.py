"""Tests for the Content View Model (Layout Engine, Phase 0)."""

import ast
import importlib
import inspect
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.models.resume import Certification as ResumeCertification
from app.models.resume import Education as ResumeEducation
from app.models.resume import Experience as ResumeExperience
from app.models.resume import Project as ResumeProject
from app.models.resume import Resume
from app.models.resume import Skill as ResumeSkill
from app.rendering.common.section_types import SectionType
from app.rendering.content import ContentView, Profile, cvm_from_resume
from app.rendering.content.models import (
    AwardEntry,
    CertificationEntry,
    EducationEntry,
    ExperienceEntry,
    LanguageEntry,
    SkillGroup,
)
from app.rendering.context import ContentReference, RenderContext
from app.rendering.layout.reference_layouts import executive_layout, sidebar_layout
from app.rendering.theme.reference_themes import blue_theme


def _resume() -> Resume:
    return Resume(
        user_id="u1",
        full_name="Jane Doe",
        email="jane@test.com",
        phone="+1-555-0100",
        location="Boston, MA",
        linkedin="https://linkedin.com/in/jane",
        github="https://github.com/jane",
        website="https://jane.dev",
        summary="Full-stack engineer with 8 years of experience.",
        education=[
            ResumeEducation(
                institution="MIT", degree="B.Sc.", field="Computer Science",
                start_date="2012", end_date="2016", gpa=3.8,
                achievements=["Dean's List"],
            )
        ],
        experience=[
            ResumeExperience(
                company="Acme", title="Senior Engineer", location="Boston",
                start_date="2016", current=True, description=["Led platform team"],
            ),
            ResumeExperience(
                company="Beta Inc", title="Engineer", location="Remote",
                start_date="2014", end_date="2016", description=["Built APIs"],
            ),
        ],
        projects=[
            ResumeProject(name="OpenMetrics", description="Metrics platform", url="https://github.com/jane/om", technologies=["Go", "React"]),
        ],
        skills=[
            ResumeSkill(category="Languages", skills=["Python", "Go"]),
            ResumeSkill(category="Frontend", skills=["React", "TypeScript"]),
        ],
        certifications=[ResumeCertification(name="AWS Certified", issuer="Amazon", date="2021")],
    )


def _rich_cvm() -> ContentView:
    return ContentView(
        stable_id="resume.abc",
        profile=Profile(full_name="Jane Doe", professional_title="Principal Engineer", email="jane@test.com"),
        summary="8 years building platforms.",
        experience=(
            ExperienceEntry(company="Acme", title="Senior Engineer", start_date="2016", current=True, description=("Led platform",)),
            ExperienceEntry(company="Beta", title="Engineer", start_date="2014", end_date="2016", description=("Built APIs",)),
            ExperienceEntry(company="Gamma", title="Junior", start_date="2012", end_date="2014", description=("Shipped features",)),
        ),
        education=(EducationEntry(institution="MIT", degree="B.Sc."),),
        skills=(SkillGroup(category="Languages", skills=("Python", "Go")),),
        certifications=(CertificationEntry(name="AWS", issuer="Amazon"),),
        awards=(AwardEntry(title="Employee of the Year", issuer="Acme"),),
        languages=(LanguageEntry(name="English", proficiency="Native"),),
    )


# ── Construction & required fields ────────────────────────────────────────────


class TestConstruction:
    def test_minimal_cvm(self):
        cvm = ContentView(stable_id="resume.x", profile=Profile(full_name="Jane Doe"))
        assert cvm.profile.full_name == "Jane Doe"
        assert cvm.experience == ()

    def test_stable_id_required(self):
        with pytest.raises(ValidationError):
            ContentView(profile=Profile(full_name="Jane"))  # type: ignore[call-arg]

    def test_profile_full_name_required(self):
        with pytest.raises(ValidationError):
            Profile(full_name="")

    def test_rich_cvm(self):
        cvm = _rich_cvm()
        assert len(cvm.experience) == 3
        assert cvm.languages[0].name == "English"


# ── Validation ────────────────────────────────────────────────────────────────


class TestValidation:
    def test_gpa_out_of_range_rejected(self):
        with pytest.raises(ValidationError):
            EducationEntry(institution="X", degree="B.Sc.", gpa=4.5)

    def test_section_order_unknown_rejected(self):
        with pytest.raises(ValidationError):
            ContentView(stable_id="x", profile=Profile(full_name="A"), section_order=("bogus",))

    def test_section_order_non_cvm_section_rejected(self):
        with pytest.raises(ValidationError):
            ContentView(stable_id="x", profile=Profile(full_name="A"), section_order=(SectionType.PUBLICATIONS.value,))


# ── Immutability ──────────────────────────────────────────────────────────────


class TestImmutability:
    def test_cvm_is_frozen(self):
        cvm = _rich_cvm()
        with pytest.raises(ValidationError):
            cvm.summary = "changed"

    def test_nested_sections_are_frozen(self):
        cvm = _rich_cvm()
        with pytest.raises(ValidationError):
            cvm.experience[0].title = "changed"
        with pytest.raises(ValidationError):
            cvm.profile.full_name = "changed"


# ── Stable identifiers ────────────────────────────────────────────────────────


class TestStableIdentifiers:
    def test_content_hash_is_hex_and_stable(self):
        cvm = _rich_cvm()
        assert len(cvm.content_hash) == 64
        assert cvm.content_hash == cvm.content_hash

    def test_content_hash_changes_with_content(self):
        a = _rich_cvm()
        b = _rich_cvm().model_copy(update={"summary": "different summary"})
        assert a.content_hash != b.content_hash

    def test_content_hash_ignores_stable_id(self):
        a = _rich_cvm()
        b = _rich_cvm().model_copy(update={"stable_id": "resume.other"})
        assert a.content_hash == b.content_hash

    def test_stable_id_preserved(self):
        assert _rich_cvm().stable_id == "resume.abc"


# ── Deterministic serialization ───────────────────────────────────────────────


class TestSerialization:
    def test_deterministic_json(self):
        assert _rich_cvm().model_dump_json() == _rich_cvm().model_dump_json()

    def test_round_trip(self):
        cvm = _rich_cvm()
        restored = ContentView.model_validate_json(cvm.model_dump_json())
        assert restored == cvm

    def test_stable_ids_in_serialization(self):
        assert "resume.abc" in _rich_cvm().model_dump_json()


# ── Section ordering ──────────────────────────────────────────────────────────


class TestSectionOrdering:
    def test_default_order_derived_and_sorted(self):
        cvm = ContentView(
            stable_id="x",
            profile=Profile(full_name="Jane"),
            summary="s",
            experience=(ExperienceEntry(company="A", title="T"),),
            education=(EducationEntry(institution="I", degree="D"),),
            skills=(SkillGroup(category="C", skills=("s",)),),
            certifications=(CertificationEntry(name="N"),),
        )
        order = cvm.section_order
        assert "summary" in order and "experience" in order
        # sorted by vocabulary default_order: profile < summary < experience < education < certifications < skills
        assert order.index("profile") < order.index("summary") < order.index("experience")
        assert order.index("experience") < order.index("education")
        assert order.index("education") < order.index("certifications")
        assert order.index("certifications") < order.index("skills")

    def test_explicit_section_order_preserved(self):
        cvm = ContentView(
            stable_id="x",
            profile=Profile(full_name="Jane"),
            experience=(ExperienceEntry(company="A", title="T"),),
            section_order=("experience", "profile"),
        )
        assert cvm.section_order == ("experience", "profile")


# ── Empty / optional sections ─────────────────────────────────────────────────


class TestEmptyOptionalSections:
    def test_profile_only(self):
        cvm = ContentView(stable_id="x", profile=Profile(full_name="Jane"))
        assert cvm.present_sections() == ("profile",)
        assert cvm.section_order == ("profile",)

    def test_empty_sections_not_present(self):
        cvm = _rich_cvm()
        assert cvm.present_sections() == cvm.section_order

    def test_section_content_accessor(self):
        cvm = _rich_cvm()
        assert cvm.section_content("summary") == "8 years building platforms."
        assert cvm.section_content("experience") == cvm.experience
        assert cvm.section_content("nope") is None

    def test_has_section(self):
        cvm = _rich_cvm()
        assert cvm.has_section("languages") is True
        assert cvm.has_section("projects") is False
        assert cvm.has_section("nope") is False


# ── Preservation of source content ────────────────────────────────────────────


class TestSourcePreservation:
    def test_cvm_from_resume_preserves_content(self):
        resume = _resume()
        cvm = cvm_from_resume(resume, stable_id="resume.r1")
        assert cvm.profile.full_name == "Jane Doe"
        assert cvm.profile.email == "jane@test.com"
        assert cvm.summary == resume.summary
        assert [e.company for e in cvm.experience] == ["Acme", "Beta Inc"]
        assert cvm.experience[0].current is True
        assert cvm.experience[1].end_date == "2016"
        assert cvm.education[0].gpa == 3.8
        assert cvm.education[0].achievements == ("Dean's List",)
        assert [s.category for s in cvm.skills] == ["Languages", "Frontend"]
        assert cvm.skills[0].skills == ("Python", "Go")
        assert cvm.projects[0].name == "OpenMetrics"
        assert cvm.certifications[0].name == "AWS Certified"

    def test_cvm_from_resume_stable_id(self):
        resume = _resume()
        assert cvm_from_resume(resume, stable_id="r1").stable_id == "resume.r1"
        assert cvm_from_resume(resume).stable_id.startswith("resume.")


# ── Same CVM across materially different layouts (acceptance) ─────────────────


class TestLayoutIndependence:
    def test_layouts_are_materially_different(self):
        exec_regions = [(r.identifier, r.column_span) for r in executive_layout().regions]
        side_regions = [(r.identifier, r.column_span) for r in sidebar_layout().regions]
        assert exec_regions == [("header", 12), ("main", 12)]
        assert side_regions == [("header", 12), ("main", 7), ("sidebar", 5)]

    def test_same_cvm_accepted_by_two_layouts(self):
        cvm = _rich_cvm()
        ref = ContentReference(stable_id=cvm.stable_id, content_hash=cvm.content_hash)

        exec_context = RenderContext(content_ref=ref, layout=executive_layout(), theme=blue_theme())
        side_context = RenderContext(content_ref=ref, layout=sidebar_layout(), theme=blue_theme())

        assert exec_context.layout_stable_id == "layout.executive.v1"
        assert side_context.layout_stable_id == "layout.sidebar.v1"
        # The content is unchanged and identical for both.
        assert exec_context.content_ref.content_hash == cvm.content_hash
        assert side_context.content_ref.content_hash == cvm.content_hash
        assert exec_context.content_ref.stable_id == side_context.content_ref.stable_id == "resume.abc"

    def test_changing_only_layout_leaves_cvm_unchanged(self):
        cvm = _rich_cvm()
        hash_before = cvm.content_hash
        RenderContext(
            content_ref=ContentReference(stable_id=cvm.stable_id, content_hash=cvm.content_hash),
            layout=executive_layout(),
            theme=blue_theme(),
        )
        RenderContext(
            content_ref=ContentReference(stable_id=cvm.stable_id, content_hash=cvm.content_hash),
            layout=sidebar_layout(),
            theme=blue_theme(),
        )
        assert cvm.content_hash == hash_before


# ── No layout/theme/renderer leakage into CVM ─────────────────────────────────


class TestNoLeakage:
    def test_cvm_fields_are_content_only(self):
        expected = {
            "stable_id", "profile", "summary", "experience", "education", "skills",
            "certifications", "projects", "awards", "languages", "section_order",
        }
        assert set(ContentView.model_fields) == expected

    def test_no_layout_or_theme_field_names(self):
        fields = set(ContentView.model_fields)
        forbidden = {
            "columns", "regions", "placement", "sidebar", "header", "grid",
            "page", "margins", "theme", "colors", "typography", "spacing",
            "capabilities", "atomics", "renderer",
        }
        assert fields.isdisjoint(forbidden)


# ── Architecture: CVM is not coupled to registries/renderers/services ─────────


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
    def test_cvm_models_not_coupled_to_rendering_registries(self):
        imports = _module_imports("app.rendering.content.models")
        for forbidden in (
            "app.rendering.layout",
            "app.rendering.theme",
            "app.rendering.context",
            "app.rendering.components",
            "app.rendering.tree",
            "app.services",
            "app.models.resume",
        ):
            assert not _imports_package(imports, forbidden), forbidden

    def test_cvm_models_use_section_vocabulary(self):
        imports = _module_imports("app.rendering.content.models")
        assert _imports_package(imports, "app.rendering.common")

    def test_builder_imports_source_model_only_for_adapter(self):
        imports = _module_imports("app.rendering.content.builders")
        assert not _imports_package(imports, "app.rendering.layout")
        assert not _imports_package(imports, "app.rendering.theme")
        assert not _imports_package(imports, "app.rendering.context")
