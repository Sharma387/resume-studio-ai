import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.resume import Resume
from app.models.match import Recommendation
from app.services.storage_service import save_resume, save_version, list_versions
from app.models.version import ResumeVersion


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def resume_id():
    rid = "test-suggestion-resume"
    resume = Resume(user_id="test", full_name="Test User", email="test@example.com", summary="Original summary.")
    save_resume(rid, resume)
    return rid


@pytest.mark.asyncio
async def test_preview_suggestion_resume_not_found(client):
    async with client as ac:
        response = await ac.post(
            "/api/v1/resume/nonexistent/preview-suggestion",
            json={"section": "Summary", "priority": "medium", "message": "Improve the summary section."},
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_preview_suggestion_returns_both_versions(client, resume_id):
    rec = {"section": "Summary", "priority": "high", "message": "Update the summary to highlight leadership experience."}
    async with client as ac:
        response = await ac.post(
            f"/api/v1/resume/{resume_id}/preview-suggestion",
            json=rec,
        )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "original" in data["data"]
    assert "modified" in data["data"]


@pytest.mark.asyncio
async def test_apply_suggestion_creates_version(client, resume_id):
    rec = {"section": "Summary", "priority": "high", "message": "Add achievements to summary."}
    async with client as ac:
        response = await ac.post(
            f"/api/v1/resume/{resume_id}/apply-suggestion",
            json=rec,
        )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "version" in data["data"]
    assert data["data"]["version"]["resume_id"] == resume_id
    versions = list_versions(resume_id)
    assert len(versions) >= 1


@pytest.mark.asyncio
async def test_create_and_list_versions(client, resume_id):
    v = ResumeVersion(id="v1", resume_id=resume_id, user_id="test", label="Snapshot", resume=Resume(user_id="test", full_name="Test", email="t@t.com"))
    save_version(v)

    async with client as ac:
        response = await ac.get(f"/api/v1/resume/{resume_id}/versions")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) >= 1


@pytest.mark.asyncio
async def test_restore_version(client, resume_id):
    v = ResumeVersion(user_id="test", 
        id="restore-v1",
        resume_id=resume_id,
        label="Restored version",
        resume=Resume(user_id="test", full_name="Restored Name", email="restored@example.com", summary="Restored summary."),
    )
    save_version(v)

    async with client as ac:
        response = await ac.post(f"/api/v1/resume/{resume_id}/versions/restore-v1/restore")
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["full_name"] == "Restored Name"
