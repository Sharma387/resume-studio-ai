"""Tests for the Theme Registry (Layout Engine, Phase 0)."""

import concurrent.futures

import pytest
from pydantic import ValidationError

from app.rendering.theme import (
    REFERENCE_THEMES,
    ColorTokens,
    ThemeLookupError,
    ThemeMetadata,
    ThemePalette,
    ThemeRegistrationError,
    ThemeRegistry,
    ThemeTokens,
    ThemeVersion,
)

_BLUE = {
    "primary": "#2563eb",
    "on_primary": "#ffffff",
    "accent": "#1e40af",
    "background": "#ffffff",
    "on_background": "#1e293b",
    "text": "#1e293b",
    "muted": "#64748b",
    "border": "#e2e8f0",
    "success": "#2e7d32",
}


def _meta(theme_id: str = "test", **overrides) -> ThemeMetadata:
    base = dict(
        theme_id=theme_id,
        stable_id=f"theme.{theme_id}.v1",
        display_name="Test Theme",
        version=ThemeVersion(major=1, minor=0, patch=0),
        api_version=ThemeVersion(major=1, minor=0, patch=0),
        engine_version=ThemeVersion(major=1, minor=0, patch=0),
    )
    base.update(overrides)
    return ThemeMetadata(**base)


def _palette(metadata: ThemeMetadata | None = None, **tokens_overrides) -> ThemePalette:
    tokens = ThemeTokens(colors=ColorTokens(**_BLUE), **tokens_overrides)
    return ThemePalette(metadata=metadata or _meta(), tokens=tokens)


def _fresh_registry(**kwargs) -> ThemeRegistry:
    return ThemeRegistry(**kwargs)


# ── Semantic versions ─────────────────────────────────────────────────────────


class TestThemeVersion:
    def test_parse_valid(self):
        version = ThemeVersion.parse("1.2.3")
        assert (version.major, version.minor, version.patch) == (1, 2, 3)
        assert str(version) == "1.2.3"

    @pytest.mark.parametrize("value", ["abc", "1.2", "1.2.3.4", "1..3", ""])
    def test_parse_invalid(self, value):
        with pytest.raises(ValueError):
            ThemeVersion.parse(value)

    def test_ordering(self):
        assert ThemeVersion(major=1, minor=0, patch=0) < ThemeVersion(major=1, minor=0, patch=1)
        assert ThemeVersion(major=2, minor=0, patch=0) > ThemeVersion(major=1, minor=9, patch=9)

    def test_negative_components_rejected(self):
        with pytest.raises(ValidationError):
            ThemeVersion(major=-1, minor=0, patch=0)


# ── Reference themes ──────────────────────────────────────────────────────────


class TestReferenceThemes:
    def test_five_reference_themes(self):
        assert len(REFERENCE_THEMES) == 5
        assert {t.theme_id for t in REFERENCE_THEMES} == {"blue", "slate", "forest", "gold", "minimal"}

    def test_stable_ids_are_versioned(self):
        for theme in REFERENCE_THEMES:
            assert theme.stable_id == f"theme.{theme.theme_id}.v1"

    def test_distinct_primaries(self):
        primaries = {t.tokens.colors.primary for t in REFERENCE_THEMES}
        assert len(primaries) == 5

    def test_register_all_reference_themes(self):
        registry = _fresh_registry()
        for theme in REFERENCE_THEMES:
            registry.register(theme)
        assert len(registry) == 5


# ── Registration & duplicates ─────────────────────────────────────────────────


class TestRegistration:
    def test_register_and_contains(self):
        registry = _fresh_registry()
        registry.register(REFERENCE_THEMES[0])
        assert registry.contains("blue")
        assert "blue" in registry
        assert len(registry) == 1

    def test_duplicate_theme_id_rejected(self):
        registry = _fresh_registry()
        registry.register(REFERENCE_THEMES[0])
        with pytest.raises(ThemeRegistrationError):
            registry.register(REFERENCE_THEMES[0])

    def test_duplicate_stable_id_rejected(self):
        registry = _fresh_registry()
        registry.register(_palette(metadata=_meta(theme_id="a", stable_id="theme.shared.v1")))
        with pytest.raises(ThemeRegistrationError):
            registry.register(_palette(metadata=_meta(theme_id="b", stable_id="theme.shared.v1")))

    def test_replacement_at_registry_level(self):
        registry = _fresh_registry(allow_replacement=True)
        registry.register(_palette(metadata=_meta(theme_id="x", display_name="First")))
        registry.register(_palette(metadata=_meta(theme_id="x", display_name="Second")))
        assert registry.resolve("x").metadata.display_name == "Second"

    def test_replacement_per_call(self):
        registry = _fresh_registry()
        registry.register(_palette(metadata=_meta(theme_id="x", display_name="First")))
        registry.register(_palette(metadata=_meta(theme_id="x", display_name="Second")), allow_replacement=True)
        assert registry.resolve("x").metadata.display_name == "Second"

    def test_unregister(self):
        registry = _fresh_registry()
        registry.register(REFERENCE_THEMES[0])
        removed = registry.unregister("blue")
        assert removed is not None
        assert not registry.contains("blue")
        assert registry.unregister("blue") is None

    def test_reject_non_palette(self):
        registry = _fresh_registry()
        with pytest.raises(ThemeRegistrationError):
            registry.register(object())  # type: ignore[arg-type]


# ── Lookup ────────────────────────────────────────────────────────────────────


