import uuid
from pathlib import Path

from fastapi import UploadFile, HTTPException

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

MAX_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf"}
ALLOWED_MIMETYPES = {"application/pdf"}


class UploadResult:
    def __init__(self, filename: str, original_name: str, size: int):
        self.filename = filename
        self.original_name = original_name
        self.size = size

    def to_dict(self) -> dict:
        return {
            "success": True,
            "filename": self.filename,
            "original_name": self.original_name,
            "size": self.size,
        }


def validate_upload(file: UploadFile) -> None:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file extension '{ext}'. Only PDF files are allowed.",
        )

    if file.content_type not in ALLOWED_MIMETYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file.content_type}'. Only PDF files are allowed.",
        )


async def store_upload(file: UploadFile) -> UploadResult:
    validate_upload(file)

    content = await file.read()

    if len(content) > MAX_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File exceeds the maximum allowed size of 10MB.",
        )

    ext = Path(file.filename or "resume.pdf").suffix.lower()
    filename = f"{uuid.uuid4().hex}{ext}"
    dest = UPLOAD_DIR / filename
    dest.write_bytes(content)

    return UploadResult(
        filename=filename,
        original_name=file.filename or "resume.pdf",
        size=len(content),
    )
