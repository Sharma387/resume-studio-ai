"""Tests for the Layout Registry (Layout Engine, Phase 0)."""

import concurrent.futures

import pytest
from pydantic import ValidationError

from app.rendering.layout import (
    REFERENCE_LAYOUTS,
    LayoutCapabilities,
    LayoutDefinition,
    LayoutLookupError,
    LayoutMetadata,
    LayoutRegistrationError,
    LayoutRegistry,
    LayoutVersion,
    PlacementRule,
    RegionDefinition,
    RegionType,
)


def _main(span: int = 12) -> RegionDefinition:
    return RegionDefinition(
        identifier="main",
        display_name="Main",
        region_type=RegionType.MAIN,
        column_span=span,
        required=True,
    )


def _meta(layout_id: str = "test", **overrides) -> LayoutMetadata:
    base = dict(
        layout_id=layout_id,
        stable_id=f"layout.{layout_id}.v1",
        display_name="Test Layout",
        version=LayoutVersion(major=1, minor=0, patch=0),
        api_version=LayoutVersion(major=1, minor=0, patch=0),
        engine_version=LayoutVersion(major=1, minor=0, patch=0),
    )
    base.update(overrides)
    return LayoutMetadata(**base)


def _definition(metadata: LayoutMetadata | None = None, **overrides) -> LayoutDefinition:
    base = dict(metadata=metadata or _meta(), capabilities=LayoutCapabilities(), regions=(_main(),))
    base.update(overrides)
    return LayoutDefinition(**base)


def _fresh_registry(**kwargs) -> LayoutRegistry:
    return LayoutRegistry(**kwargs)


# ── Semantic versions ─────────────────────────────────────────────────────────


class TestLayoutVersion:
    def test_parse_valid(self):
        version = LayoutVersion.parse("1.2.3")
        assert (version.major, version.minor, version.patch) == (1, 2, 3)
        assert str(version) == "1.2.3"

    @pytest.mark.parametrize("value", ["abc", "1.2", "1.2.3.4", "1..3", ""])
    def test_parse_invalid(self, value):
        with pytest.raises(ValueError):
            LayoutVersion.parse(value)

    def test_ordering(self):
        assert LayoutVersion(major=1, minor=0, patch=0) < LayoutVersion(major=1, minor=0, patch=1)
        assert LayoutVersion(major=1, minor=1, patch=0) < LayoutVersion(major=2, minor=0, patch=0)
        assert LayoutVersion(major=2, minor=0, patch=0) > LayoutVersion(major=1, minor=9, patch=9)
        assert LayoutVersion(major=1, minor=0, patch=0) == LayoutVersion(major=1, minor=0, patch=0)

    def test_negative_components_rejected(self):
        with pytest.raises(ValidationError):
            LayoutVersion(major=-1, minor=0, patch=0)


# ── Reference layouts ─────────────────────────────────────────────────────────


class TestReferenceLayouts:
    def test_six_reference_layouts(self):
        assert len(REFERENCE_LAYOUTS) == 6
        names = {layout.layout_id for layout in REFERENCE_LAYOUTS}
        assert names == {"executive", "modern", "sidebar", "timeline", "classic", "minimal"}

    def test_stable_ids_are_versioned(self):
        for layout in REFERENCE_LAYOUTS:
            assert layout.stable_id == f"layout.{layout.layout_id}.v1"

    def test_all_have_main_region(self):
        for layout in REFERENCE_LAYOUTS:
            assert any(region.region_type is RegionType.MAIN for region in layout.regions)

    def test_register_all_reference_layouts(self):
        registry = _fresh_registry()
        for layout in REFERENCE_LAYOUTS:
            registry.register(layout)
        assert len(registry) == 6


# ── Registration & duplicates ────────────────────────────────────────────────


class TestRegistration:
    def test_register_and_contains(self):
        registry = _fresh_registry()
        registry.register(REFERENCE_LAYOUTS[0])
        assert registry.contains("executive")
        assert "executive" in registry
        assert len(registry) == 1

    def test_duplicate_layout_id_rejected(self):
        registry = _fresh_registry()
        registry.register(REFERENCE_LAYOUTS[0])
        with pytest.raises(LayoutRegistrationError):
            registry.register(REFERENCE_LAYOUTS[0])

    def test_duplicate_stable_id_rejected(self):
        registry = _fresh_registry()
        registry.register(_definition(metadata=_meta(layout_id="a", stable_id="layout.shared.v1")))
        with pytest.raises(LayoutRegistrationError):
            registry.register(_definition(metadata=_meta(layout_id="b", stable_id="layout.shared.v1")))

    def test_replacement_at_registry_level(self):
        registry = _fresh_registry(allow_replacement=True)
        registry.register(_definition(metadata=_meta(layout_id="x", display_name="First")))
        registry.register(_definition(metadata=_meta(layout_id="x", display_name="Second")))
        assert registry.resolve("x").metadata.display_name == "Second"

    def test_replacement_per_call(self):
        registry = _fresh_registry()
        registry.register(_definition(metadata=_meta(layout_id="x", display_name="First")))
        registry.register(_definition(metadata=_meta(layout_id="x", display_name="Second")), allow_replacement=True)
        assert registry.resolve("x").metadata.display_name == "Second"

    def test_unregister(self):
        registry = _fresh_registry()
        registry.register(REFERENCE_LAYOUTS[0])
        removed = registry.unregister("executive")
        assert removed is not None
        assert not registry.contains("executive")
        assert registry.unregister("executive") is None

    def test_reject_non_definition(self):
        registry = _fresh_registry()
        with pytest.raises(LayoutRegistrationError):
            registry.register(object())  # type: ignore[arg-type]


