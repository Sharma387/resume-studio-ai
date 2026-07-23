from fastapi import APIRouter, HTTPException, Query

from app.models.application import Application, ApplicationStatus, TimelineEvent, TimelineEventType
from app.services import application_service as svc

router = APIRouter()


@router.get("/applications")
async def list_apps(status: str | None = Query(None)):
    from app.services.storage_service import list_applications
    apps = list_applications(status=status)
    return {"success": True, "data": apps}


@router.post("/applications")
async def create_app(body: Application):
    created = svc.create(company=body.company, role_title=body.role_title, **body.model_dump(exclude={"company", "role_title", "id", "created_at", "updated_at"}))
    return {"success": True, "data": created}


@router.get("/applications/{app_id}")
async def get_app(app_id: str):
    view = svc.get_view(app_id)
    if view is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return {"success": True, "data": view}


@router.put("/applications/{app_id}")
async def update_app(app_id: str, body: Application):
    updated = svc.update(app_id, **body.model_dump(exclude_unset=True))
    if updated is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return {"success": True, "data": updated}


@router.delete("/applications/{app_id}")
async def delete_app(app_id: str):
    if not svc.delete(app_id):
        raise HTTPException(status_code=404, detail="Application not found")
    return {"success": True}


@router.patch("/applications/{app_id}/status")
async def change_status(app_id: str, body: dict):
    new_status = body.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="status is required")
    try:
        status_enum = ApplicationStatus(new_status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {new_status}")
    updated = svc.change_status(app_id, status_enum)
    if updated is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return {"success": True, "data": updated}


@router.post("/applications/{app_id}/notes")
async def add_note(app_id: str, body: dict):
    content = body.get("content", "")
    if not content:
        raise HTTPException(status_code=400, detail="content is required")
    updated = svc.add_note(app_id, content)
    if updated is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return {"success": True, "data": updated}


@router.get("/applications/{app_id}/timeline")
async def get_timeline(app_id: str):
    from app.services.storage_service import list_timeline_events
    events = list_timeline_events(app_id)
    return {"success": True, "data": events}


@router.post("/applications/{app_id}/timeline")
async def add_timeline_event(app_id: str, body: TimelineEvent):
    from app.services.storage_service import load_application, save_timeline_event
    app = load_application(app_id)
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")
    import uuid
    body.id = uuid.uuid4().hex
    body.application_id = app_id
    save_timeline_event(body)
    return {"success": True, "data": body}
