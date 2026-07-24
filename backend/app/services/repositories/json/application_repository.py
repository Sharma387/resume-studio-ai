from app.models.application import Application
from app.services.repositories.interfaces import ApplicationRepository
from app.services import storage_service as store


class JsonApplicationRepository(ApplicationRepository):
    def save(self, app: Application) -> None:
        store.save_application(app)

    def get_by_id(self, app_id: str, user_id: str | None = None) -> Application | None:
        return store.load_application(app_id, user_id)

    def list_by_user(self, user_id: str | None = None, status: str | None = None) -> list[Application]:
        return store.list_applications(status=status, user_id=user_id)

    def delete(self, app_id: str, user_id: str | None = None) -> bool:
        return store.delete_application(app_id, user_id)
