"""Tests for the shared section vocabulary (Layout Engine, Phase 0)."""

import concurrent.futures

import pytest
from pydantic import ValidationError

from app.rendering.common.section_types import (
    CORE_ORIGIN,
    SECTION_REGISTRY,
    VOCABULARY_VERSION,
    SectionCategory,
    SectionDefinition,
    SectionRegistrationError,
    SectionRegistry,
    SectionType,
    SectionUnknownError,
)
from app.rendering.components import (
    EducationComponent,
    ExperienceComponent,
    SkillsComponent,
    SummaryComponent,
)


def _plugin_def(
    section_type: str = "acme.certifications",
    stable_id: str = "acme.certifications.v1",
    name: str = "Acme Certifications",
    origin: str = "acme",
) -> SectionDefinition:
    return SectionDefinition(
        section_type=section_type,
        stable_id=stable_id,
        display_name=name,
        category=SectionCategory.MAIN,
        default_order=65,
        ats_priority=70,
        supports_badges=True,
        plugin_origin=origin,
    )


def _fresh_registry(allow_replacement: bool = False) -> SectionRegistry:
    return SectionRegistry(allow_replacement=allow_replacement)


# ── SectionType enum ──────────────────────────────────────────────────────────


class TestSectionTypeEnum:
    def test_required_members_present(self):
        expected = {
            "summary", "profile", "experience", "education", "projects", "skills",
            "certifications", "awards", "publications", "patents", "languages",
            "volunteer", "interests", "references", "portfolio", "header", "footer",
            "cover_letter", "custom",
        }
        assert {s.value for s in SectionType} == expected

    def test_enum_values_are_unique(self):
        values = [s.value for s in SectionType]
        assert len(values) == len(set(values))


# ── Stable ids & definitions ──────────────────────────────────────────────────


class TestStableIds:
    def test_core_sections_have_permanent_stable_ids(self):
        for section in SectionType:
            definition = SECTION_REGISTRY.lookup(section)
            assert definition.stable_id == f"section.{section.value}.v1"

    def test_example_stable_ids(self):
        assert SECTION_REGISTRY.lookup("summary").stable_id == "section.summary.v1"
        assert SECTION_REGISTRY.lookup("profile").stable_id == "section.profile.v1"
        assert SECTION_REGISTRY.lookup("experience").stable_id == "section.experience.v1"
        assert SECTION_REGISTRY.lookup("education").stable_id == "section.education.v1"
        assert SECTION_REGISTRY.lookup("skills").stable_id == "section.skills.v1"

    def test_core_plugin_origin(self):
        for section in SectionType:
            assert SECTION_REGISTRY.lookup(section).plugin_origin == CORE_ORIGIN

    def test_every_definition_exposes_required_fields(self):
        required = {
            "section_type", "stable_id", "display_name", "category", "default_order",
            "ats_priority", "visible_by_default", "supports_sidebar", "supports_timeline",
            "supports_metrics", "supports_photo", "supports_badges", "supports_multicolumn",
            "supports_multiple", "plugin_origin", "version",
        }
        for definition in SECTION_REGISTRY.definitions():
            for field in required:
                assert hasattr(definition, field)


class TestDefinitionImmutability:
    def test_definition_is_frozen(self):
        definition = SECTION_REGISTRY.lookup("summary")
        with pytest.raises(ValidationError):
            definition.display_name = "Changed"

    def test_canonical_id(self):
        assert SECTION_REGISTRY.lookup("summary").canonical_id == "summary"

    def test_stable_id_derived_when_omitted(self):
        definition = SectionDefinition(section_type=SectionType.SUMMARY, display_name="S")
        assert definition.stable_id == "section.summary.v1"


# ── Lookup ────────────────────────────────────────────────────────────────────


class TestLookup:
    def test_lookup_by_enum(self):
        assert SECTION_REGISTRY.lookup(SectionType.SUMMARY).stable_id == "section.summary.v1"

    def test_lookup_by_value_string(self):
        assert SECTION_REGISTRY.lookup("summary").display_name == "Professional Summary"

    def test_lookup_by_stable_id(self):
        definition = SECTION_REGISTRY.lookup_by_id("section.experience.v1")
        assert definition.canonical_id == "experience"

    def test_lookup_missing_raises(self):
        with pytest.raises(SectionUnknownError):
            SECTION_REGISTRY.lookup("nope")

    def test_lookup_by_id_missing_raises(self):
        with pytest.raises(SectionUnknownError):
            SECTION_REGISTRY.lookup_by_id("nope.v1")

    def test_get_returns_none_for_missing(self):
        assert SECTION_REGISTRY.get("nope") is None

    def test_contains(self):
        assert SECTION_REGISTRY.contains("summary")
        assert SECTION_REGISTRY.contains(SectionType.SKILLS)
        assert not SECTION_REGISTRY.contains("nope")
        assert "summary" in SECTION_REGISTRY


# ── Ordering / metadata access ────────────────────────────────────────────────


class TestOrdering:
    def test_ordered_sorts_by_default_order(self):
        ordered = SECTION_REGISTRY.ordered()
        orders = [d.default_order for d in ordered]
        assert orders == sorted(orders)
        assert ordered[0].canonical_id == "header"

    def test_list_is_deterministic(self):
        assert SECTION_REGISTRY.list() == SECTION_REGISTRY.list()

    def test_metadata_map_is_immutable(self):
        with pytest.raises(TypeError):
            SECTION_REGISTRY.metadata_map()["x"] = _plugin_def()

    def test_metadata_map_keyed_by_stable_id(self):
        metadata_map = SECTION_REGISTRY.metadata_map()
        assert "section.summary.v1" in metadata_map