class TestLookup:
    def test_resolve(self):
        registry = _fresh_registry()
        registry.register(REFERENCE_THEMES[0])
        assert registry.resolve("blue").stable_id == "theme.blue.v1"

    def test_resolve_missing_raises(self):
        registry = _fresh_registry()
        with pytest.raises(ThemeLookupError):
            registry.resolve("nope")

    def test_lookup_by_stable_id(self):
        registry = _fresh_registry()
        registry.register(REFERENCE_THEMES[0])
        assert registry.lookup("theme.blue.v1").theme_id == "blue"

    def test_get_returns_none_for_missing(self):
        registry = _fresh_registry()
        assert registry.get("nope") is None


# ── Ordering / metadata / immutability ────────────────────────────────────────


class TestOrderingAndMetadata:
    def test_list_is_registration_order(self):
        registry = _fresh_registry()
        registry.register(REFERENCE_THEMES[0])  # blue
        registry.register(REFERENCE_THEMES[2])  # forest
        assert registry.list() == ("blue", "forest")

    def test_ordered_is_deterministic(self):
        registry = _fresh_registry()
        for theme in REFERENCE_THEMES:
            registry.register(theme)
        assert registry.ordered() == registry.ordered()
        stable_ids = [t.stable_id for t in registry.ordered()]
        assert stable_ids == sorted(stable_ids)

    def test_metadata_map_is_immutable(self):
        registry = _fresh_registry()
        registry.register(REFERENCE_THEMES[0])
        with pytest.raises(TypeError):
            registry.metadata()["x"] = _meta("y")

    def test_metadata_map_keyed_by_theme_id(self):
        registry = _fresh_registry()
        registry.register(REFERENCE_THEMES[0])
        assert "blue" in registry.metadata()
        assert registry.metadata()["blue"].stable_id == "theme.blue.v1"


class TestImmutability:
    def test_palette_is_frozen(self):
        palette = REFERENCE_THEMES[0]
        with pytest.raises(ValidationError):
            palette.tokens = _palette().tokens

    def test_metadata_is_frozen(self):
        with pytest.raises(ValidationError):
            REFERENCE_THEMES[0].metadata.display_name = "Renamed"

    def test_tokens_are_frozen(self):
        with pytest.raises(ValidationError):
            REFERENCE_THEMES[0].tokens.colors.primary = "#000000"


# ── Engine compatibility gate ────────────────────────────────────────────────


class TestEngineGate:
    def test_newer_engine_rejected(self):
        registry = _fresh_registry(supported_engine_version=ThemeVersion(major=1, minor=0, patch=0))
        future = _palette(metadata=_meta(engine_version=ThemeVersion(major=2, minor=0, patch=0)))
        with pytest.raises(ThemeRegistrationError):
            registry.register(future)

    def test_compatible_engine_accepted(self):
        registry = _fresh_registry(supported_engine_version=ThemeVersion(major=2, minor=0, patch=0))
        registry.register(_palette(metadata=_meta(engine_version=ThemeVersion(major=2, minor=0, patch=0))))
        assert registry.contains("test")


# ── Token validation ──────────────────────────────────────────────────────────


class TestTokenValidation:
    @pytest.mark.parametrize("bad", ["blue", "#12345", "#1234567", "rgb(1,2,3)", ""])
    def test_invalid_hex_color_rejected(self, bad):
        colors = dict(_BLUE, primary=bad)
        with pytest.raises(ValidationError):
            ColorTokens(**colors)

    def test_colors_required(self):
        with pytest.raises(ValidationError):
            ThemeTokens()  # type: ignore[call-arg]

    def test_negative_spacing_rejected(self):
        with pytest.raises(ValidationError):
            _palette(spacing={"unit_mm": -1})

    def test_invalid_density_rejected(self):
        with pytest.raises(ValidationError):
            _palette(spacing={"density": "huge"})

    def test_invalid_accent_style_rejected(self):
        with pytest.raises(ValidationError):
            _palette(effects={"accent_style": "neon"})

    def test_empty_display_name_rejected(self):
        with pytest.raises(ValidationError):
            _meta(display_name="")


# ── Plugin readiness ──────────────────────────────────────────────────────────


class TestPluginExtension:
    def test_register_plugin_theme(self):
        registry = _fresh_registry()
        plugin = _palette(
            metadata=_meta(
                theme_id="vendor.ink",
                stable_id="theme.vendor.ink.v1",
                plugin_origin="vendor",
                display_name="Vendor Ink",
            )
        )
        registry.register(plugin)
        assert registry.contains("vendor.ink")
        assert registry.resolve("vendor.ink").metadata.plugin_origin == "vendor"

    def test_plugin_does_not_touch_reference_themes(self):
        registry = _fresh_registry()
        for theme in REFERENCE_THEMES:
            registry.register(theme)
        registry.register(
            _palette(
                metadata=_meta(
                    theme_id="vendor.ink",
                    stable_id="theme.vendor.ink.v1",
                    plugin_origin="vendor",
                )
            )
        )
        assert len(registry) == 6


# ── Thread safety ─────────────────────────────────────────────────────────────


class TestThreadSafety:
    def test_concurrent_register_and_read(self):
        registry = _fresh_registry()
        errors: list[Exception] = []

        def worker(i: int) -> None:
            try:
                registry.register(
                    _palette(metadata=_meta(theme_id=f"t{i}", stable_id=f"theme.t{i}.v1"))
                )
            except ThemeRegistrationError:
                pass

        def reader(_: int) -> None:
            for _ in range(100):
                registry.contains("blue")
                registry.list()
                registry.ordered()
                registry.metadata()

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(worker, range(4)))
            list(pool.map(reader, range(4)))

        assert errors == []
        assert registry.contains("t0")


# ── Serialization ─────────────────────────────────────────────────────────────


class TestSerialization:
    def test_round_trip(self):
        palette = REFERENCE_THEMES[0]
        restored = ThemePalette.model_validate_json(palette.model_dump_json())
        assert restored == palette
        assert restored.stable_id == "theme.blue.v1"
