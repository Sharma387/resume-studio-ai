import pytest
from httpx import AsyncClient, ASGITransport
from pydantic import ValidationError

from app.main import app
from app.models.application import Application, ApplicationStatus, ApplicationPriority, TimelineEvent, TimelineEventType, ApplicationNote, DashboardSummary
from app.services.storage_service import save_application, load_application, list_applications
from app.services import application_service as svc


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class TestApplicationModel:
    def test_valid(self):
        a = Application(user_id="test", id="a1", company="Google", role_title="Engineer")
        assert a.status == ApplicationStatus.DRAFT
        assert a.priority == ApplicationPriority.MEDIUM

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            Application(user_id="test", id="a2", company="G", role_title="R", status="invalid")

    def test_invalid_priority(self):
        with pytest.raises(ValidationError):
            Application(user_id="test", id="a3", company="G", role_title="R", priority="urgent")

    def test_archived_status(self):
        a = Application(user_id="test", id="a4", company="G", role_title="R", status=ApplicationStatus.ARCHIVED)
        assert a.status == ApplicationStatus.ARCHIVED


class TestTimelineEvent:
    def test_valid(self):
        e = TimelineEvent(id="e1", application_id="a1")
        assert e.event_type == TimelineEventType.CUSTOM

    def test_resume_updated_type(self):
        e = TimelineEvent(id="e2", application_id="a1", event_type=TimelineEventType.RESUME_UPDATED)
        assert e.event_type == TimelineEventType.RESUME_UPDATED


class TestApplicationNote:
    def test_valid(self):
        n = ApplicationNote(id="n1", content="Called recruiter")
        assert n.content == "Called recruiter"

    def test_empty_content(self):
        with pytest.raises(ValidationError):
            ApplicationNote(id="n2", content="")


class TestApplicationService:
    def test_create(self):
        a = svc.create(company="Stripe", role_title="Staff Engineer", user_id="test")
        assert a.id is not None
        assert a.company == "Stripe"
        assert a.status == ApplicationStatus.DRAFT

    def test_get_not_found(self):
        assert svc.get("nonexistent") is None

    def test_create_adds_timeline(self):
        a = svc.create(company="Meta", role_title="Engineer", user_id="test")
        from app.services.storage_service import list_timeline_events
        events = list_timeline_events(a.id)
        assert len(events) >= 1
        assert events[0].event_type == TimelineEventType.CREATED

    def test_change_status(self):
        a = svc.create(company="A", role_title="B", user_id="test")
        updated = svc.change_status(a.id, ApplicationStatus.APPLIED)
        assert updated.status == ApplicationStatus.APPLIED

    def test_change_status_adds_timeline(self):
        a = svc.create(company="A", role_title="B", user_id="test")
        svc.change_status(a.id, ApplicationStatus.INTERVIEWING)
        from app.services.storage_service import list_timeline_events
        events = list_timeline_events(a.id)
        status_events = [e for e in events if e.event_type == TimelineEventType.STATUS_CHANGED]
        assert len(status_events) >= 1

    def test_add_note(self):
        a = svc.create(company="A", role_title="B", user_id="test")
        updated = svc.add_note(a.id, "Spoke with hiring manager")
        assert len(updated.notes) == 1
        assert updated.notes[0].content == "Spoke with hiring manager"

    def test_get_view(self):
        a = svc.create(company="Apple", role_title="iOS Engineer", user_id="test")
        view = svc.get_view(a.id)
        assert view is not None
        assert view.application.company == "Apple"

    def test_dashboard(self):
        svc.create(company="X", role_title="Y", user_id="test")
        dash = svc.get_dashboard()
        assert dash.total >= 1
        assert dash.active >= 1


class TestEndpoints:
    @pytest.mark.asyncio
    async def test_create(self, client):
        async with client as ac:
            resp = await ac.post("/api/v1/applications", json={"id": "e1", "user_id": "test", "company": "Google", "role_title": "Engineer"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["company"] == "Google"

    @pytest.mark.asyncio
    async def test_list(self, client):
        async with client as ac:
            resp = await ac.get("/api/v1/applications")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_not_found(self, client):
        async with client as ac:
            resp = await ac.get("/api/v1/applications/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete(self, client):
        a = svc.create(company="D", role_title="E", user_id="test")
        async with client as ac:
            resp = await ac.delete(f"/api/v1/applications/{a.id}")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_change_status_endpoint(self, client):
        a = svc.create(company="F", role_title="G", user_id="test")
        async with client as ac:
            resp = await ac.patch(f"/api/v1/applications/{a.id}/status", json={"status": "applied"})
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "applied"

    @pytest.mark.asyncio
    async def test_add_note_endpoint(self, client):
        a = svc.create(company="H", role_title="I", user_id="test")
        async with client as ac:
            resp = await ac.post(f"/api/v1/applications/{a.id}/notes", json={"content": "Test note"})
        assert resp.status_code == 200
        assert len(resp.json()["data"]["notes"]) == 1

    @pytest.mark.asyncio
    async def test_dashboard(self, client):
        async with client as ac:
            resp = await ac.get("/api/v1/dashboard")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "total" in data
