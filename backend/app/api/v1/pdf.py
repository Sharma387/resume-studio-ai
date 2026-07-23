from fastapi import Depends,  APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.services.storage_service import load_resume
from app.services.pdf_service import generate_pdf, PDF_DIR
from app.services.pdf_templates.registry import TemplateRegistry
from app.services.auth_deps import require_user

router = APIRouter()


@router.post("/resume/{resume_id}/pdf")
async def create_pdf(resume_id: str, template: str = Query(default="executive", description="PDF template name")):
    resume = load_resume(resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")

    try:
        generate_pdf(resume_id, resume, template)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "success": True,
        "template": template,
        "downloadUrl": f"/api/v1/resume/{resume_id}/pdf/download",
    }


@router.get("/resume/{resume_id}/pdf/download")
async def download_pdf(resume_id: str, _ = Depends(require_user)):
    path = PDF_DIR / f"{resume_id}.pdf"
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF not found. Generate it first.")
    resume = load_resume(resume_id)
    name_slug = resume.full_name.lower().replace(" ", "_") if resume else resume_id
    safe_name = "".join(c for c in name_slug if c.isalnum() or c in "_-")
    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=f"resume_{safe_name}.pdf",
    )


@router.get("/templates")
async def list_templates():
    return {"success": True, "data": TemplateRegistry.list_names()}