# ── Validation ────────────────────────────────────────────────────────────────


class TestValidation:
    def test_validate_passes_for_known(self):
        SECTION_REGISTRY.validate("summary")

    def test_validate_raises_for_unknown(self):
        with pytest.raises(SectionUnknownError):
            SECTION_REGISTRY.validate("nope")

    def test_is_valid(self):
        assert SECTION_REGISTRY.is_valid("skills") is True
        assert SECTION_REGISTRY.is_valid("nope") is False


# ── Serialization ─────────────────────────────────────────────────────────────


class TestSerialization:
    def test_round_trip(self):
        definition = SECTION_REGISTRY.lookup("summary")
        restored = SectionDefinition.model_validate_json(definition.model_dump_json())
        assert restored == definition
        assert restored.stable_id == "section.summary.v1"


# ── Plugin readiness ──────────────────────────────────────────────────────────


class TestPluginExtension:
    def test_register_plugin_definition(self):
        registry = _fresh_registry()
        registry.register(_plugin_def())
        assert registry.contains("acme.certifications")
        assert registry.lookup_by_id("acme.certifications.v1").display_name == "Acme Certifications"
        assert registry.lookup("acme.certifications").plugin_origin == "acme"

    def test_plugin_definition_carries_full_metadata(self):
        registry = _fresh_registry()
        registry.register(_plugin_def())
        definition = registry.lookup("acme.certifications")
        assert definition.ats_priority == 70
        assert definition.supports_badges is True

    def test_plugin_included_in_listing_and_ordered(self):
        registry = _fresh_registry()
        registry.register(_plugin_def())
        assert "acme.certifications.v1" in registry.list()
        assert any(d.canonical_id == "acme.certifications" for d in registry.ordered())

    def test_duplicate_section_type_rejected(self):
        registry = _fresh_registry()
        registry.register(_plugin_def())
        with pytest.raises(SectionRegistrationError):
            registry.register(_plugin_def(stable_id="acme.certifications.v2"))

    def test_duplicate_stable_id_rejected(self):
        registry = _fresh_registry()
        registry.register(_plugin_def())
        with pytest.raises(SectionRegistrationError):
            registry.register(_plugin_def(section_type="acme.certs", stable_id="acme.certifications.v1"))

    def test_plugin_replacement_allowed_when_enabled(self):
        registry = _fresh_registry(allow_replacement=True)
        registry.register(_plugin_def())
        registry.register(_plugin_def(name="Renamed"))
        assert registry.lookup("acme.certifications").display_name == "Renamed"

    def test_core_section_cannot_be_replaced(self):
        for registry in (_fresh_registry(), _fresh_registry(allow_replacement=True)):
            with pytest.raises(SectionRegistrationError):
                registry.register(_plugin_def(section_type="summary", stable_id="section.summary.v1"))

    def test_core_collision_rejected(self):
        registry = _fresh_registry()
        with pytest.raises(SectionRegistrationError):
            registry.register(_plugin_def(section_type="acme.summary", stable_id="section.summary.v1"))
        with pytest.raises(SectionRegistrationError):
            registry.register(_plugin_def(section_type="summary", stable_id="acme.summary.v1"))

    def test_invalid_plugin_section_type_rejected(self):
        registry = _fresh_registry()
        for bad in ("NoDot", "1start", "bad space", "UPPER.Case"):
            with pytest.raises(ValidationError):
                registry.register(_plugin_def(section_type=bad))

    def test_empty_identifiers_rejected(self):
        with pytest.raises(ValidationError):
            SectionDefinition(section_type="acme.x", display_name="X", stable_id="   ")
        with pytest.raises(ValidationError):
            SectionDefinition(section_type="", display_name="X", stable_id="acme.x.v1")

    def test_invalid_metadata_rejected(self):
        with pytest.raises(ValidationError):
            SectionDefinition(section_type="acme.x", display_name="")

    def test_non_definition_rejected(self):
        registry = _fresh_registry()
        with pytest.raises(SectionRegistrationError):
            registry.register(object())  # type: ignore[arg-type]

    def test_plugin_does_not_touch_core(self):
        registry = _fresh_registry()
        registry.register(_plugin_def())
        assert registry.core_ids() == SECTION_REGISTRY.core_ids()
        assert SECTION_REGISTRY.get("acme.certifications") is None


# ── Backward compatibility ────────────────────────────────────────────────────


class TestBackwardCompatibility:
    def test_reference_component_types_are_valid_sections(self):
        for component in (SummaryComponent(), ExperienceComponent(), EducationComponent(), SkillsComponent()):
            assert SECTION_REGISTRY.is_valid(component.section_type())

    def test_vocabulary_version_is_semantic(self):
        parts = VOCABULARY_VERSION.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)


# ── Thread safety ─────────────────────────────────────────────────────────────


class TestThreadSafety:
    def test_concurrent_plugin_registration_and_reads(self):
        registry = _fresh_registry()
        errors: list[Exception] = []

        def worker(i: int) -> None:
            try:
                registry.register(_plugin_def(section_type=f"acme.s{i}", stable_id=f"acme.s{i}.v1"))
            except SectionRegistrationError:
                pass

        def reader(_: int) -> None:
            for _ in range(100):
                registry.contains("summary")
                registry.list()
                registry.ordered()
                registry.metadata_map()

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(worker, range(4)))
            list(pool.map(reader, range(4)))

        assert errors == []
        assert registry.contains("acme.s0")
