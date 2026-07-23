"""Full data flow integration test.

Validates:
  Upload → Extract → Parse (via mocked AI) → Store → Dashboard
No mock data appears in the pipeline.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.resume import Resume
from app.services.repositories.domain_repos import ResumeRepository


def _real_pdf_bytes(text: str = "Hello World") -> bytes:
    import fitz, io
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text, fontsize=11)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def _valid_resume_json() -> str:
    r = Resume(full_name="John Smith", email="john.smith@example.com", summary="Senior Engineer with Python")
    return r.model_dump_json()


def _api(method: str, path: str, **kwargs):
    """Helper to make a fresh request to the app."""
    import asyncio

    async def _call():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            return await c.request(method, path, **kwargs)

    return asyncio.get_event_loop().run_until_complete(_call())


@pytest.fixture
def mock_ai_parser(monkeypatch):
    """Mock the AI call to return a valid resume without hitting OmniRoute."""
    json_response = _valid_resume_json()

    async def fake_call_with_retry(build_prompt, parse_response, omniroute=None, service_name="AI"):
        return parse_response(json_response)

    monkeypatch.setattr("app.services.parser_service.call_with_retry", fake_call_with_retry)


@pytest.mark.asyncio
async def test_full_data_flow_no_mock_data(mock_ai_parser):
    """Upload → Extract → Parse → Store → Dashboard — no mock data."""

    pdf_bytes = _real_pdf_bytes("John Smith john.smith@example.com Senior Engineer with Python")

    # 1. Upload
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        upload_resp = await c.post("/api/v1/upload", files={"file": ("resume.pdf", pdf_bytes, "application/pdf")})
    assert upload_resp.status_code == 200
    filename = upload_resp.json()["filename"]

    # 2. Extract
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        ext_resp = await c.post("/api/v1/extract", json={"filename": filename})
    assert ext_resp.status_code == 200
    extracted_text = ext_resp.json()["data"]["text"]

    # 3. Parse
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        parse_resp = await c.post("/api/v1/parse", json={"text": extracted_text, "filename": filename})
    assert parse_resp.status_code == 200
    parse_data = parse_resp.json()
    resume_data = parse_data["data"]
    resume_id = parse_data["id"]

    # 4. Verify NO mock data
    assert resume_data["full_name"] == "John Smith", f"Expected John Smith, got {resume_data['full_name']}"
    assert resume_data["email"] == "john.smith@example.com"

    # 5. Verify resume persisted
    repo = ResumeRepository()
    stored = repo.get(resume_id)
    assert stored is not None
    assert stored.full_name == "John Smith"

    # 6. Create a match
    from app.services.repositories.domain_repos import MatchRepository
    from app.models.match import MatchResult
    match = MatchResult(id="flow-match-1", resume_id=resume_id, overall_score=85.0, matched_skills=["Python"], missing_skills=[])
    MatchRepository().save("flow-match-1", match)

    # 7. Dashboard
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        dash_resp = await c.get("/api/v1/dashboard")
    assert dash_resp.status_code == 200
    dash_data = dash_resp.json()["data"]

    assert dash_data["resumes"]["total"] >= 1
    assert dash_data["ats"]["total_matches"] >= 1
    assert dash_data["ats"]["average_score"] > 0


@pytest.mark.asyncio
async def test_parse_without_ai_raises_error(monkeypatch):
    """Without AI and without mock flag, parse should not silently return mock data."""
    from app.core.config import settings
    monkeypatch.setattr(settings, "allow_mock_ai_data", False)
    monkeypatch.setattr(settings, "omniroute_api_url", "http://nonexistent.local/ai")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post("/api/v1/parse", json={"text": "Test resume", "filename": "test.pdf"})
    assert resp.status_code != 200, "Parse should fail when AI is unavailable and mock is disabled"
