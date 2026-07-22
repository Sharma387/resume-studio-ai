import pytest
from httpx import AsyncClient, ASGITransport
from pydantic import ValidationError

from app.main import app
from app.models.user import User, UserRole, SubscriptionTier, AccountStatus, TokenPair, LoginRequest, RegisterRequest
from app.services.user_service import UserService
from app.services.auth_service import AuthenticationService
from app.services.repositories.json_user_repo import JsonUserRepository
from app.services.repositories.json_token_repo import JsonRefreshTokenRepository
from app.core.config import settings


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# Override JWT secret for tests
settings.jwt_secret_key = "test-secret-key-not-for-production"


class TestUserModel:
    def test_valid_user(self):
        u = User(id="u1", email="test@example.com", password_hash="hash", full_name="Test")
        assert u.role == UserRole.USER
        assert u.subscription == SubscriptionTier.FREE
        assert u.status == AccountStatus.ACTIVE
        assert u.email_verified is False

    def test_invalid_role(self):
        with pytest.raises(ValidationError):
            User(id="u2", email="t@t.com", password_hash="h", full_name="T", role="superadmin")

    def test_invalid_subscription(self):
        with pytest.raises(ValidationError):
            User(id="u3", email="t@t.com", password_hash="h", full_name="T", subscription="lifetime")

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            User(id="u4", email="t@t.com", password_hash="h", full_name="T", status="unknown")


class TestUserService:
    def test_create_and_authenticate(self):
        svc = UserService()
        svc.create_user(email="auth@test.com", password="ValidPass123", full_name="Auth User")
        user = svc.authenticate("auth@test.com", "ValidPass123")
        assert user is not None
        assert user.full_name == "Auth User"

    def test_authenticate_wrong_password(self):
        svc = UserService()
        svc.create_user(email="wrong@test.com", password="CorrectPwd1", full_name="W")
        user = svc.authenticate("wrong@test.com", "wrongpassword")
        assert user is None

    def test_authenticate_nonexistent(self):
        svc = UserService()
        assert svc.authenticate("noone@test.com", "pwd") is None

    def test_duplicate_email(self):
        svc = UserService()
        svc.create_user(email="dup@test.com", password="Pass12345", full_name="A")
        import pytest
        with pytest.raises(ValueError, match="already registered"):
            svc.create_user(email="dup@test.com", password="Pass12345", full_name="B")

    def test_change_password(self):
        svc = UserService()
        user = svc.create_user(email="changepwd@test.com", password="OldPass123", full_name="C")
        ok = svc.change_password(user.id, "OldPass123", "NewPass456")
        assert ok is True
        user2 = svc.authenticate("changepwd@test.com", "NewPass456")
        assert user2 is not None


class TestTokenPair:
    def test_create_token_pair(self):
        svc = UserService()
        user = svc.create_user(email="tokens@test.com", password="TokenPass1", full_name="Token User")
        auth = AuthenticationService()
        pair = auth.create_token_pair(user)
        assert pair.access_token is not None
        assert pair.refresh_token is not None
        assert pair.token_type == "bearer"

    def test_validate_access_token(self):
        svc = UserService()
        user = svc.create_user(email="validate@test.com", password="ValPass12", full_name="V")
        auth = AuthenticationService()
        pair = auth.create_token_pair(user)
        payload = auth.validate_access_token(pair.access_token)
        assert payload is not None
        assert payload["sub"] == user.id
        assert payload["type"] == "access"

    def test_refresh_token_rotation(self):
        svc = UserService()
        user = svc.create_user(email="rotate@test.com", password="Rotate123", full_name="R")
        auth = AuthenticationService()
        pair1 = auth.create_token_pair(user)
        pair2 = auth.refresh_token_pair(pair1.refresh_token)
        assert pair2 is not None
        # Old refresh token should be invalidated
        assert auth.refresh_token_pair(pair1.refresh_token) is None


