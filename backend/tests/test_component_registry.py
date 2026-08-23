"""Tests for the section component registry (Layout Engine, Phase 0)."""

import concurrent.futures

import pytest
from pydantic import ValidationError

from app.rendering.components import (
    ComponentLookupError,
    ComponentMetadata,
    ComponentRegistrationError,
    ComponentRegistry,
    ComponentValidationResult,
    EducationComponent,
    ExperienceComponent,
    SkillsComponent,
    SummaryComponent,
)
from app.rendering.tree import NodeKind


def _default_registry() -> ComponentRegistry:
    registry = ComponentRegistry()
    for component in (SummaryComponent(), ExperienceComponent(), EducationComponent(), SkillsComponent()):
        registry.register(component)
    return registry


# ── Registration ──────────────────────────────────────────────────────────────


class TestRegistration:
    def test_register_and_has(self):
        registry = ComponentRegistry()
        registry.register(SummaryComponent())
        assert registry.has("summary")
        assert "summary" in registry

    def test_register_all_reference_components(self):
        registry = _default_registry()
        assert len(registry) == 4
        assert set(registry.list()) == {"summary", "experience", "education", "skills"}

    def test_unregister_removes_component(self):
        registry = _default_registry()
        removed = registry.unregister("summary")
        assert isinstance(removed, SummaryComponent)
        assert not registry.has("summary")
        assert registry.unregister("summary") is None

    def test_register_returns_none(self):
        registry = ComponentRegistry()
        assert registry.register(SummaryComponent()) is None


# ── Duplicate handling & replacement policy ───────────────────────────────────


class TestDuplicates:
    def test_duplicate_rejected_by_default(self):
        registry = ComponentRegistry()
        registry.register(SummaryComponent())
        with pytest.raises(ComponentRegistrationError):
            registry.register(SummaryComponent())

    def test_duplicate_rejected_even_for_different_impl(self):
        registry = ComponentRegistry()

        class OtherSummary(SummaryComponent):
            pass

        registry.register(SummaryComponent())
        with pytest.raises(ComponentRegistrationError):
            registry.register(OtherSummary())

    def test_replacement_allowed_at_registry_level(self):
        registry = ComponentRegistry(allow_replacement=True)
        registry.register(SummaryComponent())
        registry.register(ExperienceComponent())
        registry.register(SummaryComponent())  # replaces
        assert isinstance(registry.resolve("summary"), SummaryComponent)
        assert len(registry) == 2

    def test_replacement_allowed_per_call(self):
        registry = ComponentRegistry()  # registry-level: reject
        registry.register(SummaryComponent())
        registry.register(SummaryComponent(), allow_replacement=True)  # per-call: allow
        assert len(registry) == 1

    def test_replacement_keeps_original_position(self):
        registry = ComponentRegistry(allow_replacement=True)
        registry.register(SummaryComponent())
        registry.register(ExperienceComponent())
        registry.register(SummaryComponent())
        assert registry.list() == ("summary", "experience")


# ── Lookup ────────────────────────────────────────────────────────────────────


class TestLookup:
    def test_resolve_returns_component(self):
        registry = _default_registry()
        assert isinstance(registry.resolve("experience"), ExperienceComponent)

    def test_resolve_missing_raises(self):
        registry = _default_registry()
        with pytest.raises(ComponentLookupError):
            registry.resolve("awards")

    def test_get_returns_none_for_missing(self):
        registry = _default_registry()
        assert registry.get("awards") is None

    def test_contains_for_unknown_type(self):
        registry = _default_registry()
        assert "awards" not in registry
        assert 123 not in registry


# ── Ordering ──────────────────────────────────────────────────────────────────


class TestOrdering:
    def test_iteration_order_is_registration_order(self):
        registry = ComponentRegistry()
        registry.register(EducationComponent())
        registry.register(SummaryComponent())
        registry.register(SkillsComponent())
        assert registry.list() == ("education", "summary", "skills")

    def test_order_is_deterministic(self):
        registry = _default_registry()
        assert registry.list() == registry.list()
        assert list(registry) == list(registry.list())


# ── Metadata ──────────────────────────────────────────────────────────────────


class TestMetadata:
    def test_metadata_is_retrievable(self):
        registry = _default_registry()
        metadata = registry.metadata_map()["skills"]
        assert metadata.section_type == "skills"
        assert metadata.name == "Skills"
        assert metadata.ats_safe is True

    def test_metadata_is_immutable(self):
        metadata = SummaryComponent().metadata()
        with pytest.raises(ValidationError):
            metadata.name = "Changed"

    def test_metadata_map_is_immutable(self):
        registry = _default_registry()
        metadata_map = registry.metadata_map()
        with pytest.raises(TypeError):
            metadata_map["new"] = SummaryComponent().metadata()

    def test_metadata_map_reflects_current_components(self):
        registry = _default_registry()
        assert set(registry.metadata_map()) == {"summary", "experience", "education", "skills"}


