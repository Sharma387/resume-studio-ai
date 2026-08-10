"""Tests for the template_id -> layout_id migration boundary."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.resume import Resume
from app.rendering.legacy_templates import (
    DEFAULT_LEGACY_THEME,
    LEGACY_TEMPLATE_IDS,
    TEMPLATE_TO_LAYOUT,
    UnknownLegacyTemplateError,
    resolve_legacy_selection,
    resolve_legacy_template,
)
from app.services.storage_service import save_resume

LAYOUTS = {"executive", "modern", "sidebar", "timeline", "classic", "minimal"}


@pytest.fixture
def client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _save_resume(user_id="test") -> str:
    resume_id = uuid.uuid4().hex
    resume = Resume(user_id=user_id, full_name="Migrate User", email="mig@test.com")
    save_resume(resume_id, resume)
    return resume_id


class TestMapping:
    def test_every_legacy_template_maps_deterministically(self):
        assert set(TEMPLATE_TO_LAYOUT.keys()) == set(LEGACY_TEMPLATE_IDS)
        for template_id in LEGACY_TEMPLATE_IDS:
            layout = resolve_legacy_template(template_id)
            assert layout in LAYOUTS
            assert resolve_legacy_template(template_id) == layout  # deterministic

    def test_unknown_template_rejected(self):
        with pytest.raises(UnknownLegacyTemplateError):
            resolve_legacy_template("not-a-template")

    def test_resolve_legacy_selection_returns_default_theme(self):
        layout, theme = resolve_legacy_selection("executive")
        assert layout == "executive"
        assert theme == DEFAULT_LEGACY_THEME

    def test_representative_mappings(self):
        assert resolve_legacy_template("executive") == "executive"
        assert resolve_legacy_template("executive-elite") == "sidebar"
        assert resolve_legacy_template("modern-ats") == "classic"
        assert resolve_legacy_template("minimal-professional") == "minimal"


class TestTemplateLookup:
    async def test_template_endpoint_includes_layout_id(self, client):
        response = await client.get("/api/v1/resume/templates/executive")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["layout_id"] == "executive"

    async def test_unknown_template_returns_404(self, client):
        response = await client.get("/api/v1/resume/templates/nope")
        assert response.status_code == 404

    async def test_layouts_endpoint_lists_registry(self, client):
        response = await client.get("/api/v1/resume/layouts")
        assert response.status_code == 200
        data = response.json()["data"]
        assert isinstance(data, list)
        assert {item["layout_id"] for item in data} == LAYOUTS


class TestPreviewConflict:
    async def test_ambiguous_template_and_layout_rejected(self, client):
        rid = _save_resume()
        response = await client.get(f"/api/v1/resume/{rid}/preview?template_id=executive&layout_id=sidebar")
        assert response.status_code == 400

    async def test_layout_mode_is_canonical(self, client):
        rid = _save_resume()
        response = await client.get(f"/api/v1/resume/{rid}/preview?layout_id=sidebar&theme=blue")
        assert response.status_code == 200
        body = response.json()
        assert body["data"]["mode"] == "layout"

    async def test_legacy_template_mode_still_works(self, client):
        rid = _save_resume()
        response = await client.get(f"/api/v1/resume/{rid}/preview?template_id=executive")
        assert response.status_code == 200
        body = response.json()
        assert "mode" not in body["data"]  # legacy shape

    async def test_unknown_layout_404(self, client):
        rid = _save_resume()
        response = await client.get(f"/api/v1/resume/{rid}/preview?layout_id=nope")
        assert response.status_code == 404

    async def test_unknown_theme_404(self, client):
        rid = _save_resume()
        response = await client.get(f"/api/v1/resume/{rid}/preview?layout_id=sidebar&theme=nope")
        assert response.status_code == 404

    async def test_unauthorized_resume_404(self, client):
        rid = _save_resume(user_id="other")
        response = await client.get(f"/api/v1/resume/{rid}/preview?layout_id=sidebar")
        assert response.status_code == 404
