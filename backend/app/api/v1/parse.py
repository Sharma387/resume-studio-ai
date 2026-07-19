from fastapi import APIRouter
from pydantic import BaseModel

from app.services.parser_service import parse_resume
from app.models.resume import Resume

router = APIRouter()


class ParseRequest(BaseModel):
    text: str


class ParseResponse(BaseModel):
    success: bool
    data: Resume


@router.post("/parse", response_model=ParseResponse)
async def parse(req: ParseRequest):
    resume = await parse_resume(req.text)
    return ParseResponse(success=True, data=resume)
