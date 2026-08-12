"""Tests for the /export-pdf legacy→canonical migration and hardening.

Covers:

A. ``POST /resume/{id}/export-pdf`` renders through the canonical RenderTree
   pipeline (``resolve_legacy_template`` → ``export_resume`` → PDF) while
   preserving the legacy response contract (``download_url``).
B. Hardened ``GET /resume/export/{filename}``: authenticated only, strict
   filename containment (no separators, no dotfiles, stays inside the export
   directory, must be a file), with no path details leaked.
C. Import graph: ``app.api.v1.variants`` must not pull in the legacy rendering
   stack (ResumeRenderingService / Jinja HTMLRenderer / PreviewService /
   ReportLab pdf_templates).

The legacy infrastructure itself is intentionally retained; only the
rendering dependency of this endpoint is now canonical.
"""

import io
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from pypdf import PdfReader

from app.main import app
from app.models.resume import Resume
from app.rendering import legacy_templates
from app.rendering.export_service import ExportFormat
from app.services.pdf_pipeline import PDF_OUTPUT_DIR
from app.services.storage_service import save_resume


@pytest.fixture
def client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _resume(user_id="test") -> Resume:
    return Resume(
        user_id=user_id,
        full_name="Sharma Rajasekar",
        email="sharma@test.com",
        phone="+1-555-0100",
        location="Auckland, New Zealand",
        linkedin="https://linkedin.com/in/sharma",
        professional_title="Senior Transformation & Infrastructure Leader",
        summary="Transformation leader focused on distributed systems and platform reliability.",
        experience=[
            {"company": "Acme Corporation International", "title": "Senior Software Engineering Lead",
             "location": "San Francisco, CA", "start_date": "2021", "current": True,
             "description": ["Led a 12-engineer platform organization", "Designed multi-region streaming"]},
            {"company": "Beta Inc", "title": "Transformation Programme Manager",
             "start_date": "2018", "end_date": "2021", "description": ["Built a distributed scheduler"]},
        ],
        education=[{"institution": "Carnegie Mellon University", "degree": "Master of Science", "field": "Computer Science", "gpa": 3.9}],
        skills=[{"category": "Languages", "skills": ["Python", "Go", "Rust"]}],
        certifications=[{"name": "AWS Solutions Architect", "issuer": "Amazon Web Services", "date": "2022"}],
        projects=[{"name": "Project Alpha", "description": "Distributed scheduler", "url": "https://github.com/example/alpha", "technologies": ["Go", "PostgreSQL"]}],
    )


def _save_resume(user_id="test") -> str:
    resume_id = uuid.uuid4().hex
    save_resume(resume_id, _resume(user_id))
    return resume_id


def _pdf_text(data: bytes) -> str:
    return " ".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(data)).pages)


# ── A. /export-pdf canonical pipeline proof ───────────────────────────────────


class TestExportPdfCanonicalPipeline:
    """POST /resume/{id}/export-pdf must use the canonical RenderTree pipeline."""

    @pytest.mark.asyncio
    async def test_single_column_mapping_renders_canonical_pdf(self, client, monkeypatch):
        from app.rendering import export_service as es_mod

        rid = _save_resume()
        body = {"resume_data": _resume().model_dump(mode="json"), "template_id": "executive"}

        calls: list = []
        real_export = es_mod.export_resume

        def spy(resume, *, layout_id, theme_id, output_format):
            calls.append((resume, layout_id, theme_id, output_format))
            return real_export(resume, layout_id=layout_id, theme_id=theme_id, output_format=output_format)

        monkeypatch.setattr(es_mod, "export_resume", spy)

        response = await client.post(f"/api/v1/resume/{rid}/export-pdf", json=body)
        assert response.status_code == 200
        data = response.json()["data"]
        assert "download_url" in data

        # Canonical pipeline was actually invoked with the deterministic mapping.
        assert calls, "canonical export_resume was not invoked"
        _, layout_id, theme_id, output_format = calls[-1]
        assert layout_id == legacy_templates.resolve_legacy_template("executive") == "executive"
        assert theme_id == legacy_templates.DEFAULT_LEGACY_THEME
        assert output_format is ExportFormat.PDF

        download = await client.get(data["download_url"])
        assert download.status_code == 200
        assert download.headers["content-type"] == "application/pdf"
        content = download.content
        assert content[:5] == b"%PDF-"
        text = _pdf_text(content)
        assert "Sharma Rajasekar" in text
        assert "Acme Corporation International" in text
        assert "Carnegie Mellon University" in text
        assert "Python" in text

    @pytest.mark.asyncio
    async def test_two_column_mapping_renders_canonical_pdf(self, client, monkeypatch):
        from app.rendering import export_service as es_mod

        rid = _save_resume()
        body = {"resume_data": _resume().model_dump(mode="json"), "template_id": "executive-elite"}

        calls: list = []
        real_export = es_mod.export_resume

        def spy(resume, *, layout_id, theme_id, output_format):
            calls.append((resume, layout_id, theme_id, output_format))
            return real_export(resume, layout_id=layout_id, theme_id=theme_id, output_format=output_format)

        monkeypatch.setattr(es_mod, "export_resume", spy)

        response = await client.post(f"/api/v1/resume/{rid}/export-pdf", json=body)
        assert response.status_code == 200
        download = await client.get(response.json()["data"]["download_url"])
        assert download.status_code == 200
        assert download.content[:5] == b"%PDF-"

        _, layout_id, _, _ = calls[-1]
        assert layout_id == legacy_templates.resolve_legacy_template("executive-elite") == "sidebar"
        assert "Sharma Rajasekar" in _pdf_text(download.content)

    @pytest.mark.asyncio
    async def test_unknown_template_rejected_without_fallback(self, client):
        rid = _save_resume()
        body = {"resume_data": _resume().model_dump(mode="json"), "template_id": "does-not-exist"}
        response = await client.post(f"/api/v1/resume/{rid}/export-pdf", json=body)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_resume_data_rejected(self, client):
        rid = _save_resume()
        response = await client.post(
            f"/api/v1/resume/{rid}/export-pdf",
            json={"resume_data": {"bad": "shape"}, "template_id": "executive"},
        )
        assert response.status_code == 400


