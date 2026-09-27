"""Global test configuration."""

from pathlib import Path

import pytest

from app.core.config import settings
from app.services.ai_core import AIServiceUnavailable
from app.services.omniroute_service import OmniRouteError

# Enable debug mode so auth dependency auto-creates a mock user
settings.debug = True

# Tests use JSON backend by default (no PostgreSQL dependency required)
settings.storage_backend = "json"

# Ensure DATABASE_URL is set for admin service connectivity checks
if not settings.database_url:
    settings.database_url = "postgresql://rsai:rsai@localhost:5432/rsai"


# ── AI provider isolation ─────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _disable_local_ollama(monkeypatch):
    """Never contact a real local Ollama server during tests.

    The provider router defaults to Ollama-first; tests force the OmniRoute
    path (which individual tests mock) so runs are deterministic and fast.
    Both real providers are stubbed out: the local OmniRoute gateway accepts
    the request and can then hold it open for many minutes before returning
    504, so any test reaching it un-mocked stalled the whole suite.
    AI PDF OCR is a local model call too, so it is disabled here as well —
    otherwise extracting a short PDF would try to load a multi-GB model and
    hang the run. Tests that exercise OCR re-enable it themselves.
    """

    async def _no_ollama() -> None:
        return None

    async def _no_omniroute(*args, **kwargs):
        raise AIServiceUnavailable("omniroute disabled during tests")

    monkeypatch.setattr("app.services.ollama_service.detect_ollama_model", _no_ollama)
    monkeypatch.setattr("app.services.ollama_service.call_with_retry", _no_omniroute)
    monkeypatch.setattr(settings, "pdf_ai_ocr_fallback", False)

    # The local OmniRoute gateway is reachable but can hold a request open for
    # many minutes, so block it at the transport too. Unit tests of the service
    # itself patch the client and are unaffected.
    async def _no_gateway(*args, **kwargs):
        raise OmniRouteError("omniroute disabled during tests")

    monkeypatch.setattr("app.services.omniroute_service.OmniRouteService.send_prompt", _no_gateway)


# ── JSON storage cleanup between test runs ────────────────────────────────────

_STORAGE_DIRS = [Path("storage") / "users", Path("storage") / "refresh_tokens"]


@pytest.fixture(autouse=True)
def _clean_json_storage():
    """Remove stale JSON storage files before each test to prevent cross-test contamination."""
    for d in _STORAGE_DIRS:
        if d.exists():
            for f in d.glob("*.json"):
                f.unlink()


# ── PostgreSQL engine lifecycle for integration tests ─────────────────────────


@pytest.fixture(scope="session", autouse=True)
def _pg_engine():
    """Initialise the sync database engine once per test session when DATABASE_URL is available.

    This mirrors what the FastAPI lifespan does at startup, giving PostgreSQL
    integration tests a working ``_sync_session_factory``.
    """
    from sqlalchemy import create_engine as _create_sync_engine
    from sqlalchemy.orm import Session, sessionmaker

    import app.db.database as db_mod

    url = settings.database_url
    if not url:
        yield
        return

    sync_url = url
    if sync_url.startswith("postgresql+asyncpg://"):
        sync_url = sync_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)

    db_mod._sync_engine = _create_sync_engine(sync_url, pool_pre_ping=True)
    db_mod._sync_session_factory = sessionmaker(bind=db_mod._sync_engine, class_=Session, expire_on_commit=False)

    yield

    if db_mod._sync_engine is not None:
        db_mod._sync_engine.dispose()
    db_mod._sync_engine = None
    db_mod._sync_session_factory = None
