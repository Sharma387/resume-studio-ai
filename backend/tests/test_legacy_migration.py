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


def _make_resume(user_id="test") -> Resume:
    return Resume(user_id=user_id, full_name="Migrate User", email="mig@test.com")


def _save_resume(user_id="test") -> str:
    resume_id = uuid.uuid4().hex
    save_resume(resume_id, _make_resume(user_id))
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
    async def test_missing_both_ids_rejected(self, client):
        rid = _save_resume()
        response = await client.get(f"/api/v1/resume/{rid}/preview")
        assert response.status_code == 400
        assert "layout_id or template_id" in response.json()["detail"]

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

    async def test_unknown_template_404(self, client):
        rid = _save_resume()
        response = await client.get(f"/api/v1/resume/{rid}/preview?template_id=does-not-exist")
        assert response.status_code == 404

    async def test_unknown_theme_404(self, client):
        rid = _save_resume()
        response = await client.get(f"/api/v1/resume/{rid}/preview?layout_id=sidebar&theme=nope")
        assert response.status_code == 404

    async def test_unauthorized_resume_404(self, client):
        rid = _save_resume(user_id="other")
        response = await client.get(f"/api/v1/resume/{rid}/preview?layout_id=sidebar")
        assert response.status_code == 404


class TestThemeRegistryAPI:
    async def test_themes_endpoint_returns_registered_themes(self, client):
        from app.rendering.layout_preview import default_theme_registry

        response = await client.get("/api/v1/resume/themes")
        assert response.status_code == 200
        data = response.json()["data"]
        assert isinstance(data, list)
        registry_ids = {t.theme_id for t in default_theme_registry().palettes()}
        assert registry_ids
        assert {item["theme_id"] for item in data} == registry_ids
        for item in data:
            assert item["name"]
            assert "theme_id" in item


class TestPdfDownloadOwnership:
    async def test_own_resume_pdf_download_allowed(self, client):
        from app.services.pdf_service import generate_pdf
        from app.services.pdf_templates.engine import PDF_DIR

        rid = _save_resume()
        resume = _make_resume()
        generate_pdf(rid, resume, "executive")
        assert (PDF_DIR / f"{rid}.pdf").exists()

        response = await client.get(f"/api/v1/resume/{rid}/pdf/download")
        assert response.status_code == 200
        assert "application/pdf" in response.headers.get("content-type", "")

    async def test_another_users_resume_pdf_download_404(self, client):
        from app.services.pdf_service import generate_pdf
        from app.services.pdf_templates.engine import PDF_DIR

        rid = _save_resume(user_id="other")
        resume = _make_resume(user_id="other")
        # Simulate the owner having generated a PDF earlier.
        generate_pdf(rid, resume, "executive")
        assert (PDF_DIR / f"{rid}.pdf").exists()

        response = await client.get(f"/api/v1/resume/{rid}/pdf/download")
        assert response.status_code == 404


class TestCleanup:
    def test_thumbnail_service_module_removed(self):
        import importlib.util

        assert importlib.util.find_spec("app.services.thumbnail_service") is None

    def test_designer_has_no_dead_rendering_init(self):
        import app.api.v1.designer as designer

        assert not hasattr(designer, "rendering")


class TestVariantCompatibility:
    """Prove stored legacy ``template_id`` variants remain actionable through the
    canonical pipeline, so retiring TemplateRegistry does not strand variant data."""

    def test_every_legacy_template_resolves_into_a_registered_layout(self):
        from app.rendering.layout_preview import default_layout_registry

        registry = default_layout_registry()
        for template_id in LEGACY_TEMPLATE_IDS:
            layout_id = resolve_legacy_template(template_id)
            assert layout_id in LAYOUTS
            assert registry.contains(layout_id)

    async def test_stored_variant_regenerates_through_canonical_export(self, client):
        from app.rendering.layout_preview import default_layout_registry
        from app.services.resume_variants.service import create as create_variant
        from app.services.storage_service import load_resume

        rid = _save_resume()
        resume = load_resume(rid, user_id="test")
        assert resume is not None

        variant = create_variant(resume, "test", "Legacy Template Variant", template_id="modern-ats")
        assert variant["template_id"] == "modern-ats"
        layout_id = resolve_legacy_template(variant["template_id"])
        assert layout_id == "classic"
        assert default_layout_registry().contains(layout_id)

        response = await client.post(
            f"/api/v1/resume/{rid}/export",
            json={"layout_id": layout_id, "theme_id": "blue", "format": "pdf"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"

    def test_legacy_variant_default_template_id_resolves(self):
        # Variant creation defaults to "executive-elite" (matches the DB model default).
        assert resolve_legacy_template("executive-elite") == "sidebar"
