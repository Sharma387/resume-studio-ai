from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.models.cover_letter import CoverLetterRequest, CoverLetter
from app.services.storage_service import load_resume, load_cover_letter, list_cover_letters, delete_cover_letter
from app.services.cover_letter_service import generate, update, regenerate
from app.services.cover_letter_pdf import generate_cover_letter_pdf, PDF_DIR

router = APIRouter()


@router.post("/resume/{resume_id}/cover-letter")
async def create_cover_letter(resume_id: str, request: CoverLetterRequest):
    try:
        letter = await generate(resume_id, request)
        return {"success": True, "data": letter}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Resume not found")
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/resume/{resume_id}/cover-letters")
async def list_letters(resume_id: str):
    letters = list_cover_letters(resume_id)
    return {"success": True, "data": [l.model_dump() for l in letters]}


@router.get("/resume/{resume_id}/cover-letter/{letter_id}")
async def get_letter(resume_id: str, letter_id: str):
    letter = load_cover_letter(resume_id, letter_id)
    if letter is None:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    return {"success": True, "data": letter}


@router.put("/resume/{resume_id}/cover-letter/{letter_id}")
async def update_letter(resume_id: str, letter_id: str, body: CoverLetter):
    try:
        letter = await update(resume_id, letter_id, body.content, body.subject)
        return {"success": True, "data": letter}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Cover letter not found")


@router.delete("/resume/{resume_id}/cover-letter/{letter_id}")
async def delete_letter(resume_id: str, letter_id: str):
    if not delete_cover_letter(resume_id, letter_id):
        raise HTTPException(status_code=404, detail="Cover letter not found")
    return {"success": True}


@router.get("/resume/{resume_id}/cover-letter/{letter_id}/pdf")
async def export_letter_pdf(resume_id: str, letter_id: str):
    letter = load_cover_letter(resume_id, letter_id)
    if letter is None:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    resume = load_resume(resume_id)
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
async def regenerate_letter(resume_id: str, letter_id: str):
    try:
        letter = await regenerate(resume_id, letter_id)
        return {"success": True, "data": letter}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
