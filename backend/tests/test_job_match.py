import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.resume import Resume
from app.services.storage_service import save_resume


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def saved_resume_id():
    resume_id = "test-resume-for-match"
    resume = Resume(user_id="test", full_name="Jane Smith", email="jane@example.com")
    save_resume(resume_id, resume)
    return resume_id


@pytest.mark.asyncio
async def test_create_job_match_resume_not_found(client):
    async with client as ac:
        response = await ac.post(
            "/api/v1/job-match",
            json={"resume_id": "nonexistent", "description": "We need a Python developer."},
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_job_match_success(client, saved_resume_id):
    async with client as ac:
        response = await ac.post(
            "/api/v1/job-match",
            json={
                "resume_id": saved_resume_id,
                "job_title": "Senior Engineer",
                "description": "We are looking for a senior software engineer proficient in Python, React, AWS, and Docker.",
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    result = data["data"]
    assert result["resume_id"] == saved_resume_id
    assert result["job_title"] == "Senior Engineer"
    assert 0 <= result["overall_score"] <= 100
    assert len(result["skill_matches"]) > 0
    assert len(result["recommendations"]) > 0
    assert result["summary"]


@pytest.mark.asyncio
async def test_get_job_match_not_found(client):
    async with client as ac:
        response = await ac.get("/api/v1/job-match/nonexistent-match")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_job_match_success(client, saved_resume_id):
    async with client as ac:
        create_resp = await ac.post(
            "/api/v1/job-match",
            json={
                "resume_id": saved_resume_id,
                "description": "A valid job description with enough text.",
            },
        )
    match_id = create_resp.json()["data"]["id"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as get_client:
        get_resp = await get_client.get(f"/api/v1/job-match/{match_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["data"]["id"] == match_id
    assert 0 <= data["data"]["overall_score"] <= 100


@pytest.mark.asyncio
async def test_create_job_match_validates_short_description(client, saved_resume_id):
    async with client as ac:
        response = await ac.post(
            "/api/v1/job-match",
            json={"resume_id": saved_resume_id, "description": "Short"},
        )
    assert response.status_code == 422
