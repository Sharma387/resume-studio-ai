import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import AccountStatus, SubscriptionTier, User, UserRole


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        default=lambda: uuid.uuid4().hex,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=UserRole.USER.value,
    )
    subscription: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=SubscriptionTier.FREE.value,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=AccountStatus.ACTIVE.value,
    )
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    disabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=lambda: datetime.now(UTC).isoformat(),
    )
    last_login: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_login_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_password_change: Mapped[str | None] = mapped_column(String(32), nullable=True)

    refresh_tokens: Mapped[list["RefreshTokenModel"]] = relationship(
        "RefreshTokenModel",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint("role IN ('user', 'admin')", name="ck_users_role"),
        CheckConstraint(
            "subscription IN ('free', 'pro', 'enterprise')",
            name="ck_users_subscription",
        ),
        CheckConstraint(
            "status IN ('active', 'pending', 'locked', 'disabled')",
            name="ck_users_status",
        ),
    )

    def to_pydantic(self) -> User:
        return User(
            id=self.id,
            email=self.email,
            password_hash=self.password_hash,
            full_name=self.full_name,
            role=self.role,
            subscription=self.subscription,
            status=self.status,
            email_verified=self.email_verified,
            is_active=self.is_active,
            must_change_password=self.must_change_password,
            disabled=self.disabled,
            created_at=self.created_at,
            last_login=self.last_login,
            last_login_at=self.last_login_at,
            last_password_change=self.last_password_change,
        )

    @classmethod
    def from_pydantic(cls, user: User) -> "UserModel":
        def _val(v):
            return v.value if hasattr(v, "value") else v

        return cls(
            id=user.id,
            email=user.email,
            password_hash=user.password_hash,
            full_name=user.full_name,
            role=_val(user.role),
            subscription=_val(user.subscription),
            status=_val(user.status),
            email_verified=user.email_verified,
            is_active=user.is_active,
            must_change_password=user.must_change_password,
            disabled=user.disabled,
            created_at=user.created_at,
            last_login=user.last_login,
            last_login_at=user.last_login_at,
            last_password_change=user.last_password_change,
        )


class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    expires_at: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=lambda: datetime.now(UTC).isoformat(),
    )

    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="refresh_tokens",
    )
