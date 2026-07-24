from fastapi import Depends,  APIRouter, HTTPException

from app.models.resume import Resume

from app.services.auth_deps import require_user
from app.services.repositories.factory import get_resume_repository

router = APIRouter()

@router.get("/resumes")
async def list_my_resumes(current_user = Depends(require_user)):
    items = get_resume_repository().list_by_user(current_user.id, 10)
    return {"success": True, "data": [{"id": rid, **r.model_dump()} for rid, r in items]}

@router.get("/resume/{resume_id}")
async def get_resume(resume_id: str, current_user = Depends(require_user)):
    resume = get_resume_repository().get_by_id(resume_id, getattr(current_user, "id", None))
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    return {"success": True, "data": resume}

@router.put("/resume/{resume_id}")
async def update_resume(resume_id: str, resume: Resume, current_user = Depends(require_user)):
    get_resume_repository().save(resume_id, resume)
    return {"success": True, "data": resume}
