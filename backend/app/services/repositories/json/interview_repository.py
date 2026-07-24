from app.models.interview import InterviewSession
from app.services.repositories.interfaces import InterviewSessionRepository
from app.services import storage_service as store


class JsonInterviewSessionRepository(InterviewSessionRepository):
    def save(self, session: InterviewSession) -> None:
        store.save_interview_session(session)

    def get_by_id(self, application_id: str, session_id: str, user_id: str | None = None) -> InterviewSession | None:
        return store.load_interview_session(application_id, session_id, user_id)

    def list_by_application(self, application_id: str, user_id: str | None = None) -> list[InterviewSession]:
        return store.list_interview_sessions(application_id, user_id)

    def delete(self, application_id: str, session_id: str) -> bool:
        return store.delete_interview_session(application_id, session_id)
