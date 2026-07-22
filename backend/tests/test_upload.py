import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_upload_pdf_success(client):
    content = b"%PDF-1.4 fake pdf content"
    async with client as ac:
        response = await ac.post(
            "/api/v1/upload",
            files={"file": ("resume.pdf", content, "application/pdf")},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["filename"].endswith(".pdf")
    assert data["original_name"] == "resume.pdf"
    assert data["size"] == len(content)


@pytest.mark.asyncio
async def test_upload_docx_success(client):
    async with client as ac:
        response = await ac.post(
            "/api/v1/upload",
            files={"file": ("resume.docx", b"fake docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["filename"].endswith(".docx")


@pytest.mark.asyncio
async def test_upload_txt_success(client):
    async with client as ac:
        response = await ac.post(
            "/api/v1/upload",
            files={"file": ("resume.txt", b"hello", "text/plain")},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["filename"].endswith(".txt")


@pytest.mark.asyncio
async def test_upload_rejects_doc(client):
    async with client as ac:
        response = await ac.post(
            "/api/v1/upload",
            files={"file": ("resume.doc", b"fake doc", "application/msword")},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_rejects_png(client):
    async with client as ac:
        response = await ac.post(
            "/api/v1/upload",
            files={"file": ("image.png", b"fake png", "image/png")},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_rejects_jpg(client):
    async with client as ac:
        response = await ac.post(
            "/api/v1/upload",
            files={"file": ("image.jpg", b"fake jpg", "image/jpeg")},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_rejects_oversized_file(client):
    content = b"x" * (10 * 1024 * 1024 + 1)
    async with client as ac:
        response = await ac.post(
            "/api/v1/upload",
            files={"file": ("large.pdf", content, "application/pdf")},
        )
    assert response.status_code == 400
    assert "10MB" in response.json()["detail"]
