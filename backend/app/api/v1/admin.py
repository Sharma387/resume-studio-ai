"""Administration Console — operational monitoring and configuration."""

from fastapi import APIRouter, Depends, HTTPException

from app.models.user import User
from app.services import admin_service as svc
from app.services.auth_deps import require_admin

router = APIRouter()


def _admin_only(current_user: User = Depends(require_admin)) -> User:
    return current_user


# ── Dashboard ────────────────────────────────────────────────────────────────


@router.get("/admin/dashboard")
async def dashboard(_: User = Depends(_admin_only)):
    data = await svc.get_dashboard()
    return {"success": True, "data": data}


# ── Configuration ────────────────────────────────────────────────────────────


@router.get("/admin/config")
async def get_config(_: User = Depends(_admin_only)):
    return {"success": True, "data": svc.get_config()}


# ── AI ───────────────────────────────────────────────────────────────────────


@router.get("/admin/ai")
async def get_ai_config(_: User = Depends(_admin_only)):
    cfg = svc.get_config()
    connectivity = await svc.check_ai_connectivity()
    return {
        "success": True,
        "data": {
            "endpoint": cfg["omniroute_api_url"],
            "model": cfg["omniroute_model"],
            "timeout": cfg["omniroute_timeout"],
            "max_retries": cfg["omniroute_max_retries"],
            "mock_allowed": cfg["allow_mock_ai_data"],
            "key_configured": cfg["omniroute_api_key_configured"],
            "connectivity": connectivity,
        },
    }


@router.put("/admin/ai")
async def update_ai_config(body: dict, _: User = Depends(_admin_only)):
    from app.services.configuration_service import set_ai_config

    result = set_ai_config(body)
    return {"success": True, "data": result}


@router.post("/admin/ai/test")
async def test_ai_connection(_: User = Depends(_admin_only)):
    result = await svc.test_ai_connection()
    return {"success": True, "data": result}


@router.post("/admin/ai/test-parse")
async def test_ai_parse(_: User = Depends(_admin_only)):
    result = await svc.test_ai_parse_snippet()
    return {"success": True, "data": result}


@router.get("/admin/models")
async def list_models(_: User = Depends(_admin_only)):
    models = await svc.discover_models()
    return {"success": True, "data": models}


# ── Parse Test ───────────────────────────────────────────────────────────────


class ParseTestRequest:
    def __init__(self, text: str):
        self.text = text


from pydantic import BaseModel, Field


class ParseTestRequestModel(BaseModel):
    text: str = Field(..., min_length=1, description="Resume text to parse")


@router.post("/admin/ai/parse-test")
async def test_parse(body: ParseTestRequestModel, _: User = Depends(_admin_only)):
    result = await svc.test_parse_resume(body.text)
    return {"success": True, "data": result}


# ── Database ─────────────────────────────────────────────────────────────────


@router.get("/admin/database")
async def get_database_status(_: User = Depends(_admin_only)):
    return {"success": True, "data": svc.get_database_status()}


@router.post("/admin/database/validate")
async def validate_database(_: User = Depends(_admin_only)):
    return {"success": True, "data": svc.validate_database()}


# ── Storage ──────────────────────────────────────────────────────────────────


@router.get("/admin/storage")
async def get_storage_status(_: User = Depends(_admin_only)):
    return {"success": True, "data": svc.get_storage_status()}


# ── Feature Flags ────────────────────────────────────────────────────────────


@router.get("/admin/features")
async def get_features(_: User = Depends(_admin_only)):
    return {"success": True, "data": svc.get_features()}


@router.put("/admin/features")
async def update_feature(body: dict, _: User = Depends(_admin_only)):
    key = body.get("key", "")
    value = body.get("value")
    if not key or value is None:
        raise HTTPException(status_code=400, detail="key and value are required")
    try:
        result = svc.set_feature(key, value)
        return {"success": True, "data": result}
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── System Health ────────────────────────────────────────────────────────────


@router.get("/admin/system")
async def get_system_health(_: User = Depends(_admin_only)):
    dashboard_data = await svc.get_dashboard()
    ai_status = await svc.check_ai_connectivity()

    sections = {
        "application": {
            "status": "healthy",
            "version": dashboard_data["version"],
            "environment": dashboard_data["environment"],
            "uptime_seconds": dashboard_data["uptime_seconds"],
        },
        "ai": {
            "status": "healthy" if ai_status.get("reachable") else "critical",
            "provider": ai_status.get("provider"),
            "model": ai_status.get("configured_model"),
            "reachable": ai_status.get("reachable"),
        },
        "database": {
            "status": "healthy" if dashboard_data.get("database_connected") else "warning",
            "backend": dashboard_data.get("storage_backend"),
            "migration": dashboard_data.get("migration"),
        },
        "storage": {
            "status": "healthy",
            "backend": dashboard_data.get("storage_backend"),
        },
    }

    return {"success": True, "data": sections}


