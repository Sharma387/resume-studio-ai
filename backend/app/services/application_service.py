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
from app.services.storage_service import (
    save_application,
    load_application,
    list_applications,
    delete_application,
    save_timeline_event,
    list_timeline_events,
    load_resume,
    load_cover_letter,
    load_match,
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
    save_timeline_event(event)
    return event


def create(company: str, role_title: str, user_id: str, **kwargs) -> Application:
    app = Application(
        id=uuid.uuid4().hex,
        user_id=user_id,
        company=company,
        role_title=role_title,
        **{k: v for k, v in kwargs.items() if k in Application.model_fields and k not in ("id", "created_at", "updated_at")},
    )
    save_application(app)
    _add_timeline(app.id, TimelineEventType.CREATED, f"Application created", f"Added {role_title} at {company}")
    return app


def get(app_id: str, user_id: str | None = None) -> Application | None:
    return load_application(app_id, user_id)


def update(app_id: str, user_id: str | None = None, **kwargs) -> Application | None:
    app = load_application(app_id, user_id)
    if app is None:
        return None
    for key, value in kwargs.items():
        if key in Application.model_fields and key not in ("id", "created_at"):
            setattr(app, key, value)
    app.updated_at = _now()
    app.last_activity = _now()
    save_application(app)
    return app


def delete(app_id: str, user_id: str | None = None) -> bool:
    return delete_application(app_id, user_id)


def change_status(app_id: str, new_status: ApplicationStatus, user_id: str | None = None) -> Application | None:
    app = load_application(app_id, user_id)
    if app is None:
        return None
    old = app.status.value
    app.status = new_status
    app.updated_at = _now()
    app.last_activity = _now()
    save_application(app)
    _add_timeline(
        app_id, TimelineEventType.STATUS_CHANGED,
        f"Status changed to {new_status.value}",
        f"Moved from {old} to {new_status.value}",
        {"old_status": old, "new_status": new_status.value},
    )
    return app


def add_note(app_id: str, content: str, user_id: str | None = None) -> Application | None:
    app = load_application(app_id, user_id)
    if app is None:
        return None
    note = ApplicationNote(id=uuid.uuid4().hex, content=content)
    app.notes.append(note)
    app.updated_at = _now()
    app.last_activity = _now()
    save_application(app)
    _add_timeline(app_id, TimelineEventType.NOTE_ADDED, "Note added", content[:100])
    return app


def get_view(app_id: str, user_id: str | None = None) -> ApplicationView | None:
    app = load_application(app_id, user_id)
    if app is None:
        return None

    resume_name = None
    if app.resume_id:
        resume = load_resume(app.resume_id)
        if resume:
            resume_name = resume.full_name

    timeline = list_timeline_events(app_id)[:10]

    from app.services.storage_service import list_interview_sessions, list_readiness_assessments
    sessions = list_interview_sessions(app_id, user_id)
    assessments = list_readiness_assessments(app_id)

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
    apps = list_applications()
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
