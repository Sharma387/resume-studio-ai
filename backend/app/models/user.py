from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class SubscriptionTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class AccountStatus(str, Enum):
    ACTIVE = "active"
    PENDING = "pending"
    LOCKED = "locked"
    DISABLED = "disabled"


class OwnedResource(BaseModel):
    """Base model for resources that belong to a user."""
    user_id: str | None = Field(None, description="Owner user ID. None during migration.")


class User(BaseModel):
    id: str = Field(..., min_length=1)
    email: EmailStr
    password_hash: str
    full_name: str = Field(..., min_length=1)
    role: UserRole = UserRole.USER
    subscription: SubscriptionTier = SubscriptionTier.FREE
    status: AccountStatus = AccountStatus.ACTIVE
    email_verified: bool = False
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_login: str | None = None


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