# ── Storage Management ─────────────────────────────────────────────────────────


@router.get("/admin/storage/manage")
async def get_storage_manage(_: User = Depends(_admin_only)):
    return {"success": True, "data": svc.get_storage_management_status()}


@router.post("/admin/storage/validate")
async def validate_storage(_: User = Depends(_admin_only)):
    return {"success": True, "data": svc.run_storage_validation()}


@router.post("/admin/storage/switch")
async def switch_storage(body: dict, _: User = Depends(_admin_only)):
    target = body.get("target", "")
    if not target:
        raise HTTPException(status_code=400, detail="target is required (json or postgres)")
    try:
        result = await svc.switch_storage_backend(target)
        return {"success": True, "data": result}
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/admin/storage/migrate")
async def migrate_storage(_: User = Depends(_admin_only)):
    result = await svc.run_migration()
    return {"success": result["success"], "data": result}


# ── Development ────────────────────────────────────────────────────────────────


@router.get("/admin/development")
async def get_development_status(_: User = Depends(_admin_only)):
    return {"success": True, "data": svc.get_development_status()}


# ── Configuration Diagnostics ──────────────────────────────────────────────────


@router.get("/admin/configuration/diagnostics")
async def get_configuration_diagnostics(_: User = Depends(_admin_only)):
    from app.services.configuration_diagnostics_service import get_all as get_diagnostics
    data = await get_diagnostics()
    return {"success": True, "data": data}


# ── User Management ────────────────────────────────────────────────────────────

from app.services import admin_user_service as usvc
from app.services.audit_service import query as query_audit


def _paginated(page: int = 1, page_size: int = 20) -> tuple[int, int]:
    return max(1, page), min(max(1, page_size), 100)


@router.get("/admin/users")
async def list_users(
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    role: str | None = None,
    status: str | None = None,
    _: User = Depends(_admin_only),
):
    page, page_size = _paginated(page, page_size)
    result = usvc.list_users(page=page, page_size=page_size, search=search, role=role, status=status)
    return {"success": True, "data": result}


@router.get("/admin/users/stats")
async def user_stats(_: User = Depends(_admin_only)):
    return {"success": True, "data": usvc.get_dashboard_stats()}


@router.get("/admin/users/{user_id}")
async def get_user(user_id: str, _: User = Depends(_admin_only)):
    result = usvc.get_user_detail(user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True, "data": result}


@router.put("/admin/users/{user_id}")
async def update_user(user_id: str, body: dict, current_user: User = Depends(_admin_only)):
    full_name = body.get("full_name")
    if not full_name:
        raise HTTPException(status_code=400, detail="full_name is required")
    result = usvc.update_user(user_id, admin_id=current_user.id, full_name=full_name)
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True, "data": result}


@router.post("/admin/users/{user_id}/disable")
async def disable_user(user_id: str, current_user: User = Depends(_admin_only)):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot disable yourself")
    result = usvc.disable_user(user_id, admin_id=current_user.id)
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True, "data": result}


@router.post("/admin/users/{user_id}/enable")
async def enable_user(user_id: str, current_user: User = Depends(_admin_only)):
    result = usvc.enable_user(user_id, admin_id=current_user.id)
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True, "data": result}


@router.post("/admin/users/{user_id}/promote")
async def promote_user(user_id: str, current_user: User = Depends(_admin_only)):
    result = usvc.promote_user(user_id, admin_id=current_user.id)
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True, "data": result}


@router.post("/admin/users/{user_id}/demote")
async def demote_user(user_id: str, current_user: User = Depends(_admin_only)):
    try:
        result = usvc.demote_user(user_id, requester_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True, "data": result}


@router.post("/admin/users/{user_id}/reset-password")
async def reset_user_password(user_id: str, body: dict, current_user: User = Depends(_admin_only)):
    custom_password = body.get("custom_password") if body else None
    try:
        result = usvc.reset_password(user_id, admin_id=current_user.id, custom_password=custom_password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"success": True, "data": result}


# ── Audit Log ──────────────────────────────────────────────────────────────────


@router.get("/admin/audit")
async def get_audit_log(
    page: int = 1,
    page_size: int = 50,
    action: str | None = None,
    _: User = Depends(_admin_only),
):
    page, page_size = _paginated(page, page_size)
    result = query_audit(page=page, page_size=page_size, action=action)
    return {"success": True, "data": result}
