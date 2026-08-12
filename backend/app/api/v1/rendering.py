"""Resume rendering API — canonical preview + legacy compatibility boundary.

Canonical (Layout Engine):
    GET /resume/{id}/preview?layout_id=<layout>&theme=<theme>
    GET /resume/layouts
    GET /resume/themes
    GET /resume/preview/file/{filename}

LEGACY COMPATIBILITY API (retained for backward compatibility only):
    GET /resume/templates
    GET /resume/templates/{id}
    GET /resume/template-resolve/{template_id}
    GET /resume/{id}/preview?template_id=<template>

Importing this module must not initialize the legacy rendering stack
(TemplateRegistry / PreviewService / ResumeRenderingService / Jinja
HTMLRenderer / ReportLab). Legacy invocations are delegated to
``app.rendering.legacy`` lazily inside the compatibility endpoints.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.core.logging import get_logger
from app.models.user import User
from app.rendering import layout_preview, legacy_templates
from app.rendering.layout.layout_registry import LayoutLookupError
from app.rendering.theme.theme_registry import ThemeLookupError
from app.services.auth_deps import require_user
from app.services.repositories.factory import get_resume_repository

logger = get_logger(__name__)

router = APIRouter()


@router.get("/resume/templates")
async def list_resume_templates():
    """LEGACY COMPATIBILITY API — list all legacy templates (TemplateRegistry).

    Not used by the canonical Gallery/Designer/Review/Export flows.
    """
    from app.rendering.legacy.template_lookup import list_legacy_templates

    return {"success": True, "data": list_legacy_templates()}


@router.get("/resume/layouts")
async def list_resume_layouts():
    """List the new layout-engine layouts from the reference registry."""
    from app.rendering.layout.reference_layouts import REFERENCE_LAYOUTS
    return {
        "success": True,
        "data": [
            {
                "layout_id": layout.metadata.layout_id,
                "name": layout.metadata.display_name,
                "description": layout.metadata.description,
            }
            for layout in REFERENCE_LAYOUTS
        ],
    }


@router.get("/resume/themes")
async def list_resume_themes():
    """List the layout-engine themes from the theme registry."""
    from app.rendering.layout_preview import default_theme_registry
    return {
        "success": True,
        "data": [
            {
                "theme_id": theme.metadata.theme_id,
                "name": theme.metadata.display_name,
                "description": theme.metadata.description,
                "style": theme.metadata.style,
                "tags": list(theme.metadata.tags),
            }
            for theme in default_theme_registry().palettes()
        ],
    }


@router.get("/resume/templates/{template_id}")
async def get_resume_template(template_id: str):
    """LEGACY COMPATIBILITY API — a single legacy template's manifest plus its
    mapped ``layout_id`` (compatibility with the template→layout boundary).
    """
    from app.rendering.legacy.template_lookup import get_legacy_template

    tmpl = get_legacy_template(template_id)
    if tmpl is None:
        raise HTTPException(status_code=404, detail="Template not found")
    try:
        tmpl["layout_id"] = legacy_templates.resolve_legacy_template(template_id)
    except legacy_templates.UnknownLegacyTemplateError:
        tmpl["layout_id"] = None
    return {"success": True, "data": tmpl}


@router.get("/resume/template-resolve/{template_id}")
async def resolve_template_compat(template_id: str):
    """LEGACY COMPATIBILITY — resolve a legacy ``template_id`` to the canonical
    ``layout_id`` (+ default theme) using the deterministic mapping only.

    No template registry / legacy rendering is involved. Unknown ids → ``404``
    (no silent fallback). Used by the frontend ``?template=`` redirect.
    """
    from app.rendering.legacy.template_lookup import get_layout_id

    layout_id = get_layout_id(template_id)
    if layout_id is None:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
    return {
        "success": True,
        "data": {
            "template_id": template_id,
            "layout_id": layout_id,
            "theme_id": legacy_templates.DEFAULT_LEGACY_THEME,
        },
    }


@router.get("/resume/{resume_id}/preview")
async def generate_resume_preview(
    resume_id: str,
    template_id: str | None = Query(default=None),
    layout_id: str | None = Query(default=None),
    theme: str | None = Query(default=None),
    current_user: User = Depends(require_user),
):
    """Generate an HTML preview of the resume.

    Exactly one render mode must be selected:

    - ``layout_id`` (canonical): renders through the new layout engine.
    - ``template_id`` (LEGACY COMPATIBILITY): renders through the legacy
      Jinja template stack (via ``app.rendering.legacy``).

    Neither ``layout_id`` nor ``template_id`` → ``400``; both → ``400``;
    unknown ids → ``404``. There is no implicit fallback.
    """
    resume = get_resume_repository().get_by_id(resume_id, getattr(current_user, "id", None))
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")

    if layout_id is None and template_id is None:
        raise HTTPException(
            status_code=400,
            detail="Specify either layout_id or template_id",
        )
    if layout_id is not None and template_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Specify either layout_id or template_id, not both",
        )

    if layout_id is not None:
        logger.debug(
            "Layout preview requested",
            resume_id=resume_id,
            layout_id=layout_id,
            theme=theme,
            mode="layout",
        )
        try:
            preview_path = layout_preview.generate_layout_preview(resume, layout_id, theme)
        except LayoutLookupError:
            raise HTTPException(status_code=404, detail=f"Layout '{layout_id}' not found")
        except ThemeLookupError:
            raise HTTPException(status_code=404, detail=f"Theme '{theme}' not found")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {
            "success": True,
            "data": {
                "mode": "layout",
                "layout_id": layout_id,
                "preview_url": f"/api/v1/resume/preview/file/{Path(preview_path).name}",
            },
        }

    # Explicit legacy compatibility path — no default template fallback.
    from app.rendering.legacy.preview import generate_legacy_preview
    from app.rendering.legacy.template_lookup import template_exists

    if not template_exists(template_id):
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

    logger.debug("Legacy preview requested", resume_id=resume_id, template_id=template_id, theme=theme, mode="legacy")
    try:
        preview_path = generate_legacy_preview(resume, template_id, theme=theme)
        return {"success": True, "data": {"preview_url": f"/api/v1/resume/preview/file/{Path(preview_path).name}"}}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/resume/preview/file/{filename}")
async def serve_preview(filename: str):
    """Serve a generated preview HTML file.

    Only regular files inside the preview directory are served; path
    traversal or directory names resolve to a 404.
    """
    from app.rendering.paths import PREVIEW_DIR
    base = PREVIEW_DIR.resolve()
    path = (PREVIEW_DIR / filename).resolve()
    if not path.is_relative_to(base) or not path.is_file():
        raise HTTPException(status_code=404, detail="Preview not found")
    return HTMLResponse(content=path.read_text(encoding="utf-8"))
