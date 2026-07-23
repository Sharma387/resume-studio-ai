from fastapi import Depends,  APIRouter, HTTPException

from app.models.writer import WriterRequest, BulkAcceptRequest
from app.services.writer_service import (
    suggest,
    accept_suggestion,
    reject_suggestion,
    regenerate_suggestion,
    QUICK_ACTIONS,
)
from app.services.storage_service import list_writer_suggestions
from app.services.auth_deps import require_user

router = APIRouter()


@router.get("/resume/{resume_id}/writer/quick-actions")
async def get_quick_actions():
    return {"success": True, "data": QUICK_ACTIONS}


@router.post("/resume/{resume_id}/writer/suggest")
async def create_suggestions(resume_id: str, request: WriterRequest, _ = Depends(require_user)):
    try:
        suggestions = await suggest(resume_id, request)
        return {"success": True, "suggestions": [s.model_dump() for s in suggestions]}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Resume not found")
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/resume/{resume_id}/writer/suggestions")
async def list_suggestions(resume_id: str, status: str | None = None, _ = Depends(require_user)):
    suggestions = list_writer_suggestions(resume_id, status=status)
    return {"success": True, "data": [s.model_dump() for s in suggestions]}


@router.post("/resume/{resume_id}/writer/suggestions/{suggestion_id}/accept")
async def accept(resume_id: str, suggestion_id: str, _ = Depends(require_user)):
    try:
        resume = await accept_suggestion(resume_id, suggestion_id)
        return {"success": True, "data": resume}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/resume/{resume_id}/writer/suggestions/{suggestion_id}/reject")
async def reject(resume_id: str, suggestion_id: str, _ = Depends(require_user)):
    try:
        await reject_suggestion(resume_id, suggestion_id)
        return {"success": True}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/resume/{resume_id}/writer/suggestions/{suggestion_id}/regenerate")
async def regenerate(resume_id: str, suggestion_id: str, _ = Depends(require_user)):
    try:
        suggestion = await regenerate_suggestion(resume_id, suggestion_id)
        return {"success": True, "data": suggestion.model_dump()}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
