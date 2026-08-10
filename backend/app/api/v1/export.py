"""Unified export API - one RenderTree, multiple output formats."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app.models.user import User
from app.rendering.export_service import ExportFormat, ExportFormatError, export_resume
from app.rendering.layout.layout_registry import LayoutLookupError
from app.rendering.theme.theme_registry import ThemeLookupError
from app.services.auth_deps import require_user
from app.services.repositories.factory import get_resume_repository

router = APIRouter()


class ExportRequest(BaseModel):
    """Request body for the unified export endpoint."""

    layout_id: str
    theme_id: str
    format: ExportFormat


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

    try:
        result = export_resume(
            resume,
            layout_id=body.layout_id,
            theme_id=body.theme_id,
            output_format=body.format,
        )
    except LayoutLookupError:
        raise HTTPException(status_code=404, detail=f"Layout '{body.layout_id}' not found")
    except ThemeLookupError:
        raise HTTPException(status_code=404, detail=f"Theme '{body.theme_id}' not found")
    except ExportFormatError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Response(
        content=result.content,
        media_type=result.content_type,
        headers={"Content-Disposition": f'attachment; filename="{result.filename}"'},
    )