# ── Lookup ────────────────────────────────────────────────────────────────────


class TestLookup:
    def test_resolve(self):
        registry = _fresh_registry()
        registry.register(REFERENCE_LAYOUTS[0])
        assert registry.resolve("executive").stable_id == "layout.executive.v1"

    def test_resolve_missing_raises(self):
        registry = _fresh_registry()
        with pytest.raises(LayoutLookupError):
            registry.resolve("nope")

    def test_lookup_by_stable_id(self):
        registry = _fresh_registry()
        registry.register(REFERENCE_LAYOUTS[0])
        assert registry.lookup("layout.executive.v1").layout_id == "executive"

    def test_get_returns_none_for_missing(self):
        registry = _fresh_registry()
        assert registry.get("nope") is None


# ── Ordering / metadata / immutability ────────────────────────────────────────


class TestOrderingAndMetadata:
    def test_list_is_registration_order(self):
        registry = _fresh_registry()
        registry.register(REFERENCE_LAYOUTS[0])  # executive
        registry.register(REFERENCE_LAYOUTS[2])  # sidebar
        assert registry.list() == ("executive", "sidebar")

    def test_ordered_is_deterministic(self):
        registry = _fresh_registry()
        for layout in REFERENCE_LAYOUTS:
            registry.register(layout)
        assert registry.ordered() == registry.ordered()
        stable_ids = [d.stable_id for d in registry.ordered()]
        assert stable_ids == sorted(stable_ids)

    def test_metadata_map_is_immutable(self):
        registry = _fresh_registry()
        registry.register(REFERENCE_LAYOUTS[0])
        with pytest.raises(TypeError):
            registry.metadata()["x"] = _meta("y")

    def test_metadata_map_keyed_by_layout_id(self):
        registry = _fresh_registry()
        registry.register(REFERENCE_LAYOUTS[0])
        assert "executive" in registry.metadata()
        assert registry.metadata()["executive"].stable_id == "layout.executive.v1"


class TestImmutability:
    def test_definition_is_frozen(self):
        definition = REFERENCE_LAYOUTS[0]
        with pytest.raises(ValidationError):
            definition.placement_rules = ()

    def test_metadata_is_frozen(self):
        with pytest.raises(ValidationError):
            REFERENCE_LAYOUTS[0].metadata.display_name = "Renamed"


# ── Engine compatibility gate ────────────────────────────────────────────────


class TestEngineGate:
    def test_newer_engine_rejected(self):
        registry = _fresh_registry(supported_engine_version=LayoutVersion(major=1, minor=0, patch=0))
        future = _definition(metadata=_meta(engine_version=LayoutVersion(major=2, minor=0, patch=0)))
        with pytest.raises(LayoutRegistrationError):
            registry.register(future)

    def test_compatible_engine_accepted(self):
        registry = _fresh_registry(supported_engine_version=LayoutVersion(major=2, minor=0, patch=0))
        registry.register(_definition(metadata=_meta(engine_version=LayoutVersion(major=2, minor=0, patch=0))))
        assert registry.contains("test")


# ── Definition validation ─────────────────────────────────────────────────────


