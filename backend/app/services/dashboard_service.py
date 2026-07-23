"""Dashboard service — READ-ONLY aggregator. Never stores data."""

from app.services.repositories.domain_repos import (
    ResumeRepository,
    CoverLetterRepository,
    InterviewSessionRepository,
    ResumeSuggestionRepository,
    MatchRepository,
)
from app.services.storage_service import list_applications


def get_dashboard_summary(user_id: str | None = None) -> dict:
    resume_repo = ResumeRepository()
    cover_repo = CoverLetterRepository()
    interview_repo = InterviewSessionRepository()
    suggestion_repo = ResumeSuggestionRepository()
    match_repo = MatchRepository()

    def _filter(items: list, field: str = "resume_id") -> list:
        if not user_id:
            return items
        return [i for i in items if getattr(i, field, None) == user_id or getattr(i, "user_id", None) == user_id]

    all_resumes = _filter(resume_repo.list_all(), "full_name")
    all_covers = _filter(cover_repo.list_all(), "resume_id")
    all_interviews = interview_repo.list_all()
    all_apps = list_applications()
    all_suggestions = suggestion_repo.list_all()
    all_matches = match_repo.list_all()

    resume_total = len(all_resumes)
    resume_with_summary = sum(1 for r in all_resumes if r.summary)

    apps_by_status: dict[str, int] = {}
    active_apps = 0
    interview_apps = 0
    for a in all_apps:
        s = a.status.value
        apps_by_status[s] = apps_by_status.get(s, 0) + 1
        if s not in ("rejected", "withdrawn", "archived"):
            active_apps += 1
        if s == "interviewing":
            interview_apps += 1

    avg_ats = round(sum(m.overall_score for m in all_matches) / len(all_matches), 1) if all_matches else 0.0

    pending_suggestions = sum(1 for s in all_suggestions if s.status == "pending")
    interview_total = len(all_interviews)
    cover_total = len(all_covers)

    return {
        "resumes": {"total": resume_total, "with_summary": resume_with_summary},
        "applications": {"total": len(all_apps), "active": active_apps, "interviewing": interview_apps, "by_status": apps_by_status},
        "ats": {"total_matches": len(all_matches), "average_score": avg_ats},
        "interviews": {"total": interview_total},
        "cover_letters": {"total": cover_total},
        "ai_suggestions": {"total": len(all_suggestions), "pending": pending_suggestions},
    }
