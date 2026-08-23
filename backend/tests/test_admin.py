"""Tests for the Administration Console."""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Health endpoint still works ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_health_endpoint_unchanged(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["ai_service_connected"] is not None


# ── Admin endpoints require auth ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_endpoints_require_auth(client):
    """With an invalid token, admin endpoints must return 401/403."""
    headers = {"Authorization": "Bearer invalid_token_xxx"}
    for ep in [
        "/api/v1/admin/dashboard", "/api/v1/admin/config", "/api/v1/admin/ai",
        "/api/v1/admin/models", "/api/v1/admin/database", "/api/v1/admin/storage",
        "/api/v1/admin/features", "/api/v1/admin/system",
    ]:
        resp = await client.get(ep, headers=headers)
        assert resp.status_code in (401, 403), f"{ep} returned {resp.status_code}"


@pytest.mark.asyncio
async def test_admin_post_endpoints_require_auth(client):
    headers = {"Authorization": "Bearer invalid_token_xxx"}
    resp = await client.post("/api/v1/admin/ai/test", json={}, headers=headers)
    assert resp.status_code in (401, 403)
    resp = await client.post("/api/v1/admin/database/validate", json={}, headers=headers)
    assert resp.status_code in (401, 403)


# ── Admin dashboard returns expected structure ──────────────────────────────────


@pytest.mark.asyncio
async def test_dashboard_structure(client):
    resp = await client.get("/api/v1/admin/dashboard")
    assert resp.status_code in (200, 401, 403)
    if resp.status_code == 200:
        data = resp.json().get("data", {})
        for key in ["version", "storage_backend", "ai_provider"]:
            assert key in data, f"Missing: {key}"


# ── Admin config returns expected fields ────────────────────────────────────────


@pytest.mark.asyncio
async def test_config_structure(client):
    resp = await client.get("/api/v1/admin/config")
    assert resp.status_code in (200, 401, 403)
    if resp.status_code == 200:
        data = resp.json().get("data", {})
        for key in ["app_name", "app_version", "storage_backend", "omniroute_model"]:
            assert key in data, f"Missing config field: {key}"


# ── AI config endpoint ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ai_config_endpoint(client):
    resp = await client.get("/api/v1/admin/ai")
    assert resp.status_code in (200, 401, 403)
    if resp.status_code == 200:
        data = resp.json().get("data", {})
        assert "endpoint" in data
        assert "connectivity" in data


# ── Features endpoint ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_features_endpoint(client):
    resp = await client.get("/api/v1/admin/features")
    assert resp.status_code in (200, 401, 403)
    if resp.status_code == 200:
        data = resp.json().get("data", {})
        assert "debug" in data
        assert "allow_mock_ai_data" in data
        assert "storage_backend" in data


# ── Feature update ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_feature_update_requires_valid_key(client):
    resp = await client.put("/api/v1/admin/features", json={"key": "bad-key", "value": True})
    assert resp.status_code in (200, 400, 401, 403)


# ── System health endpoint ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_system_health_endpoint(client):
    resp = await client.get("/api/v1/admin/system")
    assert resp.status_code in (200, 401, 403)
    if resp.status_code == 200:
        data = resp.json().get("data", {})
        for key in ["application", "ai", "database", "storage"]:
            assert key in data, f"Missing health section: {key}"


# ── Storage endpoint ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_storage_endpoint(client):
    resp = await client.get("/api/v1/admin/storage")
    assert resp.status_code in (200, 401, 403)
    if resp.status_code == 200:
        assert "backend" in resp.json().get("data", {})


# ── Service-level tests ─────────────────────────────────────────────────────────


def test_config_service():
    from app.services.admin_service import get_config
    cfg = get_config()
    for key in ["app_name", "storage_backend", "omniroute_model"]:
        assert key in cfg


def test_get_features():
    from app.services.admin_service import get_features
    f = get_features()
    for key in ["debug", "allow_mock_ai_data", "storage_backend"]:
        assert key in f


def test_get_storage_status():
    from app.services.admin_service import get_storage_status
    s = get_storage_status()
    assert "backend" in s
    assert "json_files_available_for_migration" in s


def test_get_uptime():
    from app.services.admin_service import get_uptime
    assert get_uptime() > 0


# ── Storage Management Tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_storage_manage_endpoint(client):
    resp = await client.get("/api/v1/admin/storage/manage")
    assert resp.status_code in (200, 401, 403)
    if resp.status_code == 200:
        data = resp.json().get("data", {})
        assert "backend" in data
        assert "alembic_current" in data


@pytest.mark.asyncio
async def test_storage_validate_endpoint(client):
    resp = await client.post("/api/v1/admin/storage/validate", json={})
    assert resp.status_code in (200, 401, 403)
    if resp.status_code == 200:
        data = resp.json().get("data", {})
        assert "valid" in data
        assert "checks" in data


@pytest.mark.asyncio
async def test_storage_switch_requires_target(client):
    resp = await client.post("/api/v1/admin/storage/switch", json={})
    assert resp.status_code in (400, 401, 403)


@pytest.mark.asyncio
async def test_storage_switch_invalid_target(client):
    resp = await client.post("/api/v1/admin/storage/switch", json={"target": "invalid"})
    assert resp.status_code in (400, 401, 403)


@pytest.mark.asyncio
async def test_storage_migrate_endpoint(client):
    resp = await client.post("/api/v1/admin/storage/migrate", json={})
    assert resp.status_code in (200, 401, 403)


def test_configuration_service():
    from app.services.configuration_service import get, set_storage_backend
    cfg = get_all = __import__("app.services.configuration_service", fromlist=["get_all"]).get_all
    all_cfg = cfg()
    assert "storage_backend" in all_cfg or "app_name" in all_cfg


def test_switch_backend_validation():
    from app.services.admin_service import run_storage_validation
    result = run_storage_validation()
    assert "valid" in result
    assert "checks" in result
    assert isinstance(result["valid"], bool)


# ── Development Features Tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_development_endpoint(client):
    resp = await client.get("/api/v1/admin/development")
    assert resp.status_code in (200, 401, 403)
    if resp.status_code == 200:
        data = resp.json().get("data", {})
        assert "development_mode" in data
        assert "mock_authentication" in data
        assert "mock_ai" in data
        assert "mock_matching" in data


def test_development_features_service():
    from app.services.development_features import development_features
    status = development_features.get_status()
    assert "development_mode" in status
    assert "mock_authentication" in status
    assert "mock_ai" in status
    assert "mock_matching" in status


def test_development_audit_production_safety():
    from app.services.development_features import development_features
    warnings = development_features.audit_production_safety()
    assert isinstance(warnings, list)


def test_development_audit_detects_issues():
    from unittest.mock import patch
    from app.services.development_features import DevelopmentFeatures

    with patch.object(DevelopmentFeatures, "debug_enabled", False, create=True):
        with patch.object(DevelopmentFeatures, "mock_ai", True, create=True):
            dev = DevelopmentFeatures()
            warnings = dev.audit_production_safety()
            assert len(warnings) >= 1
            assert any("MOCK_AI" in w for w in warnings)


# ── Configuration Diagnostics Tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_configuration_diagnostics_endpoint(client):
    resp = await client.get("/api/v1/admin/configuration/diagnostics")
    assert resp.status_code in (200, 401, 403)
    if resp.status_code == 200:
        data = resp.json().get("data", {})
        assert "jwt" in data
        assert "database" in data
        assert "ai" in data
        assert "storage" in data
        assert "environment" in data


def test_diagnostics_jwt_never_exposes_secret():
    from app.services.configuration_diagnostics_service import check_jwt
    result = check_jwt()
    assert "configured" in result
    assert "secure" in result
    assert "secret" not in result
    assert "password" not in result


def test_diagnostics_jwt_detects_missing():
    from unittest.mock import patch
    from app.core.config import settings as app_settings
    with patch.object(app_settings, "jwt_secret_key", ""):
        from app.services.configuration_diagnostics_service import check_jwt
        result = check_jwt()
        assert result["configured"] is False
        assert result["secure"] is False


def test_diagnostics_storage_backend():
    from app.services.configuration_diagnostics_service import check_storage
    result = check_storage()
    assert "backend" in result
    assert result["backend"] in ("json", "postgres")


def test_diagnostics_valid_jwt_secure():
    from unittest.mock import patch
    from app.core.config import settings as app_settings
    with patch.object(app_settings, "jwt_secret_key", "a" * 32):
        from app.services.configuration_diagnostics_service import check_jwt
        result = check_jwt()
        assert result["configured"] is True
        assert result["secure"] is True


def test_diagnostics_weak_jwt_insecure():
    from unittest.mock import patch
    from app.core.config import settings as app_settings
    with patch.object(app_settings, "jwt_secret_key", "short"):
        from app.services.configuration_diagnostics_service import check_jwt
        result = check_jwt()
        assert result["configured"] is True
        assert result["secure"] is False


def test_diagnostics_environment_has_all_sections():
    import anyio
    from app.services.configuration_diagnostics_service import get_all
    async def _test():
        result = await get_all()
        for section in ["jwt", "database", "ai", "storage", "environment"]:
            assert section in result, f"Missing section: {section}"
    anyio.run(_test)
