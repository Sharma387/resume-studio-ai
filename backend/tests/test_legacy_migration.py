"""Tests for the canonical preview boundary and rendering independence.

After the legacy rendering retirement the preview is layout-only:

* ``GET /resume/{id}/preview?layout_id=…&theme=…`` (layout_id required)
* the legacy ``template_id`` preview and template→layout mapping were removed.

These tests also prove stored ``template_id`` variant metadata no longer has a
rendering/resolution dependency and that the canonical pipeline renders every
format without any legacy rendering stack.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.resume import Resume
from app.services.storage_service import save_resume

LAYOUTS = {"executive", "modern", "sidebar", "timeline", "classic", "minimal"}


@pytest.fixture
def client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _make_resume(user_id="dev-user") -> Resume:
    return Resume(user_id=user_id, full_name="Migrate User", email="mig@test.com")


def _save_resume(user_id="dev-user") -> str:
    resume_id = uuid.uuid4().hex
    save_resume(resume_id, _make_resume(user_id))
    return resume_id


class TestLayoutsEndpoint:
    async def test_layouts_endpoint_lists_registry(self, client):
        response = await client.get("/api/v1/resume/layouts")
        assert response.status_code == 200
        data = response.json()["data"]
        assert isinstance(data, list)
        assert {item["layout_id"] for item in data} == LAYOUTS


class TestPreviewCanonicalOnly:
    async def test_missing_layout_id_rejected(self, client):
        rid = _save_resume()
        response = await client.get(f"/api/v1/resume/{rid}/preview")
        assert response.status_code == 400
        assert "layout_id" in response.json()["detail"]

    async def test_retired_template_id_rejected(self, client):
        rid = _save_resume()
        response = await client.get(f"/api/v1/resume/{rid}/preview?template_id=executive")
        assert response.status_code == 400
        assert "retired" in response.json()["detail"]

    async def test_template_id_with_layout_id_rejected(self, client):
        rid = _save_resume()
        response = await client.get(f"/api/v1/resume/{rid}/preview?template_id=executive&layout_id=sidebar")
        assert response.status_code == 400

    async def test_layout_mode_is_canonical(self, client):
        rid = _save_resume()
        response = await client.get(f"/api/v1/resume/{rid}/preview?layout_id=sidebar&theme=blue")
        assert response.status_code == 200
        body = response.json()
        assert body["data"]["mode"] == "layout"

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


class TestRetiredSurfacesGone:
    async def test_legacy_template_endpoints_gone(self, client):
        assert (await client.get("/api/v1/resume/templates")).status_code == 404
        assert (await client.get("/api/v1/resume/templates/executive")).status_code == 404
        assert (await client.get("/api/v1/resume/template-resolve/executive")).status_code == 404

    def test_legacy_mapping_module_removed(self):
        import importlib.util

        assert importlib.util.find_spec("app.rendering.legacy_template_mapping") is None

    def test_designer_has_no_dead_rendering_init(self):
        import app.api.v1.designer as designer

        assert not hasattr(designer, "rendering")

    def test_variants_has_no_dead_rendering_init(self):
        import app.api.v1.variants as variants

        assert not hasattr(variants, "rendering")


class TestCanonicalBoundary:
    """Prove the canonical pipeline renders every format without any legacy
    rendering stack (TemplateRegistry / Jinja HTMLRenderer /
    ResumeRenderingService / ReportLab) — which no longer even exists."""

    def test_legacy_rendering_modules_are_removed(self):
        def spec(module: str):
            import importlib.util

            try:
                return importlib.util.find_spec(module)
            except ModuleNotFoundError:
                return None

        removed = (
            "app.rendering.registry.template_registry",
            "app.rendering.renderers.html_renderer",
            "app.rendering.service",
            "app.rendering.preview.service",
            "app.rendering.engine.renderer",
            "app.rendering.legacy_templates",
            "app.rendering.legacy_template_mapping",
            "app.services.pdf_templates.engine",
            "app.services.pdf_service",
            "app.services.pdf_pipeline",
            "app.services.template_admin_service",
            "app.api.v1.pdf",
        )
        for module in removed:
            assert spec(module) is None, module

    def test_canonical_rendering_does_not_import_legacy_stack(self):
        import subprocess
        import sys
        from pathlib import Path

        backend_dir = Path(__file__).resolve().parents[1]
        script = r"""
import sys
from app.models.resume import Resume
from app.rendering import export_service as es
from app.rendering import layout_html as lh
from app.rendering import layout_preview as lp

r = Resume(
    user_id="t",
    full_name="Boundary Tester",
    email="t@test.com",
    professional_title="Engineer",
    summary="Canonical-only proof.",
    experience=[{"company": "Acme", "title": "Engineer", "start_date": "2020", "current": True}],
    education=[{"institution": "MIT", "degree": "B.Sc.", "field": "CS"}],
    skills=[{"category": "Languages", "skills": ["Python"]}],
)
layouts = lp.default_layout_registry()
themes = lp.default_theme_registry()
for layout_id in ("executive", "modern", "sidebar", "timeline", "classic", "minimal"):
    html = lh.render_resume_layout_html(r, layouts.resolve(layout_id), themes.resolve("blue"))
    pdf = es.export_resume(r, layout_id=layout_id, theme_id="blue", output_format=es.ExportFormat.PDF)
    docx = es.export_resume(r, layout_id=layout_id, theme_id="blue", output_format=es.ExportFormat.DOCX)
    hl = es.export_resume(r, layout_id=layout_id, theme_id="blue", output_format=es.ExportFormat.HTML)
    assert html and pdf.content and docx.content and hl.content

banned = (
    "app.rendering.registry.template_registry",
    "app.rendering.renderers.html_renderer",
    "app.rendering.service",
    "app.rendering.preview.service",
    "app.rendering.legacy_template_mapping",
    "app.services.pdf_templates",
    "jinja2",
    "reportlab",
)
loaded = [m for m in sys.modules if any(m == b or m.startswith(b + ".") for b in banned)]
assert not loaded, f"canonical pipeline imported legacy modules: {loaded}"
print("OK")
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            cwd=str(backend_dir),
            timeout=180,
        )
        assert result.returncode == 0, result.stderr
        assert "OK" in result.stdout


class TestVariantsIndependence:
    """Canonical export does not depend on the ``resume_variants`` model or its
    ``template_id`` metadata (retained only as opaque business metadata).

    A stored variant with legacy ``template_id`` metadata is exported through
    the canonical API by choosing the layout explicitly — no legacy resolution.
    """

    async def test_stored_variant_exports_through_canonical_api(self, client):
        from app.rendering.layout_preview import default_layout_registry
        from app.services.resume_variants.service import create as create_variant
        from app.services.storage_service import load_resume

        rid = _save_resume()
        resume = load_resume(rid, user_id="dev-user")
        assert resume is not None

        variant = create_variant(resume, "test", "Classic Variant", template_id="modern-ats")
        assert variant["template_id"] == "modern-ats"  # opaque metadata only

        # Canonical export keys purely off layout_id + theme_id.
        assert default_layout_registry().contains("classic")
        response = await client.post(
            f"/api/v1/resume/{rid}/export",
            json={"layout_id": "classic", "theme_id": "blue", "format": "pdf"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
