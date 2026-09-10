import uuid
from datetime import UTC, datetime

import bcrypt

from app.models.user import AccountStatus, User, UserRole
from app.services.repositories.factory import get_user_repository
from app.services.repositories.interfaces import UserRepository


class UserService:
    def __init__(self, repo: UserRepository | None = None):
        self.repo = repo or get_user_repository()

    def hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def verify_password(self, plain: str, hashed: str) -> bool:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

    def create_user(self, email: str, password: str, full_name: str) -> User:
        existing = self.repo.get_by_email(email)
        if existing:
            raise ValueError("Email already registered")

        user = User(
            id=uuid.uuid4().hex,
            email=email,
            password_hash=self.hash_password(password),
            full_name=full_name,
        )
        self.repo.save(user)
        return user

    def get_by_id(self, user_id: str) -> User | None:
        return self.repo.get_by_id(user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.repo.get_by_email(email)

    def authenticate(self, email: str, password: str) -> User | None:
        user = self.repo.get_by_email(email)
        if user is None:
            return None
        if user.status != AccountStatus.ACTIVE:
            return None
        if not self.verify_password(password, user.password_hash):
            return None
        user.last_login = datetime.now(UTC).isoformat()
        self.repo.save(user)
        return user

    def change_password(self, user_id: str, current_password: str, new_password: str) -> bool:
        user = self.repo.get_by_id(user_id)
        if user is None:
            return False
        if not self.verify_password(current_password, user.password_hash):
            return False
        user.password_hash = self.hash_password(new_password)
        user.must_change_password = False
        user.last_password_change = datetime.now(UTC).isoformat()
        self.repo.save(user)
        return True

    def list_all(self) -> list[User]:
        return self.repo.list_all()

    def disable_user(self, user_id: str) -> User | None:
        user = self.repo.get_by_id(user_id)
        if user is None:
            return None
        user.disabled = True
        user.status = AccountStatus.DISABLED
        self.repo.save(user)
        return user

    def enable_user(self, user_id: str) -> User | None:
        user = self.repo.get_by_id(user_id)
        if user is None:
            return None
        user.disabled = False
        user.status = AccountStatus.ACTIVE
        self.repo.save(user)
        return user

    def promote_to_admin(self, user_id: str) -> User | None:
        user = self.repo.get_by_id(user_id)
        if user is None:
            return None
        user.role = UserRole.ADMIN
        self.repo.save(user)
        return user

    def demote_to_user(self, user_id: str, requester_id: str) -> User | None:
        if user_id == requester_id:
            raise ValueError("Cannot demote yourself")
        user = self.repo.get_by_id(user_id)
        if user is None:
            return None
        admin_count = sum(1 for u in self.list_all() if u.role == UserRole.ADMIN)
        if admin_count <= 1:
            raise ValueError("Cannot demote the last administrator")
        user.role = UserRole.USER
        self.repo.save(user)
        return user

    def reset_password(self, user_id: str, custom_password: str | None = None) -> tuple[User, str]:
        user = self.repo.get_by_id(user_id)
        if user is None:
            raise ValueError("User not found")
        if custom_password:
            from app.services.password_policy import validate as validate_pwd

            validate_pwd(custom_password)
            new_password = custom_password
        else:
            from app.services.password_policy import generate_temporary

            new_password = generate_temporary()
        user.password_hash = self.hash_password(new_password)
        user.must_change_password = True
        user.last_password_change = datetime.now(UTC).isoformat()
        self.repo.save(user)
        return user, new_password

    def update_profile(self, user_id: str, full_name: str) -> User | None:
        user = self.repo.get_by_id(user_id)
        if user is None:
            return None
        user.full_name = full_name
        self.repo.save(user)
        return user
