"""Resume Designer API — version history, autosave, ATS analysis, design recommendations."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.models.user import User
from app.services.ats_scoring import analyze as analyze_ats
from app.services.auth_deps import require_user
from app.services.recommendation_service import recommend as recommend_templates
from app.services.repositories.factory import get_resume_repository
from app.services.version_history import autosave, get_autosave, list_versions, save_version

router = APIRouter()


class SaveVersionRequest(BaseModel):
    resume_data: dict
    label: str | None = None


@router.post("/designer/{variant_id}/versions")
async def create_version(variant_id: str, body: SaveVersionRequest,
                          current_user: User = Depends(require_user)):
    version = save_version(variant_id, body.resume_data, body.label)
    return {"success": True, "data": version}


@router.get("/designer/{variant_id}/versions")
async def get_versions(variant_id: str, current_user: User = Depends(require_user)):
    return {"success": True, "data": list_versions(variant_id)}


@router.post("/designer/{variant_id}/autosave")
async def save_autosave(variant_id: str, body: SaveVersionRequest,
                         current_user: User = Depends(require_user)):
    autosave(variant_id, body.resume_data)
    return {"success": True}


@router.get("/designer/{variant_id}/autosave")
async def load_autosave(variant_id: str, current_user: User = Depends(require_user)):
    data = get_autosave(variant_id)
    return {"success": True, "data": data}


@router.get("/resume/{resume_id}/ats")
async def get_ats_analysis(resume_id: str, current_user: User = Depends(require_user)):
    resume = get_resume_repository().get_by_id(resume_id, current_user.id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    return {"success": True, "data": analyze_ats(resume)}


@router.post("/designer/{variant_id}/optimize")
async def get_design_recommendations(variant_id: str, body: dict,
                                      current_user: User = Depends(require_user)):
    resume_data = body.get("resume_data", {})
    from app.models.resume import Resume
    resume = Resume(**resume_data)
    ats = analyze_ats(resume)
    recs = recommend_templates(resume)
    return {"success": True, "data": {"ats": ats, "recommended_templates": recs}}
