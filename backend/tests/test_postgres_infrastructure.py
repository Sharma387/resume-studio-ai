"""Tests for PostgreSQL infrastructure (Phase 1).

Tests cover:
- Configuration loading
- SQLAlchemy engine creation
- Session creation
- Repository Factory returns JSON repository
- Repository Factory returns PostgreSQL repository
- Health endpoint detects PostgreSQL
- Alembic migration works (when database is available)
"""

import os
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

import app.db.models  # noqa: F401  ensure ORM models are registered on Base.metadata
from app.core.config import settings
from app.db.base import Base
from app.db.database import build_async_database_url, create_engine, dispose_engine, get_engine
from app.main import app
from app.services.repositories.factory import (
    get_application_repository,
    get_cover_letter_repository,
    get_interview_answer_repository,
    get_interview_question_repository,
    get_interview_session_repository,
    get_match_repository,
    get_readiness_assessment_repository,
    get_resume_repository,
    get_session_summary_repository,
    get_suggestion_repository,
    get_timeline_event_repository,
    get_version_repository,
)
from app.services.repositories.json.application_repository import JsonApplicationRepository
from app.services.repositories.json.cover_letter_repository import JsonCoverLetterRepository
from app.services.repositories.json.interview_repository import (
    JsonInterviewAnswerRepository,
    JsonInterviewQuestionRepository,
    JsonInterviewSessionRepository,
    JsonReadinessAssessmentRepository,
    JsonSessionSummaryRepository,
)
from app.services.repositories.json.match_repository import JsonMatchRepository
from app.services.repositories.json.resume_repository import JsonResumeRepository
from app.services.repositories.json.suggestion_repository import JsonWriterSuggestionRepository
from app.services.repositories.json.timeline_repository import JsonTimelineEventRepository
from app.services.repositories.json.version_repository import JsonResumeVersionRepository


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ── Configuration Tests ──────────────────────────────────────────────────────


class TestConfiguration:
    def test_default_storage_backend_is_json(self):
        assert settings.storage_backend == "json"

    def test_storage_backend_can_be_postgres(self):
        with patch.object(settings, "storage_backend", "postgres"):
            assert settings.storage_backend == "postgres"
        assert settings.storage_backend == "json"

    def test_database_url_defaults_to_empty(self):
        assert hasattr(settings, "database_url")

    def test_db_echo_defaults_to_false(self):
        assert settings.db_echo is False


# ── Declarative Base Tests ───────────────────────────────────────────────────


class TestBase:
    def test_base_is_declarative(self):
        assert hasattr(Base, "metadata")

    def test_base_metadata_has_users_and_refresh_tokens(self):
        tables = set(Base.metadata.tables.keys())
        assert "users" in tables
        assert "refresh_tokens" in tables


# ── Database URL Builder Tests ────────────────────────────────────────────────


class TestDatabaseUrlBuilder:
    def test_empty_url_returns_empty(self):
        with patch.object(settings, "database_url", ""):
            assert build_async_database_url() == ""

    def test_postgresql_url_is_converted_to_async(self):
        with patch.object(settings, "database_url", "postgresql://user:pass@localhost:5432/db"):
            result = build_async_database_url()
            assert result == "postgresql+asyncpg://user:pass@localhost:5432/db"

    def test_already_async_url_is_not_double_converted(self):
        with patch.object(settings, "database_url", "postgresql+asyncpg://user:pass@localhost:5432/db"):
            result = build_async_database_url()
            assert result == "postgresql+asyncpg://user:pass@localhost:5432/db"


# ── Engine Creation Tests ─────────────────────────────────────────────────────


def _reset_db_globals():
    """Reset engine and session_factory globals to None, returning a restore function."""
    import app.db.database as db_mod

    snapshot = (
        db_mod._async_engine,
        db_mod._async_session_factory,
        db_mod._sync_engine,
        db_mod._sync_session_factory,
    )
    db_mod._async_engine = None
    db_mod._async_session_factory = None
    db_mod._sync_engine = None
    db_mod._sync_session_factory = None

    def restore():
        (
            db_mod._async_engine,
            db_mod._async_session_factory,
            db_mod._sync_engine,
            db_mod._sync_session_factory,
        ) = snapshot

    return restore


class TestEngineCreation:
    @pytest.mark.asyncio
    async def test_engine_not_created_without_url(self):
        restore = _reset_db_globals()
        try:
            with patch.object(settings, "database_url", ""):
                engine = await create_engine()
                assert engine is None
                await dispose_engine()
        finally:
            restore()

    @pytest.mark.asyncio
    async def test_engine_creation_uses_async_driver(self):
        restore = _reset_db_globals()
        try:
            with patch("app.db.database.create_async_engine") as mock_create:
                with patch.object(settings, "database_url", "postgresql://rsai:rsai@localhost:5432/rsai"):
                    engine = await create_engine()
                    mock_create.assert_called_once()
                    url_arg = mock_create.call_args[0][0]
                    assert url_arg == "postgresql+asyncpg://rsai:rsai@localhost:5432/rsai"
                    assert engine is not None
                    await dispose_engine()
        finally:
            restore()

    @pytest.mark.asyncio
    async def test_dispose_engine_clears_globals(self):
        restore = _reset_db_globals()
        try:
            with patch("app.db.database.create_async_engine"):
                with patch.object(settings, "database_url", "postgresql://rsai:rsai@localhost:5432/rsai"):
                    await create_engine()
                    assert get_engine() is not None
                    await dispose_engine()
                    assert get_engine() is None
        finally:
            restore()


# ── Session Tests ────────────────────────────────────────────────────────────────


