from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.models.user import User
from app.services.auth_service import AuthenticationService

_bearer = HTTPBearer(auto_error=False)
_auth_service = AuthenticationService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> User | None:
    """Return the current user or None (optional auth)."""
    if credentials is None:
        return None
    payload = _auth_service.validate_access_token(credentials.credentials)
    if payload is None:
        return None
    user_service = _auth_service.user_service
    return user_service.get_by_id(payload.get("sub", ""))


async def require_user(current_user: User | None = Depends(get_current_user)) -> User:
    """Require a valid authenticated user."""
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


async def require_admin(current_user: User = Depends(require_user)) -> User:
    """Require an admin user."""
    from app.models.user import UserRole
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def check_resource_owner(resource_user_id: str | None, current_user: User) -> None:
    """Verify the current user owns the resource (or is admin)."""
    from app.models.user import UserRole
    if current_user.role == UserRole.ADMIN:
        return
    if resource_user_id is None:
        return  # Allow during migration — resources without user_id
    if resource_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this resource",
        )
