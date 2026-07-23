"""WorkspaceService — central aggregator for the user's Career Workspace.

Aggregates data from all existing services into a single Workspace DTO.
Does not store any data itself.
"""

from app.models.user import User
from app.services.dashboard_service import get_dashboard_summary
from app.services.storage_service import load_resume


def get_workspace(user: User | None) -> dict:
    user_id = user.id if user else None
    dashboard = get_dashboard_summary(user_id)

    active_resume = None
    if user_id:
        from app.services.repositories.domain_repos import ResumeRepository
        repo = ResumeRepository()
        resumes = repo.list_by_field("user_id", user_id)
        if resumes:
            active_resume = resumes[0]

    return {
        "user": {
            "id": user.id if user else None,
            "email": user.email if user else None,
            "full_name": user.full_name if user else None,
        } if user else None,
        "active_resume": active_resume.model_dump() if active_resume else None,
        "dashboard": dashboard,
    }
