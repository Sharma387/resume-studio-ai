"""Admin user management — list, search, promote, demote, disable, enable, reset password."""

from app.models.user import User
from app.services.audit_service import log as audit_log
from app.services.user_service import UserService


def list_users(
    page: int = 1, page_size: int = 20, search: str | None = None, role: str | None = None, status: str | None = None
) -> dict:
    svc = UserService()
    users = svc.list_all()

    if search:
        s = search.lower()
        users = [u for u in users if s in u.email.lower() or s in u.full_name.lower()]
    if role:
        users = [u for u in users if u.role.value == role]
    if status:
        users = [u for u in users if u.status.value == status]

    total = len(users)
    start = (page - 1) * page_size
    page_users = users[start : start + page_size]

    return {
        "users": [format_user(u) for u in page_users],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_user_detail(user_id: str) -> dict | None:
    svc = UserService()
    user = svc.get_by_id(user_id)
    if user is None:
        return None
    return format_user(user)


def update_user(user_id: str, admin_id: str, full_name: str | None = None) -> dict | None:
    svc = UserService()
    user = svc.get_by_id(user_id)
    if user is None:
        return None
    if full_name is not None:
        old_name = user.full_name
        user.full_name = full_name
        svc.repo.save(user)
        audit_log("update_user", admin_id, target_user=user_id, details=f"Name changed: {old_name} → {full_name}")
    return format_user(user)


def disable_user(user_id: str, admin_id: str) -> dict | None:
    svc = UserService()
    user = svc.disable_user(user_id)
    if user:
        audit_log("disable_user", admin_id, target_user=user_id)
    return format_user(user) if user else None


def enable_user(user_id: str, admin_id: str) -> dict | None:
    svc = UserService()
    user = svc.enable_user(user_id)
    if user:
        audit_log("enable_user", admin_id, target_user=user_id)
    return format_user(user) if user else None


def promote_user(user_id: str, admin_id: str) -> dict | None:
    svc = UserService()
    user = svc.promote_to_admin(user_id)
    if user:
        audit_log("promote_user", admin_id, target_user=user_id)
    return format_user(user) if user else None


def demote_user(user_id: str, requester_id: str) -> dict | None:
    svc = UserService()
    user = svc.demote_to_user(user_id, requester_id)
    if user:
        audit_log("demote_user", requester_id, target_user=user_id)
    return format_user(user) if user else None


def reset_password(user_id: str, admin_id: str, custom_password: str | None = None) -> dict | None:
    svc = UserService()
    user, temp_password = svc.reset_password(user_id, custom_password=custom_password)
    audit_log("reset_password", admin_id, target_user=user_id)
    return {"user": format_user(user), "temporary_password": temp_password}


def get_dashboard_stats() -> dict:
    svc = UserService()
    users = svc.list_all()
    return {
        "total_users": len(users),
        "administrators": sum(1 for u in users if u.role.value == "admin"),
        "disabled_users": sum(1 for u in users if u.disabled),
        "temp_passwords_active": sum(1 for u in users if u.must_change_password),
    }


def format_user(u: User) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "full_name": u.full_name,
        "role": u.role.value if hasattr(u.role, "value") else u.role,
        "status": u.status.value if hasattr(u.status, "value") else u.status,
        "disabled": u.disabled,
        "must_change_password": u.must_change_password,
        "created_at": u.created_at,
        "last_login": u.last_login,
        "last_login_at": u.last_login_at,
        "last_password_change": u.last_password_change,
    }
