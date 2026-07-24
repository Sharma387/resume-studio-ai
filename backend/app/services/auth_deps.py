from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.models.user import User, UserRole
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
    """Require a valid authenticated user. In debug mode, returns a mock user."""
    if current_user is None:
        if settings.debug:
            import uuid
            from app.models.user import User as MockUser
            from app.services.repositories.json_user_repo import JsonUserRepository
            repo = JsonUserRepository()
            mock = repo.get_by_email("dev@resume-studio.ai")
            if not mock:
                mock = MockUser(
                    id="test",
                    email="dev@resume-studio.ai",
                    password_hash=_auth_service.user_service.hash_password("dev-password"),
                    full_name="Dev User",
                )
                repo.save(mock)
            return mock
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


async def require_admin(current_user: User = Depends(require_user)) -> User:
    """Require an admin user."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def check_resource_owner(resource_user_id: str | None, current_user: User) -> None:
    """Verify the current user owns the resource (or is admin)."""
    if current_user.role == UserRole.ADMIN:
        return
    if resource_user_id is None:
        return
    if resource_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this resource",
        )
