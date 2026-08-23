from sqlalchemy import text

from app.db.database import get_sync_session
from app.db.models.user import UserModel
from app.models.user import User
from app.services.repositories.interfaces import UserRepository


class PostgresUserRepository(UserRepository):
    def save(self, user: User) -> None:
        session = get_sync_session()
        try:
            existing = session.get(UserModel, user.id)
            if existing:
                for key, value in UserModel.from_pydantic(user).__dict__.items():
                    if key != "_sa_instance_state":
                        setattr(existing, key, value)
            else:
                session.add(UserModel.from_pydantic(user))
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_by_id(self, user_id: str) -> User | None:
        session = get_sync_session()
        try:
            model = session.get(UserModel, user_id)
            return model.to_pydantic() if model else None
        finally:
            session.close()

    def get_by_email(self, email: str) -> User | None:
        session = get_sync_session()
        try:
            model = session.query(UserModel).filter(text("LOWER(email) = LOWER(:email)")).params(email=email).first()
            return model.to_pydantic() if model else None
        finally:
            session.close()

    def list_all(self) -> list[User]:
        session = get_sync_session()
        try:
            models = session.query(UserModel).order_by(UserModel.created_at.desc()).all()
            return [m.to_pydantic() for m in models]
        finally:
            session.close()

    def delete(self, user_id: str) -> bool:
        session = get_sync_session()
        try:
            model = session.get(UserModel, user_id)
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
