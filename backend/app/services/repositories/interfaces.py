"""Abstract repository interfaces for dependency inversion.

JSON implementations can be replaced with PostgreSQL repositories
without changing business services.
"""

from abc import ABC, abstractmethod

from app.models.user import User


class UserRepository(ABC):
    @abstractmethod
    def save(self, user: User) -> None: ...

    @abstractmethod
    def get_by_id(self, user_id: str) -> User | None: ...

    @abstractmethod
    def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    def list_all(self) -> list[User]: ...

    @abstractmethod
    def delete(self, user_id: str) -> bool: ...


class RefreshTokenRepository(ABC):
    @abstractmethod
    def save(self, token_hash: str, user_id: str, expires_at: str) -> None: ...

    @abstractmethod
    def get_user_id(self, token_hash: str) -> str | None: ...

    @abstractmethod
    def delete(self, token_hash: str) -> bool: ...

    @abstractmethod
    def delete_all_for_user(self, user_id: str) -> None: ...
