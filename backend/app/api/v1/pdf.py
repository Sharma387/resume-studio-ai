from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services.storage_service import load_resume
from app.services.pdf_service import generate_pdf, PDF_DIR

router = APIRouter()


@router.post("/resume/{resume_id}/pdf")
async def create_pdf(resume_id: str):
    resume = load_resume(resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    generate_pdf(resume_id, resume)
    return {
        "success": True,
        "downloadUrl": f"/api/v1/resume/{resume_id}/pdf/download",
    }


@router.get("/resume/{resume_id}/pdf/download")
async def download_pdf(resume_id: str):
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
