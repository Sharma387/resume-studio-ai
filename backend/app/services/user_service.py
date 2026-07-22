import uuid
from datetime import datetime, timezone

import bcrypt

from app.models.user import User, AccountStatus
from app.services.repositories.interfaces import UserRepository
from app.services.repositories.json_user_repo import JsonUserRepository


class UserService:
    def __init__(self, repo: UserRepository | None = None):
        self.repo = repo or JsonUserRepository()

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
        user.last_login = datetime.now(timezone.utc).isoformat()
        self.repo.save(user)
        return user

    def change_password(self, user_id: str, current_password: str, new_password: str) -> bool:
        user = self.repo.get_by_id(user_id)
        if user is None:
            return False
        if not self.verify_password(current_password, user.password_hash):
            return False
        user.password_hash = self.hash_password(new_password)
        self.repo.save(user)
        return True
