"""Resume rendering API — template listing, preview, and HTML output."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.core.logging import get_logger
from app.models.user import User
from app.rendering import layout_preview
from app.rendering.layout.layout_registry import LayoutLookupError
from app.rendering.service import ResumeRenderingService
from app.rendering.theme.theme_registry import ThemeLookupError
from app.services.auth_deps import require_user
from app.services.repositories.factory import get_resume_repository

logger = get_logger(__name__)

router = APIRouter()
rendering = ResumeRenderingService()


@router.get("/resume/templates")
async def list_resume_templates():
    """List all available resume templates with metadata."""
    templates = rendering.list_templates()
    return {"success": True, "data": templates}


@router.get("/resume/templates/{template_id}")
async def get_resume_template(template_id: str):
    """Get a single template's metadata."""
    tmpl = rendering.get_template(template_id)
    if tmpl is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"success": True, "data": tmpl}


@router.get("/resume/{resume_id}/preview")
async def generate_resume_preview(
    resume_id: str,
    template_id: str = Query(default="executive"),
    layout_id: str | None = Query(default=None),
    theme: str | None = Query(default=None),
    current_user: User = Depends(require_user),
):
    """Generate an HTML preview of the resume.

    Legacy mode (``template_id``) renders through the TemplateRegistry.
    Layout mode (``layout_id``) renders through the new layout engine; theme is
    a ThemeRegistry palette id. When ``layout_id`` is present it takes
    precedence and the legacy path is never consulted.
    """
    resume = get_resume_repository().get_by_id(resume_id, getattr(current_user, "id", None))
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")

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

    try:
        logger.debug("Legacy preview requested", resume_id=resume_id, template_id=template_id, theme=theme, mode="legacy")
        preview_path = rendering.generate_preview(resume, template_id, theme=theme)
        return {"success": True, "data": {"preview_url": f"/api/v1/resume/preview/file/{Path(preview_path).name}"}}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/resume/preview/file/{filename}")
async def serve_preview(filename: str):
    """Serve a generated preview HTML file."""
    from app.rendering.preview.service import PREVIEW_DIR
    path = PREVIEW_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Preview not found")
    return HTMLResponse(content=path.read_text(encoding="utf-8"))
