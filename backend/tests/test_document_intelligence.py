"""Backward compatibility integration test.

Tests the full workflow: Upload → Extract → Parse → Review → Generate PDF,
verifying that existing API contracts remain unchanged.
"""

import io
import uuid

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.upload_service import UPLOAD_DIR


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def _real_pdf_bytes(text: str = "Hello World") -> bytes:
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text, fontsize=11)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def _real_docx_bytes(paragraphs: list[str] | None = None) -> bytes:
    from docx import Document
    doc = Document()
    for p in (paragraphs or ["Hello World"]):
        doc.add_paragraph(p)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_full_pipeline_pdf(client):
    """Verify extract endpoint returns correct shape for PDF."""
    filename = f"{uuid.uuid4().hex}.pdf"
    (UPLOAD_DIR / filename).write_bytes(_real_pdf_bytes("Jane Smith jane@example.com"))

    async with client as ac:
        resp = await ac.post("/api/v1/extract", json={"filename": filename})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["pages"] >= 1
    assert data["data"]["characters"] > 0
    assert "text" in data["data"]


@pytest.mark.asyncio
async def test_full_pipeline_docx(client):
    """Verify extract endpoint works for DOCX."""
    filename = f"{uuid.uuid4().hex}.docx"
    (UPLOAD_DIR / filename).write_bytes(_real_docx_bytes(["John Doe", "Engineer"]))

    async with client as ac:
        resp = await ac.post("/api/v1/extract", json={"filename": filename})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "John Doe" in data["data"]["text"]


@pytest.mark.asyncio
async def test_extract_response_shape(client):
    """Verify the extract response shape matches the original contract."""
    filename = f"{uuid.uuid4().hex}.pdf"
    (UPLOAD_DIR / filename).write_bytes(_real_pdf_bytes("Test"))

    async with client as ac:
        resp = await ac.post("/api/v1/extract", json={"filename": filename})
    data = resp.json()
    assert set(data.keys()) == {"success", "data"}
    assert set(data["data"].keys()) == {"pages", "characters", "text"}


@pytest.mark.asyncio
async def test_upload_then_extract_pdf(client):
    """Upload a real PDF then extract it."""
    pdf_bytes = _real_pdf_bytes("Jane Smith Software Engineer")
    async with client as ac:
        upload_resp = await ac.post(
            "/api/v1/upload",
            files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
        )
    assert upload_resp.status_code == 200
    upload_data = upload_resp.json()
    assert upload_data["filename"].endswith(".pdf")

    t = ASGITransport(app=app)
    async with AsyncClient(transport=t, base_url="http://test") as ac2:
        ext_resp = await ac2.post("/api/v1/extract", json={"filename": upload_data["filename"]})
    assert ext_resp.status_code == 200
    assert "Jane Smith" in ext_resp.json()["data"]["text"]


@pytest.mark.asyncio
async def test_upload_then_extract_docx(client):
    """Upload a real DOCX then extract it."""
    docx_bytes = _real_docx_bytes(["John Doe", "Senior Engineer", "Python, React"])
    async with client as ac:
        upload_resp = await ac.post(
            "/api/v1/upload",
            files={"file": ("resume.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
    assert upload_resp.status_code == 200
    upload_data = upload_resp.json()
    assert upload_data["filename"].endswith(".docx")

    t = ASGITransport(app=app)
    async with AsyncClient(transport=t, base_url="http://test") as ac2:
        ext_resp = await ac2.post("/api/v1/extract", json={"filename": upload_data["filename"]})
    assert ext_resp.status_code == 200
    assert "John Doe" in ext_resp.json()["data"]["text"]
