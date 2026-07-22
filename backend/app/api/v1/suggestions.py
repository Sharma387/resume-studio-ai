import uuid

from fastapi import APIRouter, HTTPException

from app.models.match import Recommendation
from app.models.resume import Resume
from app.models.version import ResumeVersion
from app.services.storage_service import load_resume, save_resume, save_version, load_version, list_versions
from app.services.suggestion_service import apply_suggestion

router = APIRouter()


@router.post("/resume/{resume_id}/preview-suggestion")
async def preview_suggestion(resume_id: str, recommendation: Recommendation):
    resume = load_resume(resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    modified = await apply_suggestion(resume, recommendation)
    return {"success": True, "data": {"original": resume, "modified": modified}}


@router.post("/resume/{resume_id}/apply-suggestion")
async def apply_suggestion_endpoint(resume_id: str, recommendation: Recommendation):
    resume = load_resume(resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")

    modified = await apply_suggestion(resume, recommendation)
    save_resume(resume_id, modified)

    version = ResumeVersion(
        id=uuid.uuid4().hex,
        resume_id=resume_id,
        label=f"Applied: {recommendation.section} - {recommendation.message[:60]}",
        resume=modified,
    )
    save_version(version)

    return {"success": True, "data": {"version": version, "resume": modified}}


@router.post("/resume/{resume_id}/versions")
async def create_version(resume_id: str, label: str | None = None):
    resume = load_resume(resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    version = ResumeVersion(id=uuid.uuid4().hex, resume_id=resume_id, label=label, resume=resume)
    save_version(version)
    return {"success": True, "data": version}


@router.get("/resume/{resume_id}/versions")
async def get_versions(resume_id: str):
    versions = list_versions(resume_id)
    return {"success": True, "data": versions}


@router.get("/resume/{resume_id}/versions/{version_id}")
async def get_version(resume_id: str, version_id: str):
    version = load_version(resume_id, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return {"success": True, "data": version}


@router.post("/resume/{resume_id}/versions/{version_id}/restore")
async def restore_version(resume_id: str, version_id: str):
    version = load_version(resume_id, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")
    save_resume(resume_id, version.resume)
    return {"success": True, "data": version.resume}
