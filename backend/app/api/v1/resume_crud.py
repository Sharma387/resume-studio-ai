from fastapi import APIRouter, HTTPException

from app.models.resume import Resume
from app.services.storage_service import save_resume, load_resume

router = APIRouter()


@router.get("/resume/{resume_id}")
async def get_resume(resume_id: str):
    resume = load_resume(resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    return {"success": True, "data": resume}


@router.put("/resume/{resume_id}")
async def update_resume(resume_id: str, resume: Resume):
    save_resume(resume_id, resume)
    return {"success": True, "data": resume}
