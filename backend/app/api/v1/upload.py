from fastapi import APIRouter, UploadFile, Depends

from app.services.upload_service import store_upload
from app.services.auth_deps import require_user

router = APIRouter()


@router.post("/upload")
async def upload_resume(file: UploadFile, _ = Depends(require_user)):
    result = await store_upload(file)
    return result.to_dict()
