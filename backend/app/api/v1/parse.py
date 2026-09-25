import uuid
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.models.resume import Resume
from app.models.user import User
from app.services.auth_deps import require_user
from app.services.parser_service import parse_resume
from app.services.repositories.factory import get_resume_repository

router = APIRouter()


class ParseRequest(BaseModel):
    text: str
    filename: str | None = None


class ParseResponse(BaseModel):
    success: bool
    id: str | None = None
    data: Resume


@router.post("/parse", response_model=ParseResponse)
async def parse(req: ParseRequest, current_user: User = Depends(require_user)):
    resume = await parse_resume(req.text)
    resume.user_id = current_user.id
    
    # Generate resume_id from filename or create a UUID
    if req.filename:
        resume_id = Path(req.filename).stem
    else:
        resume_id = uuid.uuid4().hex
    
    get_resume_repository().save(resume_id, resume)
    return ParseResponse(success=True, id=resume_id, data=resume)
