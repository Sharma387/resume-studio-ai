"""Canonical preview/export API contract — production hardening.

Verifies the documented canonical API surface exactly:

    GET  /resume/{id}/preview?layout_id=<layout>&theme=<theme>
    POST /resume/{id}/export  {layout_id, theme_id, format}

Every parameter boundary (missing / retired / unknown / malformed) must return
a controlled 4xx, and no request may fall back to a legacy template renderer.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app
from app.models.resume import Resume
from app.services.storage_service import save_resume


@pytest.fixture
def client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _save_resume(user_id="test") -> str:
    resume_id = uuid.uuid4().hex
    resume = Resume(
        user_id=user_id,
        full_name=f"Contract User {resume_id[:6]}",
        email="contract@test.com",
        summary="Contract test resume.",
        experience=[{"company": "Acme", "title": "Engineer", "start_date": "2020"}],
    )
    save_resume(resume_id, resume)
    return resume_id


# ── Preview contract ──────────────────────────────────────────────────────────


class TestPreviewContract:
    async def test_layout_id_only_200(self, client):
        rid = _save_resume()
        response = await client.get(f"/api/v1/resume/{rid}/preview?layout_id=sidebar")
        assert response.status_code == 200
        assert response.json()["data"]["layout_id"] == "sidebar"

    async def test_layout_id_and_theme_200(self, client):
        rid = _save_resume()
        response = await client.get(f"/api/v1/resume/{rid}/preview?layout_id=sidebar&theme=gold")
        assert response.status_code == 200
        assert response.json()["data"]["mode"] == "layout"

    async def test_missing_layout_id_400(self, client):
        rid = _save_resume()
        response = await client.get(f"/api/v1/resume/{rid}/preview")
        assert response.status_code == 400
        assert "layout_id" in response.json()["detail"].lower()

    async def test_template_id_400(self, client):
        rid = _save_resume()
        response = await client.get(f"/api/v1/resume/{rid}/preview?template_id=classic")
        assert response.status_code == 400
        assert "retired" in response.json()["detail"]

    async def test_layout_id_and_template_id_400(self, client):
        rid = _save_resume()
        response = await client.get(f"/api/v1/resume/{rid}/preview?layout_id=sidebar&template_id=classic")
        assert response.status_code == 400

    async def test_unknown_layout_404(self, client):
        rid = _save_resume()
        response = await client.get(f"/api/v1/resume/{rid}/preview?layout_id=definitely-not-real")
        assert response.status_code == 404
        assert "Layout" in response.json()["detail"]

    async def test_unknown_theme_404(self, client):
        rid = _save_resume()
        response = await client.get(f"/api/v1/resume/{rid}/preview?layout_id=sidebar&theme=no-theme")
        assert response.status_code == 404
        assert "Theme" in response.json()["detail"]

    async def test_empty_parameters_controlled(self, client):
        rid = _save_resume()
        # An empty layout_id is an unknown layout → controlled 404.
        empty_layout = await client.get(f"/api/v1/resume/{rid}/preview?layout_id=&theme=blue")
        assert empty_layout.status_code == 404
        # An empty theme is optional → falls back to the engine default theme.
        empty_theme = await client.get(f"/api/v1/resume/{rid}/preview?layout_id=sidebar&theme=")
        assert empty_theme.status_code == 200

    async def test_unknown_resume_preview_404(self, client):
        response = await client.get("/api/v1/resume/nonexistent/preview?layout_id=sidebar")
        assert response.status_code == 404
        assert "Resume not found" in response.json()["detail"]


# ── Export contract ───────────────────────────────────────────────────────────


_DEFAULT_EXPORT_BODY = {"layout_id": "sidebar", "theme_id": "blue", "format": "pdf"}


class TestExportContract:
    async def test_all_supported_formats(self, client):
        rid = _save_resume()
        for fmt in ("pdf", "docx", "html"):
            response = await client.post(
                f"/api/v1/resume/{rid}/export", json={**_DEFAULT_EXPORT_BODY, "format": fmt}
            )
            assert response.status_code == 200, fmt
            assert response.content, fmt

    async def test_unknown_layout_404(self, client):
        rid = _save_resume()
        response = await client.post(
            f"/api/v1/resume/{rid}/export", json={**_DEFAULT_EXPORT_BODY, "layout_id": "nope"}
        )
        assert response.status_code == 404
        assert "Layout" in response.json()["detail"]

    async def test_unknown_theme_404(self, client):
        rid = _save_resume()
        response = await client.post(
            f"/api/v1/resume/{rid}/export", json={**_DEFAULT_EXPORT_BODY, "theme_id": "nope"}
        )
        assert response.status_code == 404
        assert "Theme" in response.json()["detail"]

    async def test_invalid_format_422(self, client):
        rid = _save_resume()
        response = await client.post(
            f"/api/v1/resume/{rid}/export", json={**_DEFAULT_EXPORT_BODY, "format": "png"}
        )
        assert response.status_code == 422

    async def test_missing_required_fields_422(self, client):
        rid = _save_resume()
        for missing in ("layout_id", "theme_id", "format"):
            body = {key: value for key, value in _DEFAULT_EXPORT_BODY.items() if key != missing}
            response = await client.post(f"/api/v1/resume/{rid}/export", json=body)
            assert response.status_code == 422, missing

    async def test_nonexistent_resume_404(self, client):
        response = await client.post(
            "/api/v1/resume/does-not-exist/export", json=_DEFAULT_EXPORT_BODY
        )
        assert response.status_code == 404
        assert "Resume not found" in response.json()["detail"]

    async def test_another_users_resume_404(self, client):
        rid = _save_resume(user_id="someone-else")
        response = await client.post(f"/api/v1/resume/{rid}/export", json=_DEFAULT_EXPORT_BODY)
        assert response.status_code == 404
        assert "Resume not found" in response.json()["detail"]

    async def test_unauthenticated_request_401(self, client):
        rid = _save_resume()
        was_debug = settings.debug
        settings.debug = False
        try:
            response = await client.post(f"/api/v1/resume/{rid}/export", json=_DEFAULT_EXPORT_BODY)
        finally:
            settings.debug = was_debug
        assert response.status_code == 401

    async def test_template_id_field_never_accepted(self, client):
        rid = _save_resume()
        response = await client.post(
            f"/api/v1/resume/{rid}/export",
            json={"layout_id": "sidebar", "theme_id": "blue", "format": "pdf", "template_id": "x"},
        )
        # The canonical export model rejects unknown fields (extra="forbid") —
        # a legacy payload cannot be accepted, translated, or fall back.
        assert response.status_code == 422
        assert response.json()["detail"]

    async def test_preview_banner_never_falls_back_to_legacy(self, client):
        rid = _save_resume()
        # A retired looking preview already returns 400 (template_id), and no
        # legacy preview URL is ever produced for a valid request.
        response = await client.get(f"/api/v1/resume/{rid}/preview?layout_id=sidebar")
        assert response.status_code == 200
        assert "templates" not in response.json()["data"]["preview_url"]
        assert "template" not in response.text.lower() or "template_id" not in response.text
