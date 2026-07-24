from fastapi import Depends,  APIRouter, HTTPException

from app.models.match import JobDescription, MatchResult

from app.services.matching_service import analyze_match
from app.services.auth_deps import require_user
from app.services.repositories.factory import get_resume_repository, get_match_repository

router = APIRouter()

@router.post("/job-match")
async def create_job_match(job: JobDescription, current_user = Depends(require_user)):
    resume = get_resume_repository().get_by_id(job.resume_id, current_user.id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")

    result = await analyze_match(job.resume_id, job.job_title, job.description, resume, current_user.id)
    get_match_repository().save(result.id, result)
    return {"success": True, "data": result}

@router.get("/job-match/{match_id}")
async def get_job_match(match_id: str, current_user = Depends(require_user)):
    result = get_match_repository().get_by_id(match_id, current_user.id)
    if result is None:
        raise HTTPException(status_code=404, detail="Match not found")
    return {"success": True, "data": result}
