import uuid

from fastapi import Depends,  APIRouter, HTTPException

from app.models.match import Recommendation
from app.models.resume import Resume
from app.models.version import ResumeVersion

from app.services.suggestion_service import apply_suggestion
from app.services.auth_deps import require_user
from app.services.repositories.factory import get_resume_repository, get_version_repository

router = APIRouter()

@router.post("/resume/{resume_id}/preview-suggestion")
async def preview_suggestion(resume_id: str, recommendation: Recommendation, current_user = Depends(require_user)):
    resume = get_resume_repository().get_by_id(resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    modified = await apply_suggestion(resume, recommendation)
    return {"success": True, "data": {"original": resume, "modified": modified}}

@router.post("/resume/{resume_id}/apply-suggestion")
async def apply_suggestion_endpoint(resume_id: str, recommendation: Recommendation, current_user = Depends(require_user)):
    resume = get_resume_repository().get_by_id(resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")

    modified = await apply_suggestion(resume, recommendation)
    get_resume_repository().save(resume_id, modified)

    version = ResumeVersion(
        id=uuid.uuid4().hex,
        user_id=current_user.id,
        resume_id=resume_id,
        label=f"Applied: {recommendation.section} - {recommendation.message[:60]}",
        resume=modified,
    )
    get_version_repository().save(version)

    return {"success": True, "data": {"version": version, "resume": modified}}

@router.post("/resume/{resume_id}/versions")
async def create_version(resume_id: str, label: str | None = None, current_user = Depends(require_user)):
    resume = get_resume_repository().get_by_id(resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    version = ResumeVersion(id=uuid.uuid4().hex, user_id=current_user.id, resume_id=resume_id, label=label, resume=resume)
    get_version_repository().save(version)
    return {"success": True, "data": version}

@router.get("/resume/{resume_id}/versions")
async def get_versions(resume_id: str, current_user = Depends(require_user)):
    versions = get_version_repository().list_by_resume(resume_id)
    return {"success": True, "data": versions}

@router.get("/resume/{resume_id}/versions/{version_id}")
async def get_version(resume_id: str, version_id: str, current_user = Depends(require_user)):
    version = get_version_repository().get_by_id(resume_id, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return {"success": True, "data": version}

@router.post("/resume/{resume_id}/versions/{version_id}/restore")
async def restore_version(resume_id: str, version_id: str, current_user = Depends(require_user)):
    version = get_version_repository().get_by_id(resume_id, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")
    get_resume_repository().save(resume_id, version.resume)
    return {"success": True, "data": version.resume}