class TestDefinitionValidation:
    def test_unknown_section_in_placement(self):
        with pytest.raises(ValidationError):
            _definition(placement_rules=(PlacementRule(section="bogus", preferred_region="main"),))

    def test_unknown_region_in_placement(self):
        with pytest.raises(ValidationError):
            _definition(placement_rules=(PlacementRule(section="summary", preferred_region="bogus"),))

    def test_unknown_region_in_allowed_regions(self):
        with pytest.raises(ValidationError):
            _definition(placement_rules=(PlacementRule(section="summary", allowed_regions=("nope",)),))

    def test_min_exceeds_max_occurrences(self):
        with pytest.raises(ValidationError):
            _definition(
                placement_rules=(PlacementRule(section="summary", min_occurrences=3, max_occurrences=1),)
            )

    def test_unknown_section_in_region_allowed(self):
        with pytest.raises(ValidationError):
            _definition(
                regions=(
                    RegionDefinition(
                        identifier="main",
                        display_name="Main",
                        region_type=RegionType.MAIN,
                        allowed_sections=("bogus",),
                    ),
                )
            )

    def test_duplicate_region_identifiers(self):
        with pytest.raises(ValidationError):
            _definition(regions=(_main(), _main(span=12)))

    def test_region_span_exceeds_columns(self):
        with pytest.raises(ValidationError):
            _definition(regions=(_main(span=13),))

    def test_region_span_sum_exceeds_columns(self):
        with pytest.raises(ValidationError):
            _definition(
                regions=(
                    _main(span=7),
                    RegionDefinition(
                        identifier="side",
                        display_name="Side",
                        region_type=RegionType.CUSTOM,
                        column_span=7,
                    ),
                ),
                capabilities=LayoutCapabilities(multi_column=True),
            )

    def test_missing_main_region(self):
        with pytest.raises(ValidationError):
            _definition(
                regions=(
                    RegionDefinition(
                        identifier="only",
                        display_name="Only",
                        region_type=RegionType.CUSTOM,
                    ),
                )
            )

    def test_capability_mismatch(self):
        with pytest.raises(ValidationError):
            _definition(capabilities=LayoutCapabilities(timeline=True))  # metadata.supports_timeline False

    def test_sidebar_region_requires_sidebar_capability(self):
        with pytest.raises(ValidationError):
            _definition(
                regions=(
                    _main(span=7),
                    RegionDefinition(
                        identifier="sidebar",
                        display_name="Sidebar",
                        region_type=RegionType.SIDEBAR,
                        column_span=5,
                    ),
                ),
                capabilities=LayoutCapabilities(multi_column=True),  # sidebar False
            )

    def test_multi_region_requires_multi_column(self):
        with pytest.raises(ValidationError):
            _definition(
                regions=(
                    _main(span=6),
                    RegionDefinition(
                        identifier="second",
                        display_name="Second",
                        region_type=RegionType.CUSTOM,
                        column_span=6,
                    ),
                ),
                capabilities=LayoutCapabilities(),  # multi_column False
            )

    def test_invalid_page_size(self):
        with pytest.raises(ValidationError):
            _definition(page={"page_size": "Tabloid", "margins": {"top_mm": 10}})

    def test_negative_margin(self):
        with pytest.raises(ValidationError):
            _definition(page={"page_size": "A4", "margins": {"top_mm": -5}})

    def test_unknown_recommended_section(self):
        with pytest.raises(ValidationError):
            _definition(metadata=_meta(recommended_sections=("bogus",)))


# ── Plugin readiness ──────────────────────────────────────────────────────────


class TestPluginExtension:
    def test_register_plugin_layout(self):
        registry = _fresh_registry()
        plugin = _definition(
            metadata=_meta(
                layout_id="vendor.mini",
                stable_id="layout.vendor.mini.v1",
                plugin_origin="vendor",
                display_name="Vendor Mini",
            )
        )
        registry.register(plugin)
        assert registry.contains("vendor.mini")
        assert registry.resolve("vendor.mini").metadata.plugin_origin == "vendor"

    def test_plugin_does_not_touch_reference_layouts(self):
        registry = _fresh_registry()
        for layout in REFERENCE_LAYOUTS:
            registry.register(layout)
        registry.register(
            _definition(
                metadata=_meta(
                    layout_id="vendor.mini",
                    stable_id="layout.vendor.mini.v1",
                    plugin_origin="vendor",
                )
            )
        )
        assert len(registry) == 7


# ── Thread safety ─────────────────────────────────────────────────────────────


class TestThreadSafety:
    def test_concurrent_register_and_read(self):
        registry = _fresh_registry()
        errors: list[Exception] = []

        def worker(i: int) -> None:
            try:
                registry.register(
                    _definition(metadata=_meta(layout_id=f"x{i}", stable_id=f"layout.x{i}.v1"))
                )
            except LayoutRegistrationError:
                pass

        def reader(_: int) -> None:
            for _ in range(100):
                registry.contains("executive")
                registry.list()
                registry.ordered()
                registry.metadata()

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(worker, range(4)))
            list(pool.map(reader, range(4)))

        assert errors == []
        assert registry.contains("x0")


# ── Serialization ─────────────────────────────────────────────────────────────


class TestSerialization:
    def test_round_trip(self):
        definition = REFERENCE_LAYOUTS[0]
        restored = LayoutDefinition.model_validate_json(definition.model_dump_json())
        assert restored == definition
        assert restored.stable_id == "layout.executive.v1"
