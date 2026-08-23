"""Resume rendering API — canonical (Layout Engine).

    GET /resume/{id}/preview?layout_id=<layout>&theme=<theme>
    GET /resume/layouts
    GET /resume/themes
    GET /resume/preview/file/{filename}

The legacy template registry/listing API (``/resume/templates``), the
mapping-only URL shim (``/resume/template-resolve``), and the legacy
``?template_id=`` preview mode were retired. This module imports no legacy
rendering stack (TemplateRegistry / PreviewService / ResumeRenderingService /
Jinja HTMLRenderer / ReportLab / legacy template mappings).
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import ValidationError

from app.core.logging import get_logger
from app.models.user import User
from app.rendering import layout_preview
from app.rendering.content import cvm_from_resume
from app.rendering.layout.effective import resolve_effective_layout
from app.rendering.layout.layout_config import LayoutConfig
from app.rendering.layout.layout_registry import LayoutLookupError
from app.rendering.theme.theme_registry import ThemeLookupError
from app.services.auth_deps import require_user
from app.services.layout_config_service import get_layout_config as load_persisted_layout_config
from app.services.repositories.factory import get_resume_repository

logger = get_logger(__name__)

router = APIRouter()


def _load_persisted_config(resume_id: str, user_id: str | None) -> LayoutConfig | None:
    """Load and validate the persisted per-resume layout config (None if absent/invalid)."""
    persisted = load_persisted_layout_config(resume_id, user_id or "")
    if not persisted:
        return None
    try:
        return LayoutConfig.model_validate(persisted)
    except ValidationError:
        logger.warning("Stored layout_config is invalid; ignoring it", resume_id=resume_id)
        return None


@router.get("/resume/layouts")
async def list_resume_layouts():
    """List the layout-engine layouts from the reference registry."""
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


@router.get("/resume/{resume_id}/preview")
async def generate_resume_preview(
    resume_id: str,
    layout_id: str | None = Query(default=None),
    theme: str | None = Query(default=None),
    template_id: str | None = Query(default=None),
    layout_config: str | None = Query(default=None),
    auto_balance: bool = Query(default=False),
    current_user: User = Depends(require_user),
):
    """Generate an HTML preview of the resume through the canonical layout engine.

    ``layout_id`` is required (``400`` when missing); ``theme`` defaults to the
    engine default. ``layout_config`` is an optional JSON-encoded
    :class:`LayoutConfig` that overrides any persisted customization
    (explicit request > persisted customization > engine default behaviour).
    ``auto_balance`` enables content-aware layout balancing (opt-in); when set
    without an explicit ``layout_config`` the persisted customization is ignored
    for this request and the layout is balanced from the resume content.
    The legacy ``template_id`` parameter was retired — requests still using it
    are rejected explicitly (no translation, no fallback).
    """
    resume = get_resume_repository().get_by_id(resume_id, getattr(current_user, "id", None))
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")

    if template_id is not None:
        raise HTTPException(status_code=400, detail="template_id is retired; use layout_id")
    if layout_id is None:
        raise HTTPException(status_code=400, detail="Specify layout_id")

    user_id = getattr(current_user, "id", None)
    # Request-explicit config wins; persisted config seeds auto-balance only.
    explicit_config = None
    if layout_config is not None:
        try:
            explicit_config = LayoutConfig.model_validate_json(layout_config)
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=f"Invalid layout_config: {e}")
    base_config = _load_persisted_config(resume_id, user_id)

    logger.debug(
        "Layout preview requested",
        resume_id=resume_id,
        layout_id=layout_id,
        theme=theme,
        mode="layout",
        customization=explicit_config is not None,
        auto_balance=auto_balance,
    )
    try:
        base = layout_preview.resolve_preview_layout(layout_id, None)
        cvm = cvm_from_resume(resume)
        resolved, effective_config, balance_result = resolve_effective_layout(
            base,
            cvm,
            explicit_config=explicit_config,
            auto_balance=auto_balance,
            base_config=base_config,
            return_balance_result=True,
        )
        density = effective_config.density.value if effective_config is not None else None
        preview_path = layout_preview.generate_layout_preview(
            resume, layout_id, theme, layout=resolved, density=density
        )
    except LayoutLookupError:
        raise HTTPException(status_code=404, detail=f"Layout '{layout_id}' not found")
    except ThemeLookupError:
        raise HTTPException(status_code=404, detail=f"Theme '{theme}' not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    data: dict[str, object] = {
        "mode": "layout",
        "layout_id": layout_id,
        "preview_url": f"/api/v1/resume/preview/file/{Path(preview_path).name}",
    }
    if balance_result is not None:
        cfg = balance_result.config
        data["auto_balance"] = True
        data["layout_rationale"] = balance_result.rationale
        data["balanced_layout"] = {
            "mode": cfg.mode.value,
            "ratio": cfg.ratio.value,
            "sidebar": cfg.sidebar.value,
        }
        # Full effective config so the UI can persist it verbatim via the
        # existing layout-config PUT (mode/sidebar/ratio/density/gap/sections).
        data["balanced_config"] = cfg.model_dump(mode="json")
    return {"success": True, "data": data}


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