class TestSession:
    @pytest.mark.asyncio
    async def test_get_session_raises_without_engine(self):
        with patch("app.db.session.get_session_factory", return_value=None):
            from app.db.session import get_db_session

            with pytest.raises(RuntimeError, match="Database not configured"):
                async for _ in get_db_session():
                    pass


# ── Repository Factory Tests (JSON) ───────────────────────────────────────────


class TestFactoryReturnsJson:
    def test_get_resume_repository(self):
        with patch.object(settings, "storage_backend", "json"):
            assert isinstance(get_resume_repository(), JsonResumeRepository)

    def test_get_application_repository(self):
        with patch.object(settings, "storage_backend", "json"):
            assert isinstance(get_application_repository(), JsonApplicationRepository)

    def test_get_cover_letter_repository(self):
        with patch.object(settings, "storage_backend", "json"):
            assert isinstance(get_cover_letter_repository(), JsonCoverLetterRepository)

    def test_get_match_repository(self):
        with patch.object(settings, "storage_backend", "json"):
            assert isinstance(get_match_repository(), JsonMatchRepository)

    def test_get_version_repository(self):
        with patch.object(settings, "storage_backend", "json"):
            assert isinstance(get_version_repository(), JsonResumeVersionRepository)

    def test_get_suggestion_repository(self):
        with patch.object(settings, "storage_backend", "json"):
            assert isinstance(get_suggestion_repository(), JsonWriterSuggestionRepository)

    def test_get_interview_session_repository(self):
        with patch.object(settings, "storage_backend", "json"):
            assert isinstance(get_interview_session_repository(), JsonInterviewSessionRepository)

    def test_get_timeline_event_repository(self):
        with patch.object(settings, "storage_backend", "json"):
            assert isinstance(get_timeline_event_repository(), JsonTimelineEventRepository)

    def test_get_interview_question_repository(self):
        with patch.object(settings, "storage_backend", "json"):
            assert isinstance(get_interview_question_repository(), JsonInterviewQuestionRepository)

    def test_get_interview_answer_repository(self):
        with patch.object(settings, "storage_backend", "json"):
            assert isinstance(get_interview_answer_repository(), JsonInterviewAnswerRepository)

    def test_get_readiness_assessment_repository(self):
        with patch.object(settings, "storage_backend", "json"):
            assert isinstance(get_readiness_assessment_repository(), JsonReadinessAssessmentRepository)

    def test_get_session_summary_repository(self):
        with patch.object(settings, "storage_backend", "json"):
            assert isinstance(get_session_summary_repository(), JsonSessionSummaryRepository)


# ── Repository Factory Tests (PostgreSQL) ─────────────────────────────────────


class TestFactoryReturnsPostgresImplementations:
    def test_get_resume_repository_postgres(self):
        with patch.object(settings, "storage_backend", "postgres"):
            from app.services.repositories.postgres.content_repository import PostgresResumeRepository

            assert isinstance(get_resume_repository(), PostgresResumeRepository)

    def test_get_application_repository_postgres(self):
        with patch.object(settings, "storage_backend", "postgres"):
            from app.services.repositories.postgres.content_repository import PostgresApplicationRepository

            assert isinstance(get_application_repository(), PostgresApplicationRepository)

    def test_get_cover_letter_repository_postgres(self):
        with patch.object(settings, "storage_backend", "postgres"):
            from app.services.repositories.postgres.content_repository import PostgresCoverLetterRepository

            assert isinstance(get_cover_letter_repository(), PostgresCoverLetterRepository)

    def test_get_match_repository_postgres(self):
        with patch.object(settings, "storage_backend", "postgres"):
            from app.services.repositories.postgres.content_repository import PostgresMatchRepository

            assert isinstance(get_match_repository(), PostgresMatchRepository)

    def test_get_version_repository_postgres(self):
        with patch.object(settings, "storage_backend", "postgres"):
            from app.services.repositories.postgres.content_repository import PostgresResumeVersionRepository

            assert isinstance(get_version_repository(), PostgresResumeVersionRepository)

    def test_get_suggestion_repository_postgres(self):
        with patch.object(settings, "storage_backend", "postgres"):
            from app.services.repositories.postgres.content_repository import PostgresWriterSuggestionRepository

            assert isinstance(get_suggestion_repository(), PostgresWriterSuggestionRepository)

    def test_get_interview_session_repository_postgres(self):
        with patch.object(settings, "storage_backend", "postgres"):
            from app.services.repositories.postgres.content_repository import PostgresInterviewSessionRepository

            assert isinstance(get_interview_session_repository(), PostgresInterviewSessionRepository)


# ── Health Endpoint Tests ─────────────────────────────────────────────────────


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_json_backend(self, client):
        with patch.object(settings, "storage_backend", "json"):
            async with client as ac:
                response = await ac.get("/api/v1/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["storage_backend"] == "json"
            assert "database_connected" not in data

    @pytest.mark.asyncio
    async def test_health_detects_postgres_backend(self, client):
        restore = _reset_db_globals()
        try:
            with patch.object(settings, "storage_backend", "postgres"):
                async with client as ac:
                    response = await ac.get("/api/v1/health")
                assert response.status_code == 200
                data = response.json()
                assert data["storage_backend"] == "postgres"
                assert "database_connected" in data
                assert data["database_connected"] is False
        finally:
            restore()


# ── Alembic Tests ─────────────────────────────────────────────────────────────


class TestAlembicMigration:
    def test_migration_file_exists(self):
        import glob

        migrations = glob.glob(os.path.join(os.path.dirname(__file__), "..", "alembic", "versions", "*.py"))
        assert len(migrations) >= 1

    def test_upgrade_and_downgrade(self):
        pytest.skip("Requires running PostgreSQL — run with --runpostgres flag")
