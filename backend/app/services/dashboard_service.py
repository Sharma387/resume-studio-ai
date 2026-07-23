"""Dashboard service — READ-ONLY aggregator. Never stores data.

Aggregates information from all existing services into a single DTO.
"""

from app.models.resume import Resume
from app.services.storage_service import list_applications, list_matches
from app.services.repositories.domain_repos import ResumeRepository, CoverLetterRepository, InterviewSessionRepository, ResumeSuggestionRepository


def get_dashboard_summary(user_id: str | None = None) -> dict:
    resume_repo = ResumeRepository()
    cover_repo = CoverLetterRepository()
    interview_repo = InterviewSessionRepository()
    suggestion_repo = ResumeSuggestionRepository()

    all_resumes = resume_repo.list_by_field("user_id", user_id) if user_id else resume_repo.list_all()
    all_covers = cover_repo.list_by_field("user_id", user_id) if user_id else cover_repo.list_all()
    all_interviews = interview_repo.list_all()
    all_apps = list_applications()
    all_suggestions = suggestion_repo.list_all()

    # Resume stats
    total_resumes = len(all_resumes)
    resume_with_summary = sum(1 for r in all_resumes if r.summary)

    # Application stats
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

    # ATS stats
    all_matches = list_matches("")
    avg_ats_score = 0.0
    if all_matches:
        avg_ats_score = sum(m.overall_score for m in all_matches) / len(all_matches)

    # AI suggestion stats
    pending_suggestions = sum(1 for s in all_suggestions if s.status == "pending")

    # Interview stats
    total_interviews = len(all_interviews)

    return {
        "resumes": {
            "total": total_resumes,
            "with_summary": resume_with_summary,
        },
        "applications": {
            "total": len(all_apps),
            "active": active_apps,
            "interviewing": interview_apps,
            "by_status": apps_by_status,
        },
        "ats": {
            "total_matches": len(all_matches),
            "average_score": round(avg_ats_score, 1),
        },
        "interviews": {
            "total": total_interviews,
        },
        "cover_letters": {
            "total": len(all_covers),
        },
        "ai_suggestions": {
            "total": len(all_suggestions),
            "pending": pending_suggestions,
        },
    }
