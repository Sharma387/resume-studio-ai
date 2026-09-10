"""Tests for PostgreSQL UserRepository and RefreshTokenRepository (Phase 2A).

Tests cover:
- ORM model creation and conversion
- UserRepository CRUD operations
- RefreshTokenRepository CRUD operations
- Duplicate email detection
- Case-insensitive email lookup
- Token lifecycle
- Transaction rollback
- Behavior parity with JSON repositories
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from app.core.config import settings
from app.db.database import get_sync_session
from app.db.models.user import RefreshTokenModel, UserModel
from app.models.user import User
from app.services.repositories.factory import get_refresh_token_repository, get_user_repository
from app.services.repositories.interfaces import UserRepository
from app.services.repositories.postgres.token_repository import PostgresRefreshTokenRepository
from app.services.repositories.postgres.user_repository import PostgresUserRepository

# ── Fixtures for PostgreSQL-dependent tests ──────────────────────────────────


def _requires_db():
    if not settings.database_url:
        pytest.skip("No DATABASE_URL configured — requires PostgreSQL")


def _reset_db():
    """Clean all rows from both tables."""
    _requires_db()
    session = get_sync_session()
    try:
        session.query(RefreshTokenModel).delete()
        session.query(UserModel).delete()
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@pytest.fixture
def pg_session():
    """Provide a clean sync session for ORM-level tests."""
    _requires_db()
    _reset_db()
    session = get_sync_session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def pg_user_repo():
    """Provide a PostgresUserRepository with clean state."""
    _requires_db()
    _reset_db()
    return PostgresUserRepository()


@pytest.fixture
def pg_token_repo():
    """Provide a PostgresRefreshTokenRepository with clean state."""
    _requires_db()
    _reset_db()
    return PostgresRefreshTokenRepository()


def _make_user(overrides: dict | None = None) -> User:
    fields = {
        "id": uuid.uuid4().hex,
        "email": "test@example.com",
        "password_hash": "$2b$12$abcdefghijklmnopqrstuv",  # fake bcrypt hash
        "full_name": "Test User",
    }
    if overrides:
        fields.update(overrides)
    return User(**fields)


# ══════════════════════════════════════════════════════════════════════════════
# ORM Model Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestUserModel:
    def test_table_name(self):
        assert UserModel.__tablename__ == "users"

    def test_columns_exist(self):
        columns = {c.name for c in UserModel.__table__.columns}
        assert "id" in columns
        assert "email" in columns
        assert "must_change_password" in columns
        assert "disabled" in columns
        assert "last_login_at" in columns
        assert "last_password_change" in columns

    def test_to_pydantic_roundtrip(self):
        user = _make_user()
        model = UserModel.from_pydantic(user)
        restored = model.to_pydantic()
        assert restored.id == user.id
        assert restored.email == user.email
        assert restored.full_name == user.full_name
        assert restored.role.value == "user"
        assert restored.subscription.value == "free"
        assert restored.status.value == "active"

    @pytest.mark.asyncio
    async def test_from_pydantic_preserves_enums(self):
        user = _make_user({"role": "admin", "subscription": "pro", "status": "pending"})
        model = UserModel.from_pydantic(user)
        assert model.role == "admin"
        assert model.subscription == "pro"
        assert model.status == "pending"

    def test_to_pydantic_password_hash(self):
        user = _make_user()
        model = UserModel.from_pydantic(user)
        restored = model.to_pydantic()
        assert restored.password_hash == user.password_hash


class TestRefreshTokenModel:
    def test_table_name(self):
        assert RefreshTokenModel.__tablename__ == "refresh_tokens"

    def test_columns_exist(self):
        columns = {c.name for c in RefreshTokenModel.__table__.columns}
        expected = {"token_hash", "user_id", "expires_at", "created_at"}
        assert columns == expected

    def test_primary_key(self):
        pk = RefreshTokenModel.__table__.primary_key
        assert [c.name for c in pk.columns] == ["token_hash"]


# ══════════════════════════════════════════════════════════════════════════════
# UserRepository Unit Tests (with patched storage_backend)
# ══════════════════════════════════════════════════════════════════════════════


class TestUserRepositoryFactory:
    def test_factory_returns_json_when_json(self):
        with patch.object(settings, "storage_backend", "json"):
            repo = get_user_repository()
            assert isinstance(repo, UserRepository)

    def test_factory_returns_postgres_when_postgres(self):
        with patch.object(settings, "storage_backend", "postgres"):
            repo = get_user_repository()
            assert isinstance(repo, PostgresUserRepository)

    def test_postgres_raises_without_database(self):
        import app.db.database as db_mod

        old_factory = db_mod._sync_session_factory
        try:
            db_mod._sync_session_factory = None
            with patch.object(settings, "storage_backend", "postgres"):
                with patch.object(settings, "database_url", ""):
                    with pytest.raises(RuntimeError, match="Database not configured"):
                        get_user_repository().get_by_id("x")
        finally:
            db_mod._sync_session_factory = old_factory


# ══════════════════════════════════════════════════════════════════════════════
# UserRepository Integration Tests (require PostgreSQL)
# ══════════════════════════════════════════════════════════════════════════════


class TestPostgresUserRepository:
    def test_save_and_get_by_id(self, pg_user_repo):
        user = _make_user()
        pg_user_repo.save(user)
        loaded = pg_user_repo.get_by_id(user.id)
        assert loaded is not None
        assert loaded.id == user.id
        assert loaded.email == user.email
        assert loaded.full_name == user.full_name

    def test_get_by_id_not_found(self, pg_user_repo):
        result = pg_user_repo.get_by_id("nonexistent")
        assert result is None

    def test_get_by_email(self, pg_user_repo):

        user = _make_user({"email": "findme@example.com"})
        pg_user_repo.save(user)
        loaded = pg_user_repo.get_by_email("findme@example.com")
        assert loaded is not None
        assert loaded.id == user.id

    def test_get_by_email_case_insensitive(self, pg_user_repo):

        user = _make_user({"email": "CaseSensitive@Test.Com"})
        pg_user_repo.save(user)
        loaded = pg_user_repo.get_by_email("casesensitive@test.com")
        assert loaded is not None
        assert loaded.id == user.id

    def test_get_by_email_not_found(self, pg_user_repo):

        result = pg_user_repo.get_by_email("nobody@example.com")
        assert result is None

    def test_list_all(self, pg_user_repo):

        u1 = _make_user({"email": "user1@test.com", "id": uuid.uuid4().hex})
        u2 = _make_user({"email": "user2@test.com", "id": uuid.uuid4().hex})
        pg_user_repo.save(u1)
        pg_user_repo.save(u2)
        all_users = pg_user_repo.list_all()
        assert len(all_users) >= 2
        emails = {u.email for u in all_users}
        assert "user1@test.com" in emails
        assert "user2@test.com" in emails

    def test_update_user(self, pg_user_repo):

        user = _make_user({"full_name": "Original Name"})
        pg_user_repo.save(user)
        user.full_name = "Updated Name"
        pg_user_repo.save(user)
        loaded = pg_user_repo.get_by_id(user.id)
        assert loaded is not None
        assert loaded.full_name == "Updated Name"

    def test_update_last_login(self, pg_user_repo):

        user = _make_user()
        pg_user_repo.save(user)
        user.last_login = datetime.now(UTC).isoformat()
        pg_user_repo.save(user)
        loaded = pg_user_repo.get_by_id(user.id)
        assert loaded is not None
        assert loaded.last_login is not None

    def test_delete_user(self, pg_user_repo):

        user = _make_user()
        pg_user_repo.save(user)
        assert pg_user_repo.delete(user.id) is True
        assert pg_user_repo.get_by_id(user.id) is None

    def test_delete_not_found(self, pg_user_repo):

        assert pg_user_repo.delete("nonexistent") is False

    def test_duplicate_email(self, pg_user_repo):

        user1 = _make_user({"email": "dupe@test.com"})
        pg_user_repo.save(user1)
        user2 = _make_user({"email": "dupe@test.com", "id": uuid.uuid4().hex})
        with pytest.raises(Exception):
            pg_user_repo.save(user2)

    def test_email_unique_index(self, pg_session):

        uid1 = uuid.uuid4().hex
        uid2 = uuid.uuid4().hex
        now = datetime.now(UTC).isoformat()
        pg_session.add(
            UserModel(id=uid1, email="unique@test.com", password_hash="hash1", full_name="A", created_at=now)
        )
        pg_session.add(
            UserModel(id=uid2, email="unique@test.com", password_hash="hash2", full_name="B", created_at=now)
        )
        with pytest.raises(Exception):
            pg_session.commit()
        pg_session.rollback()


# ══════════════════════════════════════════════════════════════════════════════
# RefreshTokenRepository Integration Tests (require PostgreSQL)
# ══════════════════════════════════════════════════════════════════════════════


class TestPostgresRefreshTokenRepository:
    def test_save_and_get_user_id(self, pg_user_repo, pg_token_repo):

        user = _make_user()
        pg_user_repo.save(user)
        token_hash = "abc123def456"
        pg_token_repo.save(token_hash, user.id, "2026-12-31T23:59:59")
        stored_user_id = pg_token_repo.get_user_id(token_hash)
        assert stored_user_id == user.id

    def test_get_user_id_not_found(self, pg_token_repo):

        result = pg_token_repo.get_user_id("nonexistent")
        assert result is None

    def test_delete_token(self, pg_user_repo, pg_token_repo):

        user = _make_user()
        pg_user_repo.save(user)
        token_hash = "deleteme"
        pg_token_repo.save(token_hash, user.id, "2026-12-31T23:59:59")
        assert pg_token_repo.delete(token_hash) is True
        assert pg_token_repo.get_user_id(token_hash) is None

    def test_delete_not_found(self, pg_token_repo):

        assert pg_token_repo.delete("nonexistent") is False

    def test_delete_all_for_user(self, pg_user_repo, pg_token_repo):

        user = _make_user()
        pg_user_repo.save(user)
        pg_token_repo.save("token1", user.id, "2026-12-31T23:59:59")
        pg_token_repo.save("token2", user.id, "2026-12-31T23:59:59")
        pg_token_repo.save("token3", user.id, "2027-01-01T00:00:00")
        pg_token_repo.delete_all_for_user(user.id)
        assert pg_token_repo.get_user_id("token1") is None
        assert pg_token_repo.get_user_id("token2") is None
        assert pg_token_repo.get_user_id("token3") is None

    def test_delete_all_for_user_other_user_unaffected(self, pg_user_repo, pg_token_repo):

        user_a = _make_user({"email": "a@test.com", "id": uuid.uuid4().hex})
        user_b = _make_user({"email": "b@test.com", "id": uuid.uuid4().hex})
        pg_user_repo.save(user_a)
        pg_user_repo.save(user_b)
        pg_token_repo.save("token_a", user_a.id, "2026-12-31T23:59:59")
        pg_token_repo.save("token_b", user_b.id, "2026-12-31T23:59:59")
        pg_token_repo.delete_all_for_user(user_a.id)
        assert pg_token_repo.get_user_id("token_a") is None
        assert pg_token_repo.get_user_id("token_b") == user_b.id

    def test_token_lifecycle(self, pg_user_repo, pg_token_repo):

        user = _make_user()
        pg_user_repo.save(user)
        token_hash = "lifecycle_token"
        pg_token_repo.save(token_hash, user.id, "2026-12-31T23:59:59")
        assert pg_token_repo.get_user_id(token_hash) == user.id
        pg_token_repo.delete(token_hash)
        assert pg_token_repo.get_user_id(token_hash) is None

    def test_fk_cascade_deletes_tokens(self, pg_user_repo, pg_token_repo):

        user = _make_user()
        pg_user_repo.save(user)
        pg_token_repo.save("cascade1", user.id, "2026-12-31T23:59:59")
        pg_token_repo.save("cascade2", user.id, "2027-01-01T00:00:00")
        pg_user_repo.delete(user.id)
        assert pg_token_repo.get_user_id("cascade1") is None
        assert pg_token_repo.get_user_id("cascade2") is None


# ══════════════════════════════════════════════════════════════════════════════
# Factory Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestFactory:
    def test_get_user_repository_json(self):
        with patch.object(settings, "storage_backend", "json"):
            from app.services.repositories.json_user_repo import JsonUserRepository

            assert isinstance(get_user_repository(), JsonUserRepository)

    def test_get_refresh_token_repository_json(self):
        with patch.object(settings, "storage_backend", "json"):
            from app.services.repositories.json_token_repo import JsonRefreshTokenRepository

            assert isinstance(get_refresh_token_repository(), JsonRefreshTokenRepository)

    def test_get_user_repository_postgres(self):
        with patch.object(settings, "storage_backend", "postgres"):
            assert isinstance(get_user_repository(), PostgresUserRepository)

    def test_get_refresh_token_repository_postgres(self):
        with patch.object(settings, "storage_backend", "postgres"):
            assert isinstance(get_refresh_token_repository(), PostgresRefreshTokenRepository)
