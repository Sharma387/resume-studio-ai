from fastapi import APIRouter, Depends, HTTPException

from app.models.user import (
    LoginRequest,
    RegisterRequest,
    RefreshRequest,
    ChangePasswordRequest,
    User,
)
from app.services.auth_service import AuthenticationService
from app.services.auth_deps import require_user, get_current_user

router = APIRouter()
auth_service = AuthenticationService()


@router.post("/auth/register")
async def register(body: RegisterRequest):
    try:
        user = auth_service.user_service.create_user(
            email=body.email,
            password=body.password,
            full_name=body.full_name,
        )
        tokens = auth_service.create_token_pair(user)
        return {"success": True, "data": {"user": user, "tokens": tokens}}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/auth/login")
async def login(body: LoginRequest):
    user = auth_service.user_service.authenticate(body.email, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    tokens = auth_service.create_token_pair(user)
    return {"success": True, "data": {"user": user, "tokens": tokens}}


@router.post("/auth/refresh")
async def refresh(body: RefreshRequest):
    tokens = auth_service.refresh_token_pair(body.refresh_token)
    if tokens is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    return {"success": True, "data": tokens}


@router.post("/auth/logout")
async def logout(body: RefreshRequest, current_user: User = Depends(require_user)):
    auth_service.logout(body.refresh_token)
    return {"success": True}


@router.post("/auth/logout-all")
async def logout_all(current_user: User = Depends(require_user)):
    auth_service.logout_all(current_user.id)
    return {"success": True}


@router.get("/auth/me")
async def get_me(current_user: User = Depends(require_user)):
    return {"success": True, "data": current_user}


@router.put("/auth/me/password")
async def change_password(body: ChangePasswordRequest, current_user: User = Depends(require_user)):
    ok = auth_service.user_service.change_password(current_user.id, body.current_password, body.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    return {"success": True}
