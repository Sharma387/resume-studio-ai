"""LEGACY COMPATIBILITY API — ReportLab resume PDF generation.

Retained for backward compatibility only (documented in docs/API.md). The
canonical export flow uses ``POST /resume/{id}/export`` with the RenderTree
pipeline; this module must not be reached by the canonical application.

Importing this module must not initialize the legacy ReportLab stack — the
generation is delegated to ``app.rendering.legacy`` lazily.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.services.auth_deps import require_user
from app.services.repositories.factory import get_resume_repository

router = APIRouter()


@router.post("/resume/{resume_id}/pdf")
async def create_pdf(resume_id: str, template: str = Query(default="executive"), current_user=Depends(require_user)):
    """LEGACY COMPATIBILITY — generate a legacy ReportLab PDF for a resume."""
    from app.rendering.legacy.pdf import generate_legacy_pdf

    resume = get_resume_repository().get_by_id(resume_id, getattr(current_user, "id", None))
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")

    try:
        generate_legacy_pdf(resume_id, resume, template)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "success": True,
        "template": template,
        "downloadUrl": f"/api/v1/resume/{resume_id}/pdf/download",
    }


@router.get("/resume/{resume_id}/pdf/download")
async def download_pdf(resume_id: str, current_user=Depends(require_user)):
    """LEGACY COMPATIBILITY — serve a generated legacy PDF."""
    from app.rendering.legacy.pdf import pdf_dir

    path = pdf_dir() / f"{resume_id}.pdf"
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF not found. Generate it first.")
    resume = get_resume_repository().get_by_id(resume_id, getattr(current_user, "id", None))
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    name_slug = resume.full_name.lower().replace(" ", "_") if resume else resume_id
    safe_name = "".join(c for c in name_slug if c.isalnum() or c in "_-")
    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=f"resume_{safe_name}.pdf",
    )


@router.get("/templates")
async def list_templates():
    """LEGACY COMPATIBILITY — list the legacy ReportLab template names."""
    from app.rendering.legacy.pdf import list_legacy_template_names

    return {"success": True, "data": list_legacy_template_names()}
