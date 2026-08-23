"""Tests for rendering GridConfig.column_ratios (Layout Engine, P3.3A)."""

import re

import pytest

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
from app.rendering.layout import LayoutConfig, LayoutResolver
from app.rendering.layout.reference_layouts import executive_layout, modern_layout, sidebar_layout
from app.rendering.renderers.tree_html_renderer import RenderTreeHTMLRenderer
from app.rendering.theme.reference_themes import blue_theme


def _cvm() -> ContentView:
    return ContentView(
        stable_id="columns",
        profile=Profile(full_name="Jane Doe", professional_title="Engineer"),
        summary="Experienced engineer with a strong record.",
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


def _html(config: LayoutConfig, base) -> str:
    layout = LayoutResolver().resolve(base, config)
    theme = blue_theme()
    context = RenderContext(layout=layout, theme=theme, state=RenderState())
    document = TreeBuilder(_registry()).build(_cvm(), context)
    return RenderTreeHTMLRenderer().render(document, theme=theme)


def _css_value(html: str, prop: str) -> str:
    match = re.search(rf"{re.escape(prop)}:\s*([^;]+);", html)
    assert match is not None, f"property {prop!r} not found in CSS"
    return match.group(1).strip()


def _region_divs(html: str) -> list[tuple[str, str]]:
    return re.findall(
        r'<div class="resume-region resume-region-(\w+)" data-region="\w+" style="([^"]+)"',
        html,
    )


class TestGridTemplate:
    def test_none_preserves_repeat_12(self):
        html = _html(LayoutConfig(), sidebar_layout())
        assert _css_value(html, "grid-template-columns") == "repeat(12, 1fr)"

    @pytest.mark.parametrize(
        "ratio,expected",
        [
            ("30/70", "30fr 70fr"),
            ("32/68", "32fr 68fr"),
            ("35/65", "35fr 65fr"),
            ("40/60", "40fr 60fr"),
        ],
    )
    def test_explicit_ratio_exact(self, ratio, expected):
        html = _html(
            LayoutConfig(mode="two_column", sidebar="left", ratio=ratio),
            sidebar_layout(),
        )
        assert _css_value(html, "grid-template-columns") == expected


class TestSidebarOrdering:
    def test_sidebar_left(self):
        html = _html(
            LayoutConfig(mode="two_column", sidebar="left", ratio="35/65"),
            sidebar_layout(),
        )
        divs = _region_divs(html)
        assert [region for region, _ in divs] == ["sidebar", "main"]
        assert divs[0][1] == "grid-column: 1"
        assert divs[1][1] == "grid-column: 2"
        assert _css_value(html, "grid-template-columns") == "35fr 65fr"

    def test_sidebar_right(self):
        html = _html(
            LayoutConfig(mode="two_column", sidebar="right", ratio="35/65"),
            sidebar_layout(),
        )
        divs = _region_divs(html)
        assert [region for region, _ in divs] == ["main", "sidebar"]
        assert divs[0][1] == "grid-column: 1"
        assert divs[1][1] == "grid-column: 2"
        assert _css_value(html, "grid-template-columns") == "65fr 35fr"


class TestHeaderSafety:
    def test_header_full_width_sidebar_left(self):
        html = _html(
            LayoutConfig(mode="two_column", sidebar="left", ratio="40/60"),
            modern_layout(),
        )
        divs = _region_divs(html)
        assert [region for region, _ in divs] == ["header", "secondary", "main"]
        assert divs[0][1] == "grid-column: 1 / -1"
        assert divs[1][1] == "grid-column: 1"
        assert divs[2][1] == "grid-column: 2"
        assert _css_value(html, "grid-template-columns") == "40fr 60fr"

    def test_header_full_width_sidebar_right(self):
        html = _html(
            LayoutConfig(mode="two_column", sidebar="right", ratio="40/60"),
            modern_layout(),
        )
        divs = _region_divs(html)
        assert [region for region, _ in divs] == ["header", "main", "secondary"]
        assert divs[0][1] == "grid-column: 1 / -1"
        assert divs[1][1] == "grid-column: 1"
        assert divs[2][1] == "grid-column: 2"
        assert _css_value(html, "grid-template-columns") == "60fr 40fr"


class TestBackwardCompatibility:
    def test_single_column_resolved_uses_spans(self):
        html = _html(LayoutConfig(mode="single"), sidebar_layout())
        assert _css_value(html, "grid-template-columns") == "repeat(12, 1fr)"
        divs = _region_divs(html)
        assert [region for region, _ in divs] == ["main"]
        assert divs[0][1] == "grid-column: span 12"

    def test_executive_default_unchanged(self):
        html = _html(LayoutConfig(), executive_layout())
        assert _css_value(html, "grid-template-columns") == "repeat(12, 1fr)"
        divs = _region_divs(html)
        assert [region for region, _ in divs] == ["header", "main"]
        assert divs[0][1] == "grid-column: span 12"
        assert divs[1][1] == "grid-column: span 12"


class TestGap:
    def test_gap_applied_with_ratio(self):
        html = _html(
            LayoutConfig(mode="two_column", ratio="35/65", gap="wide"),
            sidebar_layout(),
        )
        assert _css_value(html, "column-gap") == "16mm"

    def test_gap_unchanged_without_ratio(self):
        html = _html(LayoutConfig(), sidebar_layout())
        assert _css_value(html, "column-gap") == "0"
