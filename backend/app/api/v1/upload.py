from fastapi import APIRouter, Depends, UploadFile

from app.services.auth_deps import require_user
from app.services.upload_service import store_upload

router = APIRouter()


@router.post("/upload")
async def upload_resume(file: UploadFile, _=Depends(require_user)):
    result = await store_upload(file)
    return result.to_dict()
