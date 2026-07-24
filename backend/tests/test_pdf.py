import uuid

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.resume import Resume
from app.services.storage_service import save_resume
from app.services.pdf_service import PDF_DIR


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_generate_pdf_not_found(client):
    async with client as ac:
        response = await ac.post("/api/v1/resume/nonexistent/pdf")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_and_download_pdf(client):
    resume_id = uuid.uuid4().hex
    resume = Resume(user_id="test", full_name="Test User", email="test@example.com")
    save_resume(resume_id, resume)

    async with client as ac:
        gen_resp = await ac.post(f"/api/v1/resume/{resume_id}/pdf")
    assert gen_resp.status_code == 200
    data = gen_resp.json()
    assert data["success"] is True
    assert "download" in data["downloadUrl"]

    pdf_path = PDF_DIR / f"{resume_id}.pdf"
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as dl_client:
        dl_resp = await dl_client.get(data["downloadUrl"])
    assert dl_resp.status_code == 200
    assert dl_resp.headers["content-type"] == "application/pdf"


@pytest.mark.asyncio
async def test_download_without_generating(client):
    async with client as ac:
        response = await ac.get("/api/v1/resume/ghost/pdf/download")
    assert response.status_code == 404
