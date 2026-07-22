import pytest
from httpx import AsyncClient, ASGITransport
from pydantic import ValidationError

from app.main import app
from app.models.cover_letter import CoverLetter, CoverLetterRequest, CoverLetterTone
from app.models.resume import Resume
from app.services.storage_service import save_resume, save_cover_letter, load_cover_letter, list_cover_letters


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def resume_id():
    rid = "cl-test-resume"
    save_resume(rid, Resume(full_name="Jane Author", email="jane@example.com"))
    return rid


class TestCoverLetterModel:
    def test_valid_request(self):
        r = CoverLetterRequest(job_description="We need a senior engineer with Python experience for a full-time position.")
        assert r.tone == CoverLetterTone.PROFESSIONAL

    def test_short_jd_rejected(self):
        with pytest.raises(ValidationError):
            CoverLetterRequest(job_description="Too short")

    def test_invalid_tone(self):
        with pytest.raises(ValidationError):
            CoverLetterRequest(job_description="A valid job description here for testing.", tone="invalid")

    def test_cover_letter_defaults(self):
        c = CoverLetter(id="cl1", resume_id="r1", content="Hello")
        assert c.tone == CoverLetterTone.PROFESSIONAL
        assert c.application_id is None

    def test_cover_letter_with_application_id(self):
        c = CoverLetter(id="cl2", resume_id="r1", content="Hello", application_id="app-123")
        assert c.application_id == "app-123"


class TestCoverLetterStorage:
    def test_save_and_load(self, resume_id):
        c = CoverLetter(id="cls1", resume_id=resume_id, content="Dear Hiring Manager...")
        save_cover_letter(c)
        loaded = load_cover_letter(resume_id, "cls1")
        assert loaded is not None
        assert "Dear Hiring Manager" in loaded.content

    def test_list(self, resume_id):
        save_cover_letter(CoverLetter(id="cll1", resume_id=resume_id, content="A"))
        letters = list_cover_letters(resume_id)
        assert len(letters) >= 1

    def test_delete(self, resume_id):
        save_cover_letter(CoverLetter(id="cld1", resume_id=resume_id, content="B"))
        from app.services.storage_service import delete_cover_letter
        assert delete_cover_letter(resume_id, "cld1") is True
        assert delete_cover_letter(resume_id, "nonexistent") is False


@pytest.mark.asyncio
async def test_endpoint_generate_resume_not_found(client):
    async with client as ac:
        resp = await ac.post("/api/v1/resume/nonexistent/cover-letter", json={"job_description": "A valid job description for testing purposes with enough text."})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_endpoint_list(client, resume_id):
    save_cover_letter(CoverLetter(id="clapi1", resume_id=resume_id, content="Test"))
    async with client as ac:
        resp = await ac.get(f"/api/v1/resume/{resume_id}/cover-letters")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) >= 1


@pytest.mark.asyncio
async def test_endpoint_get_not_found(client):
    async with client as ac:
        resp = await ac.get("/api/v1/resume/r1/cover-letter/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_endpoint_get_success(client, resume_id):
    save_cover_letter(CoverLetter(id="clget1", resume_id=resume_id, content="Get me"))
    async with client as ac:
        resp = await ac.get(f"/api/v1/resume/{resume_id}/cover-letter/clget1")
    assert resp.status_code == 200
    assert resp.json()["data"]["content"] == "Get me"


@pytest.mark.asyncio
async def test_endpoint_update(client, resume_id):
    save_cover_letter(CoverLetter(id="clupd1", resume_id=resume_id, content="Old"))
    async with client as ac:
        resp = await ac.put(
            f"/api/v1/resume/{resume_id}/cover-letter/clupd1",
            json={"id": "clupd1", "resume_id": resume_id, "content": "New content here for testing."},
        )
    assert resp.status_code == 200
    assert resp.json()["data"]["content"] == "New content here for testing."


@pytest.mark.asyncio
async def test_endpoint_delete(client, resume_id):
    save_cover_letter(CoverLetter(id="cldel1", resume_id=resume_id, content="Delete me"))
    async with client as ac:
        resp = await ac.delete(f"/api/v1/resume/{resume_id}/cover-letter/cldel1")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_endpoint_pdf_not_found(client):
    async with client as ac:
        resp = await ac.post("/api/v1/resume/r1/cover-letter/nonexistent/pdf")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_endpoint_regenerate_not_found(client):
    async with client as ac:
        resp = await ac.post("/api/v1/resume/r1/cover-letter/nonexistent/regenerate")
    assert resp.status_code == 404
