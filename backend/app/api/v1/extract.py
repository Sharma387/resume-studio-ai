from fastapi import APIRouter, HTTPException

from pydantic import BaseModel

from app.services.extract_service import extract_pdf

router = APIRouter()


class ExtractRequest(BaseModel):
    filename: str


@router.post("/extract")
async def extract(req: ExtractRequest):
    try:
        result = extract_pdf(req.filename)
        return result.to_dict()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to extract text from PDF. The file may be corrupt.")