class TestAuthEndpoints:
    @pytest.mark.asyncio
    async def test_register(self, client):
        async with client as ac:
            resp = await ac.post("/api/v1/auth/register", json={"email": "new@test.com", "password": "StrongPwd1", "full_name": "New User"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["user"]["email"] == "new@test.com"
        assert "access_token" in data["data"]["tokens"]

    @pytest.mark.asyncio
    async def test_register_duplicate(self, client):
        transport = ASGITransport(app=app)
        async with client as ac:
            resp = await ac.post("/api/v1/auth/register", json={"email": "dup2@test.com", "password": "StrongPwd1", "full_name": "Dup"})
        assert resp.status_code == 200
        t2 = ASGITransport(app=app)
        async with AsyncClient(transport=t2, base_url="http://test") as ac2:
            resp2 = await ac2.post("/api/v1/auth/register", json={"email": "dup2@test.com", "password": "StrongPwd1", "full_name": "Dup2"})
        assert resp2.status_code == 409

    @pytest.mark.asyncio
    async def test_login_success(self, client):
        t1 = ASGITransport(app=app)
        async with AsyncClient(transport=t1, base_url="http://test") as c:
            await c.post("/api/v1/auth/register", json={"email": "login@test.com", "password": "LoginPwd1", "full_name": "Login"})
        t2 = ASGITransport(app=app)
        async with AsyncClient(transport=t2, base_url="http://test") as c:
            resp = await c.post("/api/v1/auth/login", json={"email": "login@test.com", "password": "LoginPwd1"})
        assert resp.status_code == 200
        assert "access_token" in resp.json()["data"]["tokens"]

    @pytest.mark.asyncio
    async def test_login_invalid(self, client):
        t = ASGITransport(app=app)
        async with AsyncClient(transport=t, base_url="http://test") as c:
            resp = await c.post("/api/v1/auth/login", json={"email": "noone@test.com", "password": "bad"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_me_requires_auth(self, client):
        t = ASGITransport(app=app)
        async with AsyncClient(transport=t, base_url="http://test") as c:
            resp = await c.get("/api/v1/auth/me")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_me_with_token(self, client):
        t1 = ASGITransport(app=app)
        async with AsyncClient(transport=t1, base_url="http://test") as c:
            reg = await c.post("/api/v1/auth/register", json={"email": "me@test.com", "password": "MePass12", "full_name": "Me"})
        token = reg.json()["data"]["tokens"]["access_token"]
        t2 = ASGITransport(app=app)
        async with AsyncClient(transport=t2, base_url="http://test") as c:
            resp = await c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["data"]["email"] == "me@test.com"

    @pytest.mark.asyncio
    async def test_refresh(self, client):
        t1 = ASGITransport(app=app)
        async with AsyncClient(transport=t1, base_url="http://test") as c:
            reg = await c.post("/api/v1/auth/register", json={"email": "refresh@test.com", "password": "RefPass1", "full_name": "Ref"})
        refresh = reg.json()["data"]["tokens"]["refresh_token"]
        t2 = ASGITransport(app=app)
        async with AsyncClient(transport=t2, base_url="http://test") as c:
            resp = await c.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
        assert resp.status_code == 200
        assert "access_token" in resp.json()["data"]

    @pytest.mark.asyncio
    async def test_logout(self, client):
        t1 = ASGITransport(app=app)
        async with AsyncClient(transport=t1, base_url="http://test") as c:
            reg = await c.post("/api/v1/auth/register", json={"email": "logout@test.com", "password": "LogOut123", "full_name": "Log"})
        refresh = reg.json()["data"]["tokens"]["refresh_token"]
        access = reg.json()["data"]["tokens"]["access_token"]
        t2 = ASGITransport(app=app)
        async with AsyncClient(transport=t2, base_url="http://test") as c:
            resp = await c.post("/api/v1/auth/logout", json={"refresh_token": refresh},
                                headers={"Authorization": f"Bearer {access}"})
        assert resp.status_code == 200
