from fastapi import Depends,  APIRouter, HTTPException

from app.models.match import JobDescription, MatchResult
from app.services.storage_service import save_match, load_match, load_resume
from app.services.matching_service import analyze_match
from app.services.auth_deps import require_user

router = APIRouter()


@router.post("/job-match")
async def create_job_match(job: JobDescription, current_user = Depends(require_user)):
    resume = load_resume(job.resume_id, current_user.id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")

    result = await analyze_match(job.resume_id, job.job_title, job.description, resume, current_user.id)
    save_match(result)
    return {"success": True, "data": result}


@router.get("/job-match/{match_id}")
async def get_job_match(match_id: str, current_user = Depends(require_user)):
    result = load_match(match_id, current_user.id)
    if result is None:
        raise HTTPException(status_code=404, detail="Match not found")
    return {"success": True, "data": result}
