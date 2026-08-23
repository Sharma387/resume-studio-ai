from sqlalchemy import text

from app.db.database import get_sync_session
from app.db.models.user import RefreshTokenModel
from app.services.repositories.interfaces import RefreshTokenRepository


class PostgresRefreshTokenRepository(RefreshTokenRepository):
    def save(self, token_hash: str, user_id: str, expires_at: str) -> None:
        session = get_sync_session()
        try:
            session.add(
                RefreshTokenModel(
                    token_hash=token_hash,
                    user_id=user_id,
                    expires_at=expires_at,
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_user_id(self, token_hash: str) -> str | None:
        session = get_sync_session()
        try:
            model = session.get(RefreshTokenModel, token_hash)
            return model.user_id if model else None
        finally:
            session.close()

    def delete(self, token_hash: str) -> bool:
        session = get_sync_session()
        try:
            model = session.get(RefreshTokenModel, token_hash)
            if model is None:
                return False
            session.delete(model)
            session.commit()
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete_all_for_user(self, user_id: str) -> None:
        session = get_sync_session()
        try:
            session.execute(
                text("DELETE FROM refresh_tokens WHERE user_id = :user_id"),
                {"user_id": user_id},
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
