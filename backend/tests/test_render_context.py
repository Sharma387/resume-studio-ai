"""Tests for the RenderContext (Layout Engine, Phase 0)."""

import ast
import concurrent.futures
import importlib
import inspect
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.rendering.context import (
    ContentReference,
    ContextValidationError,
    OutputFormat,
    RenderContext,
    RenderMode,
    RenderState,
    validate_resolved_context,
)
from app.rendering.layout.layout_definition import LayoutDefinition
from app.rendering.layout.layout_metadata import LayoutVersion
from app.rendering.layout.reference_layouts import executive_layout
from app.rendering.theme.reference_themes import blue_theme
from app.rendering.theme.theme_metadata import ThemeVersion
from app.rendering.theme.theme_palette import ThemePalette


def _layout(engine: tuple[int, int, int] = (1, 0, 0)) -> LayoutDefinition:
    return executive_layout().model_copy(
        update={
            "metadata": executive_layout().metadata.model_copy(
                update={"engine_version": LayoutVersion(major=engine[0], minor=engine[1], patch=engine[2])}
            )
        }
    )


def _theme(engine: tuple[int, int, int] = (1, 0, 0)) -> ThemePalette:
    return blue_theme().model_copy(
        update={
            "metadata": blue_theme().metadata.model_copy(
                update={"engine_version": ThemeVersion(major=engine[0], minor=engine[1], patch=engine[2])}
            )
        }
    )


def _context(**overrides) -> RenderContext:
    base = dict(layout=_layout(), theme=_theme())
    base.update(overrides)
    return RenderContext(**base)


# ── Construction ──────────────────────────────────────────────────────────────


class TestConstruction:
    def test_valid_context_builds(self):
        context = _context()
        assert context.layout.stable_id == "layout.executive.v1"
        assert context.theme.stable_id == "theme.blue.v1"

    def test_layout_and_theme_are_required(self):
        with pytest.raises(ValidationError):
            RenderContext(theme=_theme())  # missing layout
        with pytest.raises(ValidationError):
            RenderContext(layout=_layout())  # missing theme

    def test_content_ref_optional(self):
        assert _context().content_ref is None
        context = _context(content_ref=ContentReference(stable_id="resume.abc", content_hash="a" * 32))
        assert context.content_ref.stable_id == "resume.abc"

    def test_default_state(self):
        state = _context().state
        assert state.output_format is OutputFormat.HTML
        assert state.mode is RenderMode.PRODUCTION
        assert state.page_number == 1
        assert state.page_count is None
        assert state.deterministic is True


# ── Immutability (top-level and nested) ───────────────────────────────────────


class TestImmutability:
    def test_context_is_frozen(self):
        context = _context()
        with pytest.raises(ValidationError):
            context.layout = _layout(engine=(2, 0, 0))

    def test_state_is_frozen(self):
        context = _context()
        with pytest.raises(ValidationError):
            context.state.output_format = OutputFormat.PDF

    def test_nested_models_are_frozen(self):
        context = _context()
        with pytest.raises(ValidationError):
            context.layout.metadata.display_name = "Renamed"
        with pytest.raises(ValidationError):
            context.theme.tokens.colors.primary = "#000000"

    def test_content_reference_is_frozen(self):
        ref = ContentReference(stable_id="resume.a", content_hash="a" * 32)
        with pytest.raises(ValidationError):
            ref.stable_id = "changed"


# ── RenderState ───────────────────────────────────────────────────────────────


class TestRenderState:
    def test_custom_state(self):
        state = RenderState(
            output_format=OutputFormat.PDF,
            mode=RenderMode.PREVIEW,
            page_number=2,
            page_count=3,
            locale="en-GB",
            timezone="Europe/London",
            accessibility_mode=True,
            ats_mode=True,
        )
        assert state.output_format is OutputFormat.PDF
        assert state.mode is RenderMode.PREVIEW

    def test_page_number_exceeds_page_count_rejected(self):
        with pytest.raises(ValidationError):
            RenderState(page_number=4, page_count=3)

    def test_page_number_zero_rejected(self):
        with pytest.raises(ValidationError):
            RenderState(page_number=0)

    def test_invalid_output_format_rejected(self):
        with pytest.raises(ValidationError):
            RenderState(output_format="svg")  # type: ignore[arg-type]


# ── OutputFormat ──────────────────────────────────────────────────────────────


class TestOutputFormat:
    def test_enum_values(self):
        assert {f.value for f in OutputFormat} == {
            "html",
            "pdf",
            "docx",
            "pptx",
            "png",
            "json",
        }

    def test_state_accepts_each_format(self):
        for fmt in OutputFormat:
            assert RenderState(output_format=fmt).output_format is fmt


# ── ContentReference ──────────────────────────────────────────────────────────


