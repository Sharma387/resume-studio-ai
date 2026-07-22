import json
from pathlib import Path

from app.services.repositories.interfaces import RefreshTokenRepository

TOKENS_DIR = Path("storage") / "refresh_tokens"
TOKENS_DIR.mkdir(parents=True, exist_ok=True)


class JsonRefreshTokenRepository(RefreshTokenRepository):
    def save(self, token_hash: str, user_id: str, expires_at: str) -> None:
        path = TOKENS_DIR / f"{token_hash}.json"
        data = {"user_id": user_id, "expires_at": expires_at}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def get_user_id(self, token_hash: str) -> str | None:
        path = TOKENS_DIR / f"{token_hash}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("user_id")

    def delete(self, token_hash: str) -> bool:
        path = TOKENS_DIR / f"{token_hash}.json"
        if not path.exists():
            return False
        path.unlink()
        return True

    def delete_all_for_user(self, user_id: str) -> None:
        if not TOKENS_DIR.exists():
            return
        for f in TOKENS_DIR.iterdir():
            if f.suffix == ".json":
                data = json.loads(f.read_text(encoding="utf-8"))
                if data.get("user_id") == user_id:
                    f.unlink()
