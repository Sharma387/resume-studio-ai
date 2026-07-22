import json

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.resume import Resume


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def _make_mock_resume_json() -> str:
    r = Resume(
        full_name="John Doe",
        email="john@example.com",
        phone="+1 555-0000",
        location="NYC",
        linkedin="https://linkedin.com/in/johndoe",
        github="https://github.com/johndoe",
        website="https://johndoe.dev",
        summary="A summary.",
        education=[{"institution": "MIT", "degree": "BS", "field": "CS", "achievements": []}],
        experience=[{"company": "Acme", "title": "Dev", "current": False, "description": []}],
        projects=[{"name": "Project X", "technologies": []}],
        skills=[{"category": "Lang", "skills": ["Python"]}],
        certifications=[{"name": "Cert"}],
    )
    return r.model_dump_json()


@pytest.fixture(autouse=True)
def mock_omniroute(monkeypatch):
    """Replace OmniRouteService so parse endpoint works without real API."""
    monkeypatch.setattr("app.services.parser_service.settings.omniroute_api_key", "test-key")
    json_response = _make_mock_resume_json()

    class FakeOmniRoute:
        def __init__(self):
            self.max_retries = 0

        async def send_prompt(self, system: str, user: str) -> str:
            return json_response

    import app.services.parser_service as mod
    monkeypatch.setattr(mod, "OmniRouteService", lambda *a, **kw: FakeOmniRoute())


@pytest.mark.asyncio
async def test_parse_returns_resume(client):
    async with client as ac:
        response = await ac.post("/api/v1/parse", json={"text": "dummy text"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    resume = data["data"]
    assert resume["full_name"] == "John Doe"
    assert resume["email"] == "john@example.com"


@pytest.mark.asyncio
async def test_parse_includes_sections(client):
    async with client as ac:
        response = await ac.post("/api/v1/parse", json={"text": "dummy"})
    data = response.json()["data"]
    assert len(data["education"]) > 0
    assert len(data["experience"]) > 0
    assert len(data["projects"]) > 0
    assert len(data["skills"]) > 0
    assert len(data["certifications"]) > 0


@pytest.mark.asyncio
async def test_parse_serializes_urls(client):
    async with client as ac:
        response = await ac.post("/api/v1/parse", json={"text": "dummy"})
    data = response.json()["data"]
    assert data["linkedin"].startswith("http")


@pytest.mark.asyncio
async def test_parse_empty_text(client):
    async with client as ac:
        response = await ac.post("/api/v1/parse", json={"text": ""})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_parse_with_filename_saves_resume(client):
    async with client as ac:
        response = await ac.post(
            "/api/v1/parse",
            json={"text": "dummy", "filename": "test-abc.pdf"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-abc"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as get_client:
        get_resp = await get_client.get(f"/api/v1/resume/{data['id']}")
    assert get_resp.status_code == 200
