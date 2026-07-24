from app.models.resume import Resume
from app.services.repositories.interfaces import ResumeRepository
from app.services import storage_service as store


class JsonResumeRepository(ResumeRepository):
    def save(self, resume_id: str, resume: Resume) -> None:
        store.save_resume(resume_id, resume)

    def get_by_id(self, resume_id: str, user_id: str | None = None) -> Resume | None:
        return store.load_resume(resume_id, user_id)

    def list_by_user(self, user_id: str, limit: int = 10) -> list[tuple[str, Resume]]:
        return store.list_resumes(user_id=user_id, limit=limit)
