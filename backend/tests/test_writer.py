import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.resume import Resume
from app.models.writer import ResumeSuggestion, WriterRequest
from app.services.storage_service import save_resume, save_writer_suggestion, load_writer_suggestion, list_writer_suggestions
from app.services.writer_service import QUICK_ACTIONS


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def resume_id():
    rid = "writer-test-resume"
    save_resume(rid, Resume(full_name="Test User", email="test@example.com", summary="I am a good worker."))
    return rid


class TestWriterModel:
    def test_valid_suggestion(self):
        s = ResumeSuggestion(id="s1", resume_id="r1", section="summary", original_text="old", suggested_text="new")
        assert s.status == "pending"
        assert 0.0 <= s.confidence <= 1.0
        assert s.source == "ai_writer"

    def test_invalid_status(self):
        with pytest.raises(Exception):
            ResumeSuggestion(id="s1", resume_id="r1", section="summary", status="invalid")

    def test_confidence_bounds(self):
        with pytest.raises(Exception):
            ResumeSuggestion(id="s1", resume_id="r1", section="summary", confidence=1.5)


class TestQuickActions:
    def test_actions_defined(self):
        assert "strengthen" in QUICK_ACTIONS
        assert "summary" in QUICK_ACTIONS
        assert "grammar" in QUICK_ACTIONS
        assert len(QUICK_ACTIONS) >= 5


class TestWriterStorage:
    def test_save_and_load(self, resume_id):
        s = ResumeSuggestion(id="ws1", resume_id=resume_id, section="summary", original_text="a", suggested_text="b")
        save_writer_suggestion(s)
        loaded = load_writer_suggestion(resume_id, "ws1")
        assert loaded is not None
        assert loaded.section == "summary"

    def test_list_suggestions(self, resume_id):
        save_writer_suggestion(ResumeSuggestion(id="l1", resume_id=resume_id, section="a", original_text="x", suggested_text="y"))
        all_s = list_writer_suggestions(resume_id)
        assert len(all_s) >= 1

    def test_list_filter_by_status(self, resume_id):
        save_writer_suggestion(ResumeSuggestion(id="st1", resume_id=resume_id, section="a", original_text="x", suggested_text="y", status="pending"))
        pending = list_writer_suggestions(resume_id, status="pending")
        assert all(s.status == "pending" for s in pending)


@pytest.mark.asyncio
async def test_endpoint_quick_actions(client):
    async with client as ac:
        resp = await ac.get("/api/v1/resume/any/writer/quick-actions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) >= 5


@pytest.mark.asyncio
async def test_endpoint_suggest_resume_not_found(client):
    async with client as ac:
        resp = await ac.post(
            "/api/v1/resume/nonexistent/writer/suggest",
            json={"prompt": "Improve the summary"},
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_endpoint_accept_not_found(client):
    async with client as ac:
        resp = await ac.post("/api/v1/resume/r1/writer/suggestions/bad-id/accept")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_endpoint_reject_not_found(client):
    async with client as ac:
        resp = await ac.post("/api/v1/resume/r1/writer/suggestions/bad-id/reject")
    assert resp.status_code == 404


class TestAcceptSuggestion:
    @pytest.mark.asyncio
    async def test_accept_updates_resume(self, resume_id):
        s = ResumeSuggestion(id="accept1", resume_id=resume_id, section="summary", original_text="I am a good worker.", suggested_text="Highly accomplished professional.")
        save_writer_suggestion(s)

        from app.services.writer_service import accept_suggestion
        resume = await accept_suggestion(resume_id, "accept1")
        assert "Highly accomplished" in resume.summary

    @pytest.mark.asyncio
    async def test_accept_marks_as_accepted(self, resume_id):
        s = ResumeSuggestion(id="accept2", resume_id=resume_id, section="summary", original_text="a", suggested_text="b")
        save_writer_suggestion(s)

        from app.services.writer_service import accept_suggestion
        await accept_suggestion(resume_id, "accept2")
        loaded = load_writer_suggestion(resume_id, "accept2")
        assert loaded.status == "accepted"


class TestRejectSuggestion:
    @pytest.mark.asyncio
    async def test_reject_marks_as_rejected(self, resume_id):
        s = ResumeSuggestion(id="rej1", resume_id=resume_id, section="summary", original_text="a", suggested_text="b")
        save_writer_suggestion(s)

        from app.services.writer_service import reject_suggestion
        await reject_suggestion(resume_id, "rej1")
        loaded = load_writer_suggestion(resume_id, "rej1")
        assert loaded.status == "rejected"
