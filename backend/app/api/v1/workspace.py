from fastapi import APIRouter, Depends

from app.models.user import User
from app.services.auth_deps import get_current_user
from app.services.workspace_service import get_workspace
from app.services.dashboard_service import get_dashboard_summary

router = APIRouter()


@router.get("/workspace")
async def workspace(current_user: User | None = Depends(get_current_user)):
    data = get_workspace(current_user)
    return {"success": True, "data": data}


@router.get("/dashboard")
async def dashboard(current_user: User | None = Depends(get_current_user)):
    user_id = current_user.id if current_user else None
    data = get_dashboard_summary(user_id)
    return {"success": True, "data": data}
