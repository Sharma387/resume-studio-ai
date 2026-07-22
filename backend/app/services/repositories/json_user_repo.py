import json
from pathlib import Path

from app.models.user import User
from app.services.repositories.interfaces import UserRepository

USERS_DIR = Path("storage") / "users"
USERS_DIR.mkdir(parents=True, exist_ok=True)


class JsonUserRepository(UserRepository):
    def save(self, user: User) -> None:
        path = USERS_DIR / f"{user.id}.json"
        path.write_text(user.model_dump_json(indent=2), encoding="utf-8")

    def get_by_id(self, user_id: str) -> User | None:
        path = USERS_DIR / f"{user_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return User(**data)

    def get_by_email(self, email: str) -> User | None:
        if not USERS_DIR.exists():
            return None
        email_lower = email.lower().strip()
        for f in USERS_DIR.iterdir():
            if f.suffix == ".json":
                data = json.loads(f.read_text(encoding="utf-8"))
                if data.get("email", "").lower().strip() == email_lower:
                    return User(**data)
        return None

    def list_all(self) -> list[User]:
        if not USERS_DIR.exists():
            return []
        users = []
        for f in USERS_DIR.iterdir():
            if f.suffix == ".json":
                data = json.loads(f.read_text(encoding="utf-8"))
                users.append(User(**data))
        return users

    def delete(self, user_id: str) -> bool:
        path = USERS_DIR / f"{user_id}.json"
        if not path.exists():
            return False
        path.unlink()
        return True
