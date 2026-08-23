"""Unified export API - one RenderTree, multiple output formats."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, ValidationError

from app.core.logging import get_logger
from app.models.user import User
from app.rendering.export_service import ExportFormat, ExportFormatError, export_resume
from app.rendering.layout.layout_config import LayoutConfig
from app.rendering.layout.layout_registry import LayoutLookupError
from app.rendering.theme.theme_registry import ThemeLookupError
from app.services.auth_deps import require_user
from app.services.layout_config_service import get_layout_config as load_persisted_layout_config
from app.services.repositories.factory import get_resume_repository

logger = get_logger(__name__)

router = APIRouter()


class ExportRequest(BaseModel):
    """Request body for the unified export endpoint.

    Unknown fields (e.g. the retired ``template_id``) are rejected so a legacy
    payload can never be silently accepted by the canonical export path.
    ``layout_config`` is optional; when omitted the persisted customization is
    used (explicit request > persisted customization > engine default).
    ``auto_balance`` enables content-aware layout balancing (opt-in).
    """

    model_config = ConfigDict(extra="forbid")

    layout_id: str
    theme_id: str
    format: ExportFormat
    layout_config: LayoutConfig | None = None
    auto_balance: bool = False


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


@router.post("/resume/{resume_id}/export")
async def export_resume_artifact(
    resume_id: str,
    body: ExportRequest,
    current_user: User = Depends(require_user),
):
    """Export a resume in the requested layout + theme + format."""
    resume = get_resume_repository().get_by_id(resume_id, getattr(current_user, "id", None))
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Request-explicit config wins; persisted config seeds auto-balance only.
    user_id = getattr(current_user, "id", None)
    base_config = _load_persisted_config(resume_id, user_id)

    try:
        result = export_resume(
            resume,
            layout_id=body.layout_id,
            theme_id=body.theme_id,
            output_format=body.format,
            layout_config=body.layout_config,
            auto_balance=body.auto_balance,
            base_config=base_config,
        )
    except LayoutLookupError:
        raise HTTPException(status_code=404, detail=f"Layout '{body.layout_id}' not found")
    except ThemeLookupError:
        raise HTTPException(status_code=404, detail=f"Theme '{body.theme_id}' not found")
    except ExportFormatError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Response(
        content=result.content,
        media_type=result.content_type,
        headers={"Content-Disposition": f'attachment; filename="{result.filename}"'},
    )
