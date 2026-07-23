from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.extract import router as extract_router
from app.api.v1.health import router as health_router
from app.api.v1.job_match import router as job_match_router
from app.api.v1.parse import router as parse_router
from app.api.v1.pdf import router as pdf_router
from app.api.v1.resume_crud import router as resume_crud_router
from app.api.v1.suggestions import router as suggestions_router
from app.api.v1.upload import router as upload_router
from app.api.v1.cover_letter import router as cover_letter_router
from app.api.v1.applications import router as applications_router
from app.api.v1.auth import router as auth_router
from app.api.v1.workspace import router as workspace_router
from app.api.v1.interviews import router as interviews_router
from app.api.v1.writer import router as writer_router
from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.error_handler import setup_error_handlers
from app.core.middleware.request_id import RequestIDMiddleware, TimingMiddleware
from app.core.middleware.security import SecurityHeadersMiddleware

setup_logging(json_mode=settings.debug is False)
logger = get_logger(__name__)

app = FastAPI(title=settings.app_name, version=settings.app_version)

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
app.include_router(resume_crud_router, prefix="/api/v1")
app.include_router(pdf_router, prefix="/api/v1")
app.include_router(job_match_router, prefix="/api/v1")
app.include_router(suggestions_router, prefix="/api/v1")
app.include_router(writer_router, prefix="/api/v1")
app.include_router(cover_letter_router, prefix="/api/v1")
app.include_router(applications_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(interviews_router, prefix="/api/v1")
app.include_router(workspace_router, prefix="/api/v1")
