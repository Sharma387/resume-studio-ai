from fastapi import Depends,  APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.models.cover_letter import CoverLetterRequest, CoverLetter

from app.services.cover_letter_service import generate, update, regenerate
from app.services.cover_letter_pdf import generate_cover_letter_pdf, PDF_DIR
from app.services.auth_deps import require_user
from app.services.repositories.factory import get_cover_letter_repository, get_resume_repository

router = APIRouter()

@router.post("/resume/{resume_id}/cover-letter")
async def create_cover_letter(resume_id: str, request: CoverLetterRequest, current_user = Depends(require_user)):
    try:
        letter = await generate(resume_id, request, current_user.id)
        return {"success": True, "data": letter}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Resume not found")
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.get("/resume/{resume_id}/cover-letters")
async def list_letters(resume_id: str, current_user = Depends(require_user)):
    letters = get_cover_letter_repository().list_by_resume(resume_id, current_user.id)
    return {"success": True, "data": [l.model_dump() for l in letters]}

@router.get("/resume/{resume_id}/cover-letter/{letter_id}")
async def get_letter(resume_id: str, letter_id: str, current_user = Depends(require_user)):
    letter = get_cover_letter_repository().get_by_id(resume_id, letter_id, current_user.id)
    if letter is None:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    return {"success": True, "data": letter}

@router.put("/resume/{resume_id}/cover-letter/{letter_id}")
async def update_letter(resume_id: str, letter_id: str, body: CoverLetter, current_user = Depends(require_user)):
    try:
        letter = await update(resume_id, letter_id, body.content, body.subject)
        return {"success": True, "data": letter}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Cover letter not found")

@router.delete("/resume/{resume_id}/cover-letter/{letter_id}")
async def delete_letter(resume_id: str, letter_id: str, current_user = Depends(require_user)):
    if not get_cover_letter_repository().delete(resume_id, letter_id, current_user.id):
        raise HTTPException(status_code=404, detail="Cover letter not found")
    return {"success": True}

@router.get("/resume/{resume_id}/cover-letter/{letter_id}/pdf")
async def export_letter_pdf(resume_id: str, letter_id: str, current_user = Depends(require_user)):
    letter = get_cover_letter_repository().get_by_id(resume_id, letter_id, current_user.id)
    if letter is None:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    resume = get_resume_repository().get_by_id(resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")

    path = generate_cover_letter_pdf(resume_id, letter_id, letter, resume)
    name_slug = resume.full_name.lower().replace(" ", "_") if resume else letter_id
    safe_name = "".join(c for c in name_slug if c.isalnum() or c in "_-")
    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=f"cover_letter_{safe_name}.pdf",
    )

@router.post("/resume/{resume_id}/cover-letter/{letter_id}/regenerate")
async def regenerate_letter(resume_id: str, letter_id: str, current_user = Depends(require_user)):
    try:
        letter = await regenerate(resume_id, letter_id)
        return {"success": True, "data": letter}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
