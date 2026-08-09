"""New RenderTree → HTML pipeline orchestration (additive).

Wires: Resume → CVM → RenderContext → TreeBuilder → RenderTree → HTML.

This is the new production path (Layout Engine). It does NOT touch the legacy
TemplateRegistry path, PreviewService, or any API. PreviewService integration
awaits the ``template_id → layout`` migration.
"""

from __future__ import annotations

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
from app.rendering.content import ContentView, cvm_from_resume
from app.rendering.context import OutputFormat, RenderContext, RenderState
from app.rendering.layout.layout_definition import LayoutDefinition
from app.rendering.renderers.tree_docx_renderer import RenderTreeDOCXRenderer
from app.rendering.renderers.tree_html_renderer import RenderTreeHTMLRenderer
from app.rendering.renderers.tree_pdf_renderer import RenderTreePDFRenderer
from app.rendering.theme.theme_palette import ThemePalette

_REFERENCE_COMPONENTS: tuple = (
    ProfileComponent(),
    SummaryComponent(),
    ExperienceComponent(),
    EducationComponent(),
    SkillsComponent(),
    CertificationsComponent(),
    ProjectsComponent(),
    AwardsComponent(),
    LanguagesComponent(),
)


def default_component_registry() -> ComponentRegistry:
    """A ComponentRegistry populated with the built-in reference components."""
    registry = ComponentRegistry()
    for component in _REFERENCE_COMPONENTS:
        registry.register(component)
    return registry


def render_layout_html(
    cvm: ContentView,
    layout: LayoutDefinition,
    theme: ThemePalette,
    *,
    state: RenderState | None = None,
    registry: ComponentRegistry | None = None,
    renderer: RenderTreeHTMLRenderer | None = None,
) -> str:
    """Render a ContentView through ``layout`` + ``theme`` into HTML."""
    context = RenderContext(layout=layout, theme=theme, state=state or RenderState())
    builder = TreeBuilder(registry or default_component_registry())
    document = builder.build(cvm, context)
    return (renderer or RenderTreeHTMLRenderer()).render(document, theme=theme)


def render_resume_layout_html(
    resume: Resume,
    layout: LayoutDefinition,
    theme: ThemePalette,
    *,
    stable_id: str | None = None,
    state: RenderState | None = None,
) -> str:
    """Build a CVM from ``resume`` and render it through ``layout`` + ``theme``."""
    cvm = cvm_from_resume(resume, stable_id=stable_id)
    return render_layout_html(cvm, layout, theme, state=state)


def render_layout_pdf(
    cvm: ContentView,
    layout: LayoutDefinition,
    theme: ThemePalette,
    *,
    state: RenderState | None = None,
    registry: ComponentRegistry | None = None,
    renderer: RenderTreePDFRenderer | None = None,
) -> bytes:
    """Render a ContentView through ``layout`` + ``theme`` into PDF bytes.

    Orchestration seam mirroring ``render_layout_html``: CVM → RenderContext →
    TreeBuilder → RenderTree → RenderTreePDFRenderer.
    """
    context = RenderContext(
        layout=layout,
        theme=theme,
        state=state or RenderState(output_format=OutputFormat.PDF),
    )
    builder = TreeBuilder(registry or default_component_registry())
    document = builder.build(cvm, context)
    return (renderer or RenderTreePDFRenderer()).render(document, theme=theme)


def render_resume_layout_pdf(
    resume: Resume,
    layout: LayoutDefinition,
    theme: ThemePalette,
    *,
    stable_id: str | None = None,
    state: RenderState | None = None,
) -> bytes:
    """Build a CVM from ``resume`` and render it through ``layout`` + ``theme`` to PDF."""
    cvm = cvm_from_resume(resume, stable_id=stable_id)
    return render_layout_pdf(cvm, layout, theme, state=state)


def render_layout_docx(
    cvm: ContentView,
    layout: LayoutDefinition,
    theme: ThemePalette,
    *,
    state: RenderState | None = None,
    registry: ComponentRegistry | None = None,
    renderer: RenderTreeDOCXRenderer | None = None,
) -> bytes:
    """Render a ContentView through ``layout`` + ``theme`` into DOCX bytes."""
    context = RenderContext(
        layout=layout,
        theme=theme,
        state=state or RenderState(output_format=OutputFormat.DOCX),
    )
    builder = TreeBuilder(registry or default_component_registry())
    document = builder.build(cvm, context)
    return (renderer or RenderTreeDOCXRenderer()).render(document, theme=theme)


def render_resume_layout_docx(
    resume: Resume,
    layout: LayoutDefinition,
    theme: ThemePalette,
    *,
    stable_id: str | None = None,
    state: RenderState | None = None,
) -> bytes:
    """Build a CVM from ``resume`` and render it through ``layout`` + ``theme`` to DOCX."""
    cvm = cvm_from_resume(resume, stable_id=stable_id)
    return render_layout_docx(cvm, layout, theme, state=state)
