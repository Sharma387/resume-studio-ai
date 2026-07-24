from app.models.version import ResumeVersion
from app.services.repositories.interfaces import ResumeVersionRepository
from app.services import storage_service as store


class JsonResumeVersionRepository(ResumeVersionRepository):
    def save(self, version: ResumeVersion) -> None:
        store.save_version(version)

    def get_by_id(self, resume_id: str, version_id: str, user_id: str | None = None) -> ResumeVersion | None:
        return store.load_version(resume_id, version_id, user_id)

    def list_by_resume(self, resume_id: str, user_id: str | None = None) -> list[ResumeVersion]:
        return store.list_versions(resume_id, user_id)