class TestContentReference:
    def test_valid(self):
        ContentReference(stable_id="resume.abc", content_hash="abcd1234" * 4)

    def test_invalid_hash_rejected(self):
        with pytest.raises(ValidationError):
            ContentReference(stable_id="resume.abc", content_hash="not-a-hash!")

    def test_empty_stable_id_rejected(self):
        with pytest.raises(ValidationError):
            ContentReference(stable_id="", content_hash="a" * 32)


# ── Engine compatibility ──────────────────────────────────────────────────────


class TestEngineCompatibility:
    def test_compatible(self):
        _context(engine_version=(1, 0, 0))

    def test_no_engine_version_allowed(self):
        _context(engine_version=None)

    def test_layout_requires_newer_engine(self):
        context = dict(layout=_layout(engine=(2, 0, 0)), theme=_theme())
        with pytest.raises(ValidationError):
            RenderContext(**context, engine_version=(1, 0, 0))
        RenderContext(**context, engine_version=(2, 0, 0))

    def test_theme_requires_newer_engine(self):
        context = dict(layout=_layout(), theme=_theme(engine=(2, 0, 0)))
        with pytest.raises(ValidationError):
            RenderContext(**context, engine_version=(1, 0, 0))
        RenderContext(**context, engine_version=(2, 0, 0))

    def test_invalid_engine_version_rejected(self):
        with pytest.raises(ValidationError):
            _context(engine_version=(1, 0))  # wrong arity
        with pytest.raises(ValidationError):
            _context(engine_version="1.0.0")  # wrong type

    def test_validate_resolved_context_raises(self):
        with pytest.raises(ContextValidationError):
            validate_resolved_context(
                layout=_layout(engine=(2, 0, 0)),
                theme=_theme(),
                content_ref=None,
                engine_version=(1, 0, 0),
            )


# ── Serialization & stable identifiers ───────────────────────────────────────


class TestSerialization:
    def test_round_trip(self):
        context = _context(
            content_ref=ContentReference(stable_id="resume.abc", content_hash="a" * 32),
            state=RenderState(output_format=OutputFormat.PDF),
            engine_version=(1, 0, 0),
        )
        restored = RenderContext.model_validate_json(context.model_dump_json())
        assert restored == context

    def test_stable_identifiers_in_serialization(self):
        raw = _context().model_dump_json()
        assert "layout.executive.v1" in raw
        assert "theme.blue.v1" in raw

    def test_deterministic_serialization(self):
        a = _context().model_dump_json()
        b = _context().model_dump_json()
        assert a == b

    def test_stable_identifier_properties(self):
        context = _context()
        assert context.layout_stable_id == "layout.executive.v1"
        assert context.theme_stable_id == "theme.blue.v1"


# ── Copy / replace semantics ──────────────────────────────────────────────────


class TestCopy:
    def test_context_with_new_state(self):
        context = _context()
        updated = context.model_copy(
            update={"state": context.state.model_copy(update={"output_format": OutputFormat.PDF})}
        )
        assert updated.state.output_format is OutputFormat.PDF
        assert context.state.output_format is OutputFormat.HTML  # original unchanged

    def test_context_with_new_layout(self):
        context = _context()
        updated = context.model_copy(update={"layout": _layout(engine=(2, 0, 0))})
        assert updated.layout.metadata.engine_version == LayoutVersion(major=2, minor=0, patch=0)
        assert context.layout.metadata.engine_version == LayoutVersion(major=1, minor=0, patch=0)


# ── Thread-safe reads ─────────────────────────────────────────────────────────


class TestThreadSafety:
    def test_concurrent_serialization_is_stable(self):
        context = _context()

        def serialize(_: int) -> str:
            return context.model_dump_json()

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(serialize, range(16)))
        assert len(set(results)) == 1


# ── Architecture: no forbidden registry dependencies ──────────────────────────


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


class TestArchitectureDependencies:
    def test_theme_registry_does_not_import_layout(self):
        imports = _module_imports("app.rendering.theme.theme_registry")
        assert not _imports_package(imports, "app.rendering.layout")

    def test_layout_registry_does_not_import_theme(self):
        imports = _module_imports("app.rendering.layout.layout_registry")
        assert not _imports_package(imports, "app.rendering.theme")

    def test_component_registry_imports_neither(self):
        imports = _module_imports("app.rendering.components.registry")
        assert not _imports_package(imports, "app.rendering.layout")
        assert not _imports_package(imports, "app.rendering.theme")

    def test_render_context_is_composition_point(self):
        imports = _module_imports("app.rendering.context.render_context")
        assert _imports_package(imports, "app.rendering.layout")
        assert _imports_package(imports, "app.rendering.theme")
        # RenderContext resolves nothing: it must not import any registry.
        assert not _imports_package(imports, "app.rendering.layout.layout_registry")
        assert not _imports_package(imports, "app.rendering.theme.theme_registry")
        assert not _imports_package(imports, "app.rendering.components")
