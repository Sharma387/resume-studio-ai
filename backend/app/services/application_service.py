import uuid
from datetime import datetime, timezone

from app.models.application import (
    Application,
    ApplicationStatus,
    ApplicationView,
    DashboardSummary,
    TimelineEvent,
    TimelineEventType,
    ApplicationNote,
)
from app.services.repositories.factory import (
    get_application_repository,
    get_timeline_event_repository,
    get_resume_repository,
    get_cover_letter_repository,
    get_match_repository,
    get_interview_session_repository,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _add_timeline(app_id: str, event_type: TimelineEventType, title: str, description: str = "", metadata: dict | None = None) -> TimelineEvent:
    event = TimelineEvent(
        id=uuid.uuid4().hex,
        application_id=app_id,
        event_type=event_type,
        title=title,
        description=description,
        metadata=metadata or {},
    )
    get_timeline_event_repository().save(event)
    return event


def create(company: str, role_title: str, user_id: str, **kwargs) -> Application:
    app = Application(
        id=uuid.uuid4().hex,
        user_id=user_id,
        company=company,
        role_title=role_title,
        **{k: v for k, v in kwargs.items() if k in Application.model_fields and k not in ("id", "created_at", "updated_at")},
    )
    get_application_repository().save(app)
    _add_timeline(app.id, TimelineEventType.CREATED, f"Application created", f"Added {role_title} at {company}")
    return app


def get(app_id: str, user_id: str | None = None) -> Application | None:
    return get_application_repository().get_by_id(app_id, user_id)


def update(app_id: str, user_id: str | None = None, **kwargs) -> Application | None:
    app = get_application_repository().get_by_id(app_id, user_id)
    if app is None:
        return None
    for key, value in kwargs.items():
        if key in Application.model_fields and key not in ("id", "created_at"):
            setattr(app, key, value)
    app.updated_at = _now()
    app.last_activity = _now()
    get_application_repository().save(app)
    return app


def delete(app_id: str, user_id: str | None = None) -> bool:
    return get_application_repository().delete(app_id, user_id)


def change_status(app_id: str, new_status: ApplicationStatus, user_id: str | None = None) -> Application | None:
    app = get_application_repository().get_by_id(app_id, user_id)
    if app is None:
        return None
    old = app.status.value
    app.status = new_status
    app.updated_at = _now()
    app.last_activity = _now()
    get_application_repository().save(app)
    _add_timeline(
        app_id, TimelineEventType.STATUS_CHANGED,
        f"Status changed to {new_status.value}",
        f"Moved from {old} to {new_status.value}",
        {"old_status": old, "new_status": new_status.value},
    )
    return app


def add_note(app_id: str, content: str, user_id: str | None = None) -> Application | None:
    app = get_application_repository().get_by_id(app_id, user_id)
    if app is None:
        return None
    note = ApplicationNote(id=uuid.uuid4().hex, content=content)
    app.notes.append(note)
    app.updated_at = _now()
    app.last_activity = _now()
    get_application_repository().save(app)
    _add_timeline(app_id, TimelineEventType.NOTE_ADDED, "Note added", content[:100])
    return app


def get_view(app_id: str, user_id: str | None = None) -> ApplicationView | None:
    app = get_application_repository().get_by_id(app_id, user_id)
    if app is None:
        return None

    resume_name = None
    if app.resume_id:
        resume = load_resume(app.resume_id)
        if resume:
            resume_name = resume.full_name

    timeline = get_timeline_event_repository().list_by_application(app_id)[:10]

    
    sessions = get_interview_session_repository().list_by_application(app_id, user_id)
    assessments = []  # TODO: implement readiness assessment storage

    latest_session = sessions[0].model_dump() if sessions else None
    latest_readiness = assessments[0].model_dump() if assessments else None

    return ApplicationView(
        application=app,
        resume_name=resume_name,
        cover_letter_count=len(app.cover_letter_ids),
        match_count=len(app.match_ids),
        version_count=len(app.version_ids),
        interview_count=len(sessions),
        latest_interview_session=latest_session,
        latest_readiness=latest_readiness,
        recent_timeline=timeline,
    )


def get_dashboard() -> DashboardSummary:
    apps = get_application_repository().list_by_user()
    by_status: dict[str, int] = {}
    by_priority: dict[str, int] = {}
    active = 0
    interviews = 0
    offers = 0

    for a in apps:
        s = a.status.value
        by_status[s] = by_status.get(s, 0) + 1
        p = a.priority.value
        by_priority[p] = by_priority.get(p, 0) + 1
        if s not in ("rejected", "withdrawn", "archived"):
            active += 1
        if s == "interviewing":
            interviews += 1
        if s == "offered":
            offers += 1

    return DashboardSummary(
        total=len(apps),
        by_status=by_status,
        by_priority=by_priority,
        active=active,
        interviews=interviews,
        offers=offers,
        recent_applications=apps[:5],
    )