# ── B. Download security tests ────────────────────────────────────────────────


class TestExportDownloadSecurity:
    """GET /resume/export/{filename} must be authenticated and traversal-safe."""

    @pytest.mark.asyncio
    async def test_unauthenticated_request_rejected(self, client, monkeypatch):
        from app.core.config import settings as app_settings

        monkeypatch.setattr(app_settings, "debug", False)
        response = await client.get("/api/v1/resume/export/0000000000000000.pdf")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_artifact_served(self, client):
        artifact = PDF_OUTPUT_DIR / "deadbeefcafef00d.pdf"
        artifact.write_bytes(b"%PDF-1.4 fake artifact" )
        try:
            response = await client.get("/api/v1/resume/export/deadbeefcafef00d.pdf")
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/pdf"
            assert response.content == b"%PDF-1.4 fake artifact"
        finally:
            artifact.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_traversal_with_slash_rejected(self, client):
        response = await client.get("/api/v1/resume/export/..%2F..%2Fetc%2Fpasswd")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_backslash_rejected(self, client):
        response = await client.get("/api/v1/resume/export/abc%5Cdef.pdf")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_dotfile_rejected(self, client):
        response = await client.get("/api/v1/resume/export/.env")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_dot_relative_rejected(self, client):
        response = await client.get("/api/v1/resume/export/..%2Fx.pdf")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_symlink_resolving_outside_rejected(self, client, tmp_path):
        """A filename that resolves (through a symlink) outside the export dir is rejected."""
        outside = tmp_path / "leaked.pdf"
        outside.write_bytes(b"%PDF-1.4 secret")
        link = PDF_OUTPUT_DIR / "symlink-leak.pdf"
        try:
            link.symlink_to(outside)
            response = await client.get("/api/v1/resume/export/symlink-leak.pdf")
            assert response.status_code == 404
        finally:
            link.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_nonexistent_file_rejected(self, client):
        response = await client.get("/api/v1/resume/export/0000000000000000.pdf")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_directory_masquerading_as_file_rejected(self, client):
        subdir = PDF_OUTPUT_DIR / "fake-file-dir"
        subdir.mkdir(exist_ok=True)
        try:
            response = await client.get("/api/v1/resume/export/fake-file-dir")
            assert response.status_code == 404
        finally:
            subdir.rmdir()

    @pytest.mark.asyncio
    async def test_rejection_leaks_no_paths(self, client):
        response = await client.get("/api/v1/resume/export/..%2F..%2Fetc%2Fpasswd")
        body = response.text
        assert response.status_code == 404
        assert "pdf_exports" not in body
        assert "/etc/" not in body
        assert str(PDF_OUTPUT_DIR) not in body


# ── C. Import-graph proof ─────────────────────────────────────────────────────


class TestVariantsImportGraph:
    """Importing app.api.v1.variants must not load the legacy renderer stack."""

    def test_variants_does_not_import_legacy_renderer_stack(self):
        backend_dir = Path(__file__).resolve().parents[1]
        script = r"""
import sys
before = set(sys.modules)
import app.api.v1.variants  # noqa: F401
after = set(sys.modules)
new = after - before

# Legacy rendering stack that the migrated endpoint must not require.
banned = (
    "app.rendering.registry.template_registry",  # TemplateRegistry
    "app.rendering.service",               # ResumeRenderingService
    "app.rendering.preview.service",       # PreviewService
    "app.rendering.renderers.html_renderer",  # legacy Jinja HTMLRenderer
    "app.services.pdf_templates",          # ReportLab resume PDF templates
    "reportlab",
    "jinja2",
)
loaded = sorted(m for m in new if any(m == b or m.startswith(b + ".") for b in banned))
assert not loaded, f"app.api.v1.variants imports legacy renderer stack: {loaded}"
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
