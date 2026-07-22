import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import settings
from app.models.user import User, TokenPair
from app.services.repositories.interfaces import RefreshTokenRepository
from app.services.repositories.json_token_repo import JsonRefreshTokenRepository
from app.services.user_service import UserService


class AuthenticationService:
    def __init__(
        self,
        user_service: UserService | None = None,
        token_repo: RefreshTokenRepository | None = None,
    ):
        self.user_service = user_service or UserService()
        self.token_repo = token_repo or JsonRefreshTokenRepository()

    # ── Token generation ────────────────────────────────────────

    def _hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _create_access_token(self, user: User) -> tuple[str, str]:
        jti = uuid.uuid4().hex
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_expire_minutes)
        payload = {
            "sub": user.id,
            "jti": jti,
            "role": user.role.value,
            "exp": expire,
            "type": "access",
        }
        token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        return token, jti

    def _create_refresh_token(self, user: User) -> tuple[str, str]:
        jti = uuid.uuid4().hex
        expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_expire_days)
        payload = {
            "sub": user.id,
            "jti": jti,
            "exp": expire,
            "type": "refresh",
        }
        token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        token_hash = self._hash_token(token)

        self.token_repo.save(
            token_hash=token_hash,
            user_id=user.id,
            expires_at=expire.isoformat(),
        )
        return token, jti

    def create_token_pair(self, user: User) -> TokenPair:
        access_token, _ = self._create_access_token(user)
        refresh_token, _ = self._create_refresh_token(user)
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.jwt_access_expire_minutes * 60,
        )

    # ── Token validation ────────────────────────────────────────

    def validate_access_token(self, token: str) -> dict | None:
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            if payload.get("type") != "access":
                return None
            return payload
        except JWTError:
            return None

    def validate_refresh_token(self, token: str) -> User | None:
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            if payload.get("type") != "refresh":
                return None

            jti = payload.get("jti")
            user_id = payload.get("sub")
            if not jti or not user_id:
                return None

            # Verify token hash exists in storage
            token_hash = self._hash_token(token)
            stored_user_id = self.token_repo.get_user_id(token_hash)
            if stored_user_id != user_id:
                return None

            return self.user_service.get_by_id(user_id)
        except JWTError:
            return None

    def refresh_token_pair(self, refresh_token: str) -> TokenPair | None:
        user = self.validate_refresh_token(refresh_token)
        if user is None:
            return None

        # Revoke old refresh token (rotation)
        token_hash = self._hash_token(refresh_token)
        self.token_repo.delete(token_hash)

        # Issue new pair
        return self.create_token_pair(user)

    def logout(self, refresh_token: str) -> None:
        token_hash = self._hash_token(refresh_token)
        self.token_repo.delete(token_hash)

    def logout_all(self, user_id: str) -> None:
        self.token_repo.delete_all_for_user(user_id)