# ── Registry immutability of returned collections ─────────────────────────────


class TestCollectionImmutability:
    def test_components_returns_immutable_tuple(self):
        registry = _default_registry()
        components = registry.components()
        assert isinstance(components, tuple)
        assert len(components) == 4

    def test_list_returns_immutable_tuple(self):
        registry = _default_registry()
        listing = registry.list()
        with pytest.raises(AttributeError):
            listing.append("x")  # type: ignore[attr-defined]


# ── Rejected registrations ────────────────────────────────────────────────────


class TestRejectedRegistrations:
    def test_rejects_non_component(self):
        registry = ComponentRegistry()
        with pytest.raises(ComponentRegistrationError):
            registry.register("summary")  # type: ignore[arg-type]
        with pytest.raises(ComponentRegistrationError):
            registry.register(object())  # type: ignore[arg-type]

    def test_rejects_broken_metadata(self):
        registry = ComponentRegistry()

        class Broken(SummaryComponent):
            def metadata(self) -> ComponentMetadata:  # type: ignore[override]
                raise RuntimeError("boom")

        with pytest.raises(ComponentRegistrationError):
            registry.register(Broken())

    def test_rejects_empty_section_type(self):
        registry = ComponentRegistry()

        class Empty(SummaryComponent):
            def section_type(self) -> str:
                return ""

        with pytest.raises(ComponentRegistrationError):
            registry.register(Empty())

    def test_rejects_metadata_mismatch(self):
        registry = ComponentRegistry()

        class Lying(SummaryComponent):
            def section_type(self) -> str:
                return "not-summary"

        with pytest.raises(ComponentRegistrationError):
            registry.register(Lying())


# ── Reference components ──────────────────────────────────────────────────────


class TestReferenceComponents:
    @pytest.mark.parametrize(
        "component,section_type",
        [
            (SummaryComponent(), "summary"),
            (ExperienceComponent(), "experience"),
            (EducationComponent(), "education"),
            (SkillsComponent(), "skills"),
        ],
    )
    def test_section_type_and_metadata(self, component, section_type):
        assert component.section_type() == section_type
        assert component.metadata().section_type == section_type
        assert component.metadata().name != ""

    def test_validate_input_returns_result(self):
        result = SummaryComponent().validate_input({"summary": "Hello"})
        assert isinstance(result, ComponentValidationResult)
        assert result.valid is True

    def test_build_render_nodes_returns_section(self):
        node = ExperienceComponent().build_render_nodes(
            {"company": "Acme"}, region="main", order=2
        )
        assert node.kind is NodeKind.SECTION
        assert node.content_ref == "experience"
        assert node.region == "main"
        assert node.order == 2
        assert node.children[0].kind is NodeKind.BLOCK
        assert node.children[0].children[0].kind is NodeKind.TEXT

    def test_build_render_nodes_extracts_text(self):
        node = SummaryComponent().build_render_nodes({"summary": "Professional engineer."})
        text = node.children[0].children[0].data
        assert text is not None
        assert text.text == "Professional engineer."

    def test_skills_without_category_fall_back_to_plain_bullets(self):
        node = SkillsComponent().build_render_nodes(
            {"skills": [{"skills": ("Python", "Go")}]}, region="main", order=0
        )
        bullets = [
            leaf
            for block in node.children[0].children
            for leaf in block.children
            if leaf.kind is NodeKind.BULLET
        ]
        assert [leaf.data.text for leaf in bullets] == ["Python", "Go"]
        assert all(not getattr(leaf.data, "runs", None) for leaf in bullets)


# ── Thread safety ─────────────────────────────────────────────────────────────


class TestThreadSafety:
    def test_concurrent_reads_are_safe(self):
        registry = _default_registry()
        errors = []

        def read_loop(_: int) -> None:
            try:
                for _ in range(200):
                    registry.resolve("summary")
                    registry.has("experience")
                    registry.list()
                    registry.metadata_map()
                    len(registry)
            except Exception as exc:  # pragma: no cover - failure surfaces below
                errors.append(exc)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(read_loop, range(8)))

        assert errors == []

    def test_concurrent_register_and_read(self):
        registry = ComponentRegistry()

        def register_worker(_: int) -> None:
            try:
                registry.register(SummaryComponent())
            except ComponentRegistrationError:
                pass  # expected when another worker wins

        def read_worker(_: int) -> None:
            for _ in range(200):
                registry.has("summary")
                registry.list()

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(register_worker, range(4)))
            list(pool.map(read_worker, range(4)))

        assert registry.has("summary")
        assert len(registry) == 1
