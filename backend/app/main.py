from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.admin import router as admin_router
from app.api.v1.applications import router as applications_router
from app.api.v1.auth import router as auth_router
from app.api.v1.cover_letter import router as cover_letter_router
from app.api.v1.designer import router as designer_router
from app.api.v1.export import router as export_router
from app.api.v1.extract import router as extract_router
from app.api.v1.health import router as health_router
from app.api.v1.interviews import router as interviews_router
from app.api.v1.job_match import router as job_match_router
from app.api.v1.parse import router as parse_router
from app.api.v1.pdf import router as pdf_router
from app.api.v1.rendering import router as rendering_router
from app.api.v1.resume_crud import router as resume_crud_router
from app.api.v1.suggestions import router as suggestions_router
from app.api.v1.upload import router as upload_router
from app.api.v1.variants import router as variants_router
from app.api.v1.writer import router as writer_router
from app.core.config import settings
from app.core.error_handler import setup_error_handlers
from app.core.logging import get_logger, setup_logging
from app.core.middleware.request_id import RequestIDMiddleware, TimingMiddleware
from app.core.middleware.security import SecurityHeadersMiddleware

setup_logging(json_mode=settings.debug is False)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    issues: list[str] = []

    # JWT validation
    if not settings.jwt_secret_key:
        issues.append("JWT_SECRET_KEY is missing")
    elif not settings.jwt_secret_secure:
        issues.append("JWT_SECRET_KEY too short (min 32 chars)")

    if issues:
        for issue in issues:
            logger.error("Configuration validation failed", component="Startup", issue=issue)
        if not settings.debug:
            raise RuntimeError("Configuration validation failed")

    # Initialize database engine for PostgreSQL
    if settings.storage_backend == "postgres" and settings.database_url:
        from app.db.database import create_engine, dispose_engine

        await create_engine()
        logger.info("Database engine initialized")

    yield

    if settings.storage_backend == "postgres" and settings.database_url:
        from app.db.database import dispose_engine

        await dispose_engine()
        logger.info("Database engine disposed")


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

logger.info(
    "Application starting",
    storage_backend=settings.storage_backend,
)

# Middleware (order matters)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(TimingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handlers
setup_error_handlers(app)

# Routers
app.include_router(health_router, prefix="/api/v1")
app.include_router(upload_router, prefix="/api/v1")
app.include_router(extract_router, prefix="/api/v1")
app.include_router(parse_router, prefix="/api/v1")
app.include_router(rendering_router, prefix="/api/v1")
app.include_router(export_router, prefix="/api/v1")
app.include_router(resume_crud_router, prefix="/api/v1")
app.include_router(pdf_router, prefix="/api/v1")
app.include_router(job_match_router, prefix="/api/v1")
app.include_router(suggestions_router, prefix="/api/v1")
app.include_router(writer_router, prefix="/api/v1")
app.include_router(cover_letter_router, prefix="/api/v1")
app.include_router(applications_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(interviews_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(variants_router, prefix="/api/v1")
app.include_router(designer_router, prefix="/api/v1")
