"""Resume Variants and Template Recommendation API."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from app.models.user import User
from app.rendering.layout.layout_config import LayoutConfig
from app.services.ai_optimizer import optimize as ai_optimize
from app.services.ai_optimizer import target_for_job
from app.services.auth_deps import require_user
from app.services.layout_config_service import get_layout_config as get_persisted_layout_config
from app.services.layout_config_service import set_layout_config as set_persisted_layout_config
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


# ── Layout configuration (persisted in resume_variants.customization) ────────


class LayoutConfigUpdateRequest(BaseModel):
    """Body for persisting a validated :class:`LayoutConfig`.

    Unknown fields are rejected so a typo can never silently become an extra
    key inside the stored ``customization`` namespace.
    """

    model_config = ConfigDict(extra="forbid")

    config: LayoutConfig


@router.get("/resume/{resume_id}/layout-config")
async def get_resume_layout_config(resume_id: str, current_user: User = Depends(require_user)):
    """Return the persisted layout configuration for a resume (``{}`` if unset)."""
    resume = get_resume_repository().get_by_id(resume_id, current_user.id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    return {
        "success": True,
        "data": {"layout_config": get_persisted_layout_config(resume_id, current_user.id)},
    }


@router.put("/resume/{resume_id}/layout-config")
async def set_resume_layout_config(
    resume_id: str,
    body: LayoutConfigUpdateRequest,
    current_user: User = Depends(require_user),
):
    """Persist a layout configuration under ``resume_variants.customization``.

    Always writes the full, normalized ``LayoutConfig`` payload namespaced as
    ``{"layout_config": {...}}``; unrelated customization keys are preserved.
    """
    resume = get_resume_repository().get_by_id(resume_id, current_user.id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    stored = set_persisted_layout_config(
        resume_id, current_user.id, body.config.model_dump(mode="json", exclude_none=True)
    )
    return {"success": True, "data": {"layout_config": stored}}


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
