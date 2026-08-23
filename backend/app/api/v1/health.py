from fastapi import APIRouter

from app.core.config import settings
from app.db.database import check_database_connection
from app.services.omniroute_service import check_ai_connection

router = APIRouter()


@router.get("/health")
async def health():
    backend = settings.storage_backend
    db_connected = None
    if backend == "postgres":
        db_connected = await check_database_connection()

    ai_connected = await check_ai_connection()

    response = {
        "status": "healthy",
        "version": settings.app_version,
        "storage_backend": backend,
        "ai_service_connected": ai_connected,
    }
    if backend == "postgres":
        response["database_connected"] = db_connected
    return response
