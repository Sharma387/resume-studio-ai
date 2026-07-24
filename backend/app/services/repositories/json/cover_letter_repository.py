from app.models.cover_letter import CoverLetter
from app.services.repositories.interfaces import CoverLetterRepository
from app.services import storage_service as store


class JsonCoverLetterRepository(CoverLetterRepository):
    def save(self, letter: CoverLetter) -> None:
        store.save_cover_letter(letter)

    def get_by_id(self, resume_id: str, letter_id: str, user_id: str | None = None) -> CoverLetter | None:
        return store.load_cover_letter(resume_id, letter_id, user_id)

    def list_by_resume(self, resume_id: str, user_id: str | None = None) -> list[CoverLetter]:
        return store.list_cover_letters(resume_id, user_id)

    def delete(self, resume_id: str, letter_id: str, user_id: str | None = None) -> bool:
        return store.delete_cover_letter(resume_id, letter_id, user_id)
