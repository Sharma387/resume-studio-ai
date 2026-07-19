from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.extract import router as extract_router
from app.api.v1.health import router as health_router
from app.api.v1.parse import router as parse_router
from app.api.v1.upload import router as upload_router
from app.core.config import settings
from app.core.logging import setup_logging

setup_logging()

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(upload_router, prefix="/api/v1")
app.include_router(extract_router, prefix="/api/v1")
app.include_router(parse_router, prefix="/api/v1")
