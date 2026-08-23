"""P3.4: LayoutConfig.density wired into the CSS custom-property spacing scale.

End-to-end contract:

* ``normal``/``None`` emit no density styling → the rendered HTML (spacing
  custom properties and locked ``.layout-*`` rules included) is byte-identical
  to the P1/P2 output — backward compatibility is preserved exactly.
* ``compact`` (0.85) / ``spacious`` (1.2) scale the *consumers* of the four
  spacing custom properties via additive ``calc(var(--x, <fallback>) * F)``
  rules that beat the base *and* ``.layout-*`` cascade (higher specificity,
  later in the stylesheet).
* Density must NOT re-declare ``--x = calc(var(--x) * F)``: that is a custom
  property cycle (guaranteed-invalid per the CSS Variables spec), which would
  silently break spacing in WeasyPrint/browsers instead of scaling it.
* Persisted ``LayoutConfig.density`` survives the JSON round-trip and reaches
  the HTML/PDF renderers through the preview + export production paths.
"""

import re
import uuid
from pathlib import Path

from app.models.resume import Resume
from app.rendering.builder import TreeBuilder
from app.rendering.components import (
    AwardsComponent,
    CertificationsComponent,
    ComponentRegistry,
    EducationComponent,
    ExperienceComponent,
    LanguagesComponent,
    ProfileComponent,
    ProjectsComponent,
    SkillsComponent,
    SummaryComponent,
)
from app.rendering.content.models import ContentView, Profile
from app.rendering.context import RenderContext, RenderState
from app.rendering.export_service import ExportFormat, export_resume
from app.rendering.layout import LayoutConfig
from app.rendering.layout.reference_layouts import sidebar_layout
from app.rendering.layout_html import render_layout_pdf
from app.rendering.layout_preview import generate_layout_preview, render_layout_preview_html
from app.rendering.renderers.tree_html_renderer import (
    _DENSITY_CONSUMERS,
    _DENSITY_SCALE,
    _DENSITY_VARS,
    RenderTreeHTMLRenderer,
)
from app.rendering.theme.reference_themes import blue_theme


def _cvm() -> ContentView:
    return ContentView(
        stable_id="density",
        profile=Profile(full_name="Jane Doe", professional_title="Engineer"),
        summary="Experienced engineer.",
    )


def _registry() -> ComponentRegistry:
    registry = ComponentRegistry()
    for component in (
        ProfileComponent(),
        SummaryComponent(),
        ExperienceComponent(),
        EducationComponent(),
        SkillsComponent(),
        CertificationsComponent(),
        ProjectsComponent(),
        AwardsComponent(),
        LanguagesComponent(),
    ):
        registry.register(component)
    return registry


def _document():
    theme = blue_theme()
    context = RenderContext(layout=sidebar_layout(), theme=theme, state=RenderState())
    return TreeBuilder(_registry()).build(_cvm(), context)


def _html(density: str | None) -> str:
    return RenderTreeHTMLRenderer().render(_document(), theme=blue_theme(), density=density)


def _main_class(html: str) -> str:
    match = re.search(r'<main class="([^"]*)"', html)
    assert match is not None
    return match.group(1)


def _css_value(html: str, prop: str) -> str:
    match = re.search(rf"{re.escape(prop)}:\s*([^;]+);", html)
    assert match is not None, f"property {prop!r} not found in CSS"
    return match.group(1).strip()


def _resume() -> Resume:
    return Resume(
        user_id="density-test",
        full_name=f"Density User {uuid.uuid4().hex[:6]}",
        email="density@test.com",
        summary="Density render test.",
        experience=[{"company": "Acme", "title": "Engineer", "start_date": "2020"}],
    )


class TestDensityNormalIsLocked:
    def test_normal_equals_none_byte_for_byte(self):
        assert _html("normal") == _html(None)

    def test_normal_emits_no_density_styling(self):
        html = _html("normal")
        assert "density-" not in _main_class(html)
        assert "density-" not in html

    def test_unknown_density_ignored(self):
        assert _html("bogus") == _html(None)

    def test_four_spacing_vars_populated_with_theme_values(self):
        html = _html(None)
        assert _css_value(html, "--section-spacing") == "8.0mm"
        assert _css_value(html, "--block-spacing") == "4.0mm"
        assert _css_value(html, "--inline-spacing") == "6.0mm"
        assert _css_value(html, "--line-height") == "1.5"

    def test_layout_css_values_preserved(self):
        html = _html(None)
        assert "--section-spacing: 6mm" in html
        assert "--block-spacing: 3.5mm" in html

    def test_main_class_without_density(self):
        normal = _main_class(_html(None))
        assert normal == "resume layout-sidebar"


