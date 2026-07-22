import uuid
from pathlib import Path

import fitz
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.upload_service import UPLOAD_DIR


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def _write_test_pdf(pages: list[str]) -> str:
    doc = fitz.open()
    for content in pages:
        page = doc.new_page()
        page.insert_text((50, 50), content, fontsize=11)
    filename = f"{uuid.uuid4().hex}.pdf"
    doc.save(str(UPLOAD_DIR / filename))
    doc.close()
    return filename


def _write_empty_pdf() -> str:
    doc = fitz.open()
    page = doc.new_page()
    filename = f"{uuid.uuid4().hex}.pdf"
    doc.save(str(UPLOAD_DIR / filename))
    doc.close()
    return filename


def _write_corrupt_pdf() -> str:
    filename = f"{uuid.uuid4().hex}.pdf"
    (UPLOAD_DIR / filename).write_bytes(b"not a pdf at all")
    return filename


@pytest.mark.asyncio
async def test_extract_success(client):
    filename = _write_test_pdf(["Hello World"])
    async with client as ac:
        response = await ac.post("/api/v1/extract", json={"filename": filename})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["pages"] == 1
    assert data["data"]["characters"] > 0
    assert "Hello World" in data["data"]["text"]


@pytest.mark.asyncio
async def test_extract_empty_pdf(client):
    filename = _write_empty_pdf()
    async with client as ac:
        response = await ac.post("/api/v1/extract", json={"filename": filename})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["pages"] == 1
    assert data["data"]["characters"] == 0
    assert data["data"]["text"] == ""


@pytest.mark.asyncio
async def test_extract_corrupt_pdf(client):
    filename = _write_corrupt_pdf()
    async with client as ac:
        response = await ac.post("/api/v1/extract", json={"filename": filename})
    assert response.status_code == 400
    assert "corrupt" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_extract_file_not_found(client):
    async with client as ac:
        response = await ac.post("/api/v1/extract", json={"filename": "nonexistent.pdf"})
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_extract_multi_page(client):
    filename = _write_test_pdf(["Page 1 content", "Page 2 content", "Page 3 content"])
    async with client as ac:
        response = await ac.post("/api/v1/extract", json={"filename": filename})
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["pages"] == 3
    assert "Page 1 content" in data["data"]["text"]
    assert "Page 2 content" in data["data"]["text"]
    assert "Page 3 content" in data["data"]["text"]
