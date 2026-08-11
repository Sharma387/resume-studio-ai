"""Resume Variants and Template Recommendation API."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.models.user import User
from app.services.ai_optimizer import optimize as ai_optimize
from app.services.ai_optimizer import target_for_job
from app.services.auth_deps import require_user
from app.services.recommendation_service import recommend
from app.services.repositories.factory import get_resume_repository
from app.services.resume_variants.service import create as create_variant
from app.services.resume_variants.service import get as get_variant
from app.services.resume_variants.service import list_by_user

router = APIRouter()


@router.get("/resume/{resume_id}/recommendations")
async def get_recommendations(resume_id: str, current_user: User = Depends(require_user)):
    """Get AI template recommendations for a resume."""
    resume = get_resume_repository().get_by_id(resume_id, current_user.id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    recs = recommend(resume)
    return {"success": True, "data": recs}


class VariantCreateRequest(BaseModel):
    name: str
    template_id: str | None = None
    theme: str | None = None


@router.post("/resume/{resume_id}/variants")
async def create_resume_variant(resume_id: str, body: VariantCreateRequest,
                                 current_user: User = Depends(require_user)):
    resume = get_resume_repository().get_by_id(resume_id, current_user.id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    variant = create_variant(resume, current_user.id, body.name, body.template_id, body.theme)
    return {"success": True, "data": variant}


@router.get("/variants")
async def list_variants(current_user: User = Depends(require_user)):
    return {"success": True, "data": list_by_user(current_user.id)}


@router.get("/variants/{variant_id}")
async def get_resume_variant(variant_id: str, current_user: User = Depends(require_user)):
    variant = get_variant(variant_id)
    if variant is None or variant["user_id"] != current_user.id:
        raise HTTPException(status_code=404, detail="Variant not found")
    return {"success": True, "data": variant}


# ── AI Optimizer ────────────────────────────────────────────────────────────────


@router.post("/resume/{resume_id}/optimize")
async def optimize_resume(resume_id: str, current_user: User = Depends(require_user)):
    resume = get_resume_repository().get_by_id(resume_id, current_user.id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    return {"success": True, "data": ai_optimize(resume)}


class TargetJobRequest(BaseModel):
    job_description: str
    resume_id: str


@router.post("/resume/target-job")
async def target_resume_for_job(body: TargetJobRequest, current_user: User = Depends(require_user)):
    resume = get_resume_repository().get_by_id(body.resume_id, current_user.id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    result = target_for_job(resume, body.job_description)
    return {"success": True, "data": result}


class PdfExportRequest(BaseModel):
    resume_data: dict
    template_id: str = "executive-elite"
    theme: str | None = None
    page_size: str = "A4"


@router.post("/resume/{resume_id}/export-pdf")
async def export_resume_pdf(resume_id: str, body: PdfExportRequest,
                            current_user: User = Depends(require_user)):
    """Legacy PDF export kept for compatibility.

    Renders through the canonical RenderTree pipeline: the legacy
    ``template_id`` is resolved to its mapped ``layout_id`` and exported as
    PDF. The response contract (``download_url``) is unchanged.
    """
    import hashlib
    import json

    from app.models.resume import Resume as ResumeModel
    from app.rendering import legacy_templates
    from app.rendering.export_service import ExportFormat, ExportFormatError
    from app.rendering.export_service import export_resume as canonical_export
    from app.rendering.layout.layout_registry import LayoutLookupError
    from app.rendering.theme.theme_registry import ThemeLookupError
    from app.services.pdf_pipeline import PDF_OUTPUT_DIR

    try:
        resume = ResumeModel(**body.resume_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid resume data: {e}")

    try:
        layout_id = legacy_templates.resolve_legacy_template(body.template_id)
    except legacy_templates.UnknownLegacyTemplateError:
        raise HTTPException(status_code=400, detail=f"Template '{body.template_id}' not found")
    theme_id = body.theme or legacy_templates.DEFAULT_LEGACY_THEME

    try:
        result = canonical_export(
            resume,
            layout_id=layout_id,
            theme_id=theme_id,
            output_format=ExportFormat.PDF,
        )
    except (LayoutLookupError, ThemeLookupError):
        raise HTTPException(status_code=404, detail=f"Template '{body.template_id}' not found")
    except ExportFormatError as e:
        raise HTTPException(status_code=400, detail=str(e))

    filename = hashlib.md5(json.dumps(body.resume_data, sort_keys=True).encode()).hexdigest()[:16]
    try:
        output_path = PDF_OUTPUT_DIR / f"{filename}.pdf"
        output_path.write_bytes(result.content)
        return {"success": True, "data": {"download_url": f"/api/v1/resume/export/{filename}.pdf"}}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"PDF generation failed: {e}")


@router.get("/resume/export/{filename}")
async def download_export(filename: str, current_user: User = Depends(require_user)):
    """Serve a generated legacy export artifact (authenticated).

    The filename must be a plain artifact name inside the PDF output
    directory. Any path separator, dotfile, or path resolving outside the
    directory is rejected — no traversal, no directory listing.
    """
    from app.services.pdf_pipeline import PDF_OUTPUT_DIR

    if (
        "/" in filename
        or "\\" in filename
        or filename in (".", "..")
        or filename.startswith(".")
    ):
        raise HTTPException(status_code=404, detail="File not found")

    base = PDF_OUTPUT_DIR.resolve()
    path = (PDF_OUTPUT_DIR / filename).resolve()
    if not path.is_relative_to(base) or not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    from fastapi.responses import FileResponse

    return FileResponse(str(path), media_type="application/pdf", filename=filename)
