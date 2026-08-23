"""Configuration diagnostics — safe, read-only health checks for all subsystems.

Never exposes secrets. All sensitive values are masked or reported as booleans.
"""

from app.core.config import settings
from app.core.logging import get_logger
from app.services.development_features import development_features

logger = get_logger(__name__)


def _mask(s: str, keep: int = 4) -> str:
    """Mask a sensitive string, showing only the last `keep` characters."""
    if not s:
        return ""
    if len(s) <= keep:
        return "*" * len(s)
    return "*" * (len(s) - keep) + s[-keep:]


def check_jwt() -> dict:
    return {
        "configured": bool(settings.jwt_secret_key),
        "secure": settings.jwt_secret_secure,
        "length_requirement": 32,
        "algorithm": settings.jwt_algorithm,
        "access_token_expiry_minutes": settings.jwt_access_expire_minutes,
        "refresh_token_expiry_days": settings.jwt_refresh_expire_days,
    }


def check_database() -> dict:
    connected = False
    migration_current = None
    if settings.database_url and settings.storage_backend == "postgres":
        try:
            from sqlalchemy import text

            from app.db.database import get_sync_session

            session = get_sync_session()
            session.execute(text("SELECT 1"))
            connected = True
            row = session.execute(text("SELECT version_num FROM alembic_version")).fetchone()
            migration_current = row[0] if row else None
            session.close()
        except Exception as e:
            logger.warning("Database diagnostics check failed", error=str(e))

    return {
        "configured": bool(settings.database_url),
        "connected": connected,
        "migration_current": migration_current,
    }


async def check_ai() -> dict:
    from app.services.omniroute_service import check_ai_connection

    connected = await check_ai_connection()
    return {
        "configured": bool(settings.omniroute_api_url),
        "connected": connected,
        "model": settings.omniroute_model,
        "mock_mode": development_features.mock_ai,
    }


def check_storage() -> dict:
    return {
        "backend": settings.storage_backend,
        "json_backend_available": True,
        "postgres_backend_available": bool(settings.database_url),
    }


def check_environment() -> dict:
    return {
        "debug": settings.debug,
        "allow_mock_ai_data": settings.allow_mock_ai_data,
        "development_mode": development_features.debug_enabled,
        "storage_backend": settings.storage_backend,
    }


async def get_all() -> dict:
    return {
        "jwt": check_jwt(),
        "database": check_database(),
        "ai": await check_ai(),
        "storage": check_storage(),
        "environment": check_environment(),
    }
