from app.models.match import MatchResult
from app.services.repositories.interfaces import MatchRepository
from app.services import storage_service as store


class JsonMatchRepository(MatchRepository):
    def save(self, match_id: str, match: MatchResult) -> None:
        store.save_match(match)

    def get_by_id(self, match_id: str, user_id: str | None = None) -> MatchResult | None:
        return store.load_match(match_id, user_id)

    def list_by_resume(self, resume_id: str, user_id: str | None = None) -> list[MatchResult]:
        return store.list_matches(resume_id, user_id)
