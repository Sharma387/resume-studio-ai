import pytest
from httpx import AsyncClient, ASGITransport
from pydantic import ValidationError

from app.main import app
from app.models.notification import Notification
from app.services.workspace_service import get_workspace
from app.services.dashboard_service import get_dashboard_summary
from app.services.sync_service import SyncService, SyncStatus
from app.services.repositories.json_base import JsonBaseRepository
from app.models.resume import Resume
from app.models.cover_letter import CoverLetter


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class TestNotificationModel:
    def test_valid(self):
        n = Notification(id="n1", user_id="u1", type="resume_exported", title="Resume Exported")
        assert n.read is False
        assert n.type == "resume_exported"

    def test_minimal(self):
        n = Notification(id="n2", user_id="u1", type="test", title="Hi")
        assert n.message == ""

    def test_invalid_no_type(self):
        with pytest.raises(ValidationError):
            Notification(id="n3", user_id="u1", title="No Type")


class TestJsonBaseRepository:
    def test_save_and_get(self, tmp_path):
        class TestRepo(JsonBaseRepository[Resume]):
            model_class = Resume
            sub_dir = "test_resumes"

        repo = TestRepo()
        repo.root = tmp_path / "test_resumes"
        repo.root.mkdir()

        resume = Resume(full_name="Test User", email="t@t.com")
        repo.save("repo-test-1", resume)
        loaded = repo.get("repo-test-1")
        assert loaded is not None
        assert loaded.full_name == "Test User"


class TestDashboardService:
    def test_returns_summary(self):
        summary = get_dashboard_summary()
        assert "resumes" in summary
        assert "applications" in summary
        assert "ats" in summary
        assert "interviews" in summary
        assert "cover_letters" in summary
        assert "ai_suggestions" in summary

    def test_never_stores_data(self):
        from app.services.dashboard_service import get_dashboard_summary
        s1 = get_dashboard_summary()
        s2 = get_dashboard_summary()
        # Multiple calls should work (no side effects)
        assert s1["resumes"]["total"] == s2["resumes"]["total"]


class TestWorkspaceService:
    def test_returns_workspace_without_user(self):
        ws = get_workspace(None)
        assert "user" in ws
        assert ws["user"] is None
        assert "dashboard" in ws

    def test_returns_active_resume(self):
        ws = get_workspace(None)
        assert "active_resume" in ws
        assert "dashboard" in ws


class TestSyncService:
    def test_queue(self):
        svc = SyncService()
        svc.mark_dirty("resume", "r1")
        assert svc.queue_size() == 1

    def test_status(self):
        svc = SyncService()
        svc.mark_dirty("resume", "r1")
        svc.mark_dirty("cover_letter", "c1")
        status = svc.get_status()
        assert status["queued"] == 2

    def test_push_not_implemented(self):
        svc = SyncService()
        import pytest
        with pytest.raises(NotImplementedError):
            import asyncio
            asyncio.run(svc.push())

    def test_resolve_conflicts_remote_wins(self):
        svc = SyncService()
        result = svc.resolve_conflicts({"name": "local"}, {"name": "remote"})
        assert result["name"] == "remote"


class TestWorkspaceEndpoints:
    @pytest.mark.asyncio
    async def test_dashboard_endpoint(self, client):
        async with client as ac:
            resp = await ac.get("/api/v1/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        # New dashboard format has module-level keys
        assert any(k in data["data"] for k in ("resumes", "applications", "total"))

    @pytest.mark.asyncio
    async def test_workspace_endpoint(self, client):
        async with client as ac:
            resp = await ac.get("/api/v1/workspace")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "dashboard" in data["data"]
