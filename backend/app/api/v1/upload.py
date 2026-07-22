from fastapi import APIRouter, UploadFile

from app.services.upload_service import store_upload

router = APIRouter()


@router.post("/upload")
async def upload_resume(file: UploadFile):
    result = await store_upload(file)
    return result.to_dict()
