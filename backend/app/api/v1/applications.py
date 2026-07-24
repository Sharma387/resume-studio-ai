from fastapi import Depends,  APIRouter, HTTPException, Query

from app.models.application import Application, ApplicationStatus, TimelineEvent, TimelineEventType
from app.services import application_service as svc
from app.services.auth_deps import require_user

router = APIRouter()


@router.get("/dashboard")
async def dashboard(current_user = Depends(require_user)):
    return {"success": True, "data": svc.get_dashboard()}


@router.get("/applications")
async def list_apps(status: str | None = Query(None), current_user = Depends(require_user)):
    from app.services.storage_service import list_applications
    apps = list_applications(status=status, user_id=current_user.id)
    return {"success": True, "data": apps}


@router.post("/applications")
async def create_app(body: Application, current_user = Depends(require_user)):
    created = svc.create(company=body.company, role_title=body.role_title, user_id=current_user.id, **body.model_dump(exclude={"company", "role_title", "id", "created_at", "updated_at", "user_id"}))
    return {"success": True, "data": created}


@router.get("/applications/{app_id}")
async def get_app(app_id: str, current_user = Depends(require_user)):
    view = svc.get_view(app_id, current_user.id)
    if view is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return {"success": True, "data": view}


@router.put("/applications/{app_id}")
async def update_app(app_id: str, body: Application, current_user = Depends(require_user)):
    updated = svc.update(app_id, user_id=current_user.id, **body.model_dump(exclude_unset=True))
    if updated is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return {"success": True, "data": updated}


@router.delete("/applications/{app_id}")
async def delete_app(app_id: str, current_user = Depends(require_user)):
    if not svc.delete(app_id, current_user.id):
        raise HTTPException(status_code=404, detail="Application not found")
    return {"success": True}


@router.patch("/applications/{app_id}/status")
async def change_status(app_id: str, body: dict, current_user = Depends(require_user)):
    new_status = body.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="status is required")
    try:
        status_enum = ApplicationStatus(new_status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {new_status}")
    updated = svc.change_status(app_id, status_enum, current_user.id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return {"success": True, "data": updated}


@router.post("/applications/{app_id}/notes")
async def add_note(app_id: str, body: dict, current_user = Depends(require_user)):
    content = body.get("content", "")
    if not content:
        raise HTTPException(status_code=400, detail="content is required")
    updated = svc.add_note(app_id, content, current_user.id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return {"success": True, "data": updated}


@router.get("/applications/{app_id}/timeline")
async def get_timeline(app_id: str, current_user = Depends(require_user)):
    from app.services.storage_service import list_timeline_events
    events = list_timeline_events(app_id)
    return {"success": True, "data": events}


@router.post("/applications/{app_id}/timeline")
async def add_timeline_event(app_id: str, body: TimelineEvent, current_user = Depends(require_user)):
    from app.services.storage_service import load_application, save_timeline_event
    app = load_application(app_id, current_user.id)
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")
    import uuid
    body.id = uuid.uuid4().hex
    body.application_id = app_id
    save_timeline_event(body)
    return {"success": True, "data": body}
