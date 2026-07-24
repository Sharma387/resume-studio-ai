import uuid

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.resume import Resume
from app.services.storage_service import save_resume


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_get_resume_not_found(client):
    async with client as ac:
        response = await ac.get("/api/v1/resume/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_resume_success(client):
    resume_id = uuid.uuid4().hex
    resume = Resume(user_id="test", full_name="Test User", email="test@example.com")
    save_resume(resume_id, resume)

    async with client as ac:
        response = await ac.get(f"/api/v1/resume/{resume_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["full_name"] == "Test User"


@pytest.mark.asyncio
async def test_update_resume(client):
    resume_id = uuid.uuid4().hex
    resume = Resume(user_id="test", full_name="Original", email="orig@example.com")
    save_resume(resume_id, resume)

    updated = Resume(user_id="test", full_name="Updated", email="updated@example.com")

    async with client as ac:
        response = await ac.put(
            f"/api/v1/resume/{resume_id}",
            json=updated.model_dump(),
        )
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["full_name"] == "Updated"