class TestDensityScaleCss:
    def test_compact_scales_all_four_vars_consumers(self):
        html = _html("compact")
        for var, prop, selector, fallback in _DENSITY_CONSUMERS:
            assert var in _DENSITY_VARS
            compiled = selector.format(d="compact")
            assert (
                f"{compiled} {{ {prop}: calc(var({var}, {fallback}) * {_DENSITY_SCALE['compact']}); }}"
                in html
            ), f"missing density rule for {var}"

    def test_spacious_uses_factor_1_2(self):
        html = _html("spacious")
        assert "* 1.2" in html
        assert "* 0.85" not in html

    def test_compact_does_not_redeclare_custom_property(self):
        html = _html("compact")
        for var in _DENSITY_VARS:
            assert f"{var}: calc(var({var}" not in html, f"self-referential cycle for {var}"

    def test_density_rule_follows_layout_css_in_source(self):
        html = _html("compact")
        layout_at = html.index(".layout-sidebar {")
        density_at = html.index(".resume.density-compact")
        assert density_at > layout_at

    def test_density_class_applied_to_main(self):
        assert _main_class(_html("compact")) == "resume layout-sidebar density-compact"
        assert _main_class(_html("spacious")) == "resume layout-sidebar density-spacious"

    def test_base_layout_spacing_untouched_when_density_set(self):
        html = _html("compact")
        assert "--section-spacing: 6mm" in html
        assert "--block-spacing: 3.5mm" in html
        assert _css_value(html, "--section-spacing") == "8.0mm"

    def test_normal_has_no_density_rules(self):
        assert ".resume.density-" not in _html("normal")


class TestDensityConfig:
    def test_layout_config_density_round_trip(self):
        for value in ("compact", "normal", "spacious"):
            dumped = LayoutConfig(density=value).model_dump_json()
            restored = LayoutConfig.model_validate_json(dumped)
            assert restored.density.value == value

    def test_persisted_shape_validates(self):
        restored = LayoutConfig.model_validate(
            {"density": "spacious", "mode": "single", "sections": {}}
        )
        assert restored.density.value == "spacious"

    def test_density_defaults_normal(self):
        assert LayoutConfig().density.value == "normal"


class TestDensityProductionPaths:
    def test_export_html_carries_density(self):
        plain = export_resume(
            _resume(),
            layout_id="sidebar",
            theme_id="blue",
            output_format=ExportFormat.HTML,
        ).content.decode()
        compact = export_resume(
            _resume(),
            layout_id="sidebar",
            theme_id="blue",
            output_format=ExportFormat.HTML,
            layout_config=LayoutConfig(density="compact"),
        ).content.decode()
        assert "density-compact" in compact
        assert "density-" not in plain
        assert ".resume.density-compact" in compact

    def test_pdf_normal_equals_none_bytes(self):
        kwargs = dict(layout=sidebar_layout(), theme=blue_theme())
        none = render_layout_pdf(_cvm(), **kwargs)
        normal = render_layout_pdf(_cvm(), **kwargs, density="normal")
        assert normal == none
        assert none.startswith(b"%PDF")

    def test_export_pdf_density_changes_bytes(self):
        compact = export_resume(
            _resume(),
            layout_id="sidebar",
            theme_id="blue",
            output_format=ExportFormat.PDF,
            layout_config=LayoutConfig(density="compact"),
        ).content
        normal = export_resume(
            _resume(),
            layout_id="sidebar",
            theme_id="blue",
            output_format=ExportFormat.PDF,
            layout_config=LayoutConfig(density="normal"),
        ).content
        assert compact != normal
        assert compact.startswith(b"%PDF")

    def test_render_preview_density(self):
        resume = _resume()
        plain = render_layout_preview_html(resume, "sidebar", "blue")
        compact = render_layout_preview_html(resume, "sidebar", "blue", density="compact")
        assert "density-" not in plain
        assert "density-compact" in compact

    def test_generate_preview_cache_keyed_on_density(self, tmp_path, monkeypatch):
        from app.rendering import layout_preview as lp

        monkeypatch.setattr(lp, "PREVIEW_DIR", tmp_path)
        resume = _resume()
        normal = generate_layout_preview(resume, "sidebar", "blue", density="normal")
        compact = generate_layout_preview(resume, "sidebar", "blue", density="compact")
        assert normal != compact
        (base_dir, name) = (Path(compact).parent, Path(compact).name)
        assert "density-compact" in (base_dir / name).read_text(encoding="utf-8")
