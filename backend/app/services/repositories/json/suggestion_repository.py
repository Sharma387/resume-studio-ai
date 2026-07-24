from app.models.writer import ResumeSuggestion
from app.services.repositories.interfaces import WriterSuggestionRepository
from app.services import storage_service as store


class JsonWriterSuggestionRepository(WriterSuggestionRepository):
    def save(self, suggestion: ResumeSuggestion) -> None:
        store.save_writer_suggestion(suggestion)

    def get_by_id(self, resume_id: str, suggestion_id: str, user_id: str | None = None) -> ResumeSuggestion | None:
        return store.load_writer_suggestion(resume_id, suggestion_id, user_id)

    def list_by_resume(self, resume_id: str, status: str | None = None, user_id: str | None = None) -> list[ResumeSuggestion]:
        return store.list_writer_suggestions(resume_id, status, user_id)

    def update(self, resume_id: str, suggestion_id: str, user_id: str | None = None, **updates) -> ResumeSuggestion | None:
        return store.update_writer_suggestion(resume_id, suggestion_id, user_id=user_id, **updates)
