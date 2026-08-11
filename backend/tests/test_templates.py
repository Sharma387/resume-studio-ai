"""Tests for the resume template feature — registry, rendering, and API endpoints."""

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.resume import Resume
from app.rendering.registry.template_registry import TEMPLATES_DIR, TemplateRegistry
from app.rendering.service import ResumeRenderingService
from app.services import template_admin_service as tas
from app.services.storage_service import save_resume


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _make_resume(**overrides) -> Resume:
    data = dict(
        user_id="test",
        full_name="Template Test User",
        email="template@test.com",
        summary="Experienced engineer with 5+ years of experience.",
        phone="+1 555-0100",
        location="San Francisco",
        education=[{"institution": "MIT", "degree": "BS", "field": "Computer Science"}],
        experience=[
            {
                "company": "Acme",
                "title": "Senior Engineer",
                "start_date": "2020-01",
                "end_date": "2024-12",
                "description": ["Built microservices", "Reduced latency by 40%"],
            }
        ],
        skills=[{"category": "Languages", "skills": ["Python", "Go", "TypeScript"]}],
        projects=[{"name": "Open Source", "description": "A popular library"}],
        certifications=[{"name": "AWS Certified Solutions Architect"}],
    )
    data.update(overrides)
    return Resume(**data)


# ── Template Registry / Manifest Validation ─────────────────────────────────────


class TestTemplateRegistryValidation:
    def test_every_filesystem_template_is_discovered(self):
        """Every directory with a manifest.json must be a valid, discoverable template."""
        registry = TemplateRegistry()
        registry.invalidate_cache()
        discovered = registry.discover()

        expected = {
            d.name
            for d in TEMPLATES_DIR.iterdir()
            if d.is_dir() and (d / "manifest.json").exists()
        }
        assert expected == set(discovered.keys())

    def test_all_manifests_have_required_fields(self):
        registry = TemplateRegistry()
        registry.invalidate_cache()
        for pkg in registry.discover().values():
            m = pkg.manifest
            assert m.id, "manifest missing id"
            assert m.name, "manifest missing name"
            assert isinstance(m.ats_score, int)
            assert 0 <= m.ats_score <= 100, f"{m.id} ats_score out of range"
            assert m.colour_themes, f"{m.id} has no colour themes"

    def test_template_ids_are_unique(self):
        registry = TemplateRegistry()
        registry.invalidate_cache()
        ids = [pkg.manifest.id for pkg in registry.discover().values()]
        assert len(ids) == len(set(ids))

    def test_every_template_has_template_html(self):
        registry = TemplateRegistry()
        registry.invalidate_cache()
        for pkg in registry.discover().values():
            assert pkg.html_path is not None, f"{pkg.manifest.id} missing template.html"

    def test_categories_are_reported(self):
        cats = tas.get_categories()
        assert isinstance(cats, list)
        assert len(cats) > 0
        assert all(isinstance(c, str) and c for c in cats)

    def test_validate_existing_template(self):
        registry = TemplateRegistry()
        registry.invalidate_cache()
        template_id = next(iter(registry.discover().keys()))
        result = tas.validate_template(template_id)
        assert result["valid"] is True

    def test_validate_missing_template(self):
        result = tas.validate_template("does-not-exist")
        assert result["valid"] is False

    def test_get_template_detail_returns_metadata(self):
        registry = TemplateRegistry()
        registry.invalidate_cache()
        template_id = next(iter(registry.discover().keys()))
        detail = tas.get_template_detail(template_id)
        assert detail is not None
        assert detail["id"] == template_id
        assert "has_html" in detail
        assert "has_css" in detail

    def test_get_template_detail_missing_returns_none(self):
        assert tas.get_template_detail("does-not-exist") is None


# ── Rendering Service Tests ─────────────────────────────────────────────────────


class TestRenderingService:
    def test_render_html_raises_for_unknown_template(self):
        svc = ResumeRenderingService()
        with pytest.raises(ValueError):
            svc.render_html(_make_resume(), "does-not-exist")

    def test_render_html_with_theme(self):
        svc = ResumeRenderingService()
        resume = _make_resume(full_name="Themed Resume")
        html = svc.render_html(resume, "executive", theme="blue")
        assert html.startswith("<!DOCTYPE html>")
        assert "Themed Resume" in html

    def test_list_templates_matches_filesystem(self):
        svc = ResumeRenderingService()
        registry = TemplateRegistry()
        registry.invalidate_cache()
        api_ids = {t["id"] for t in svc.list_templates()}
        disk_ids = set(registry.discover().keys())
        assert api_ids == disk_ids

    def test_generate_preview_creates_file_and_caches(self):
        svc = ResumeRenderingService()
        resume = _make_resume(full_name="Preview Cache Test")
        p1 = svc.generate_preview(resume, "executive")
        p2 = svc.generate_preview(resume, "executive")
        assert Path(p1).exists()
        assert p1 == p2  # cached
        assert "Resume" in Path(p1).read_text(encoding="utf-8")

    def test_generate_preview_raises_for_unknown_template(self):
        svc = ResumeRenderingService()
        with pytest.raises(ValueError):
            svc.generate_preview(_make_resume(), "does-not-exist")


# ── Template API Endpoints ──────────────────────────────────────────────────────


class TestTemplateAPI:
    @pytest.mark.asyncio
    async def test_list_templates_returns_all_with_metadata(self, client):
        resp = await client.get("/api/v1/resume/templates")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert len(body["data"]) >= 12
        for t in body["data"]:
            assert "id" in t and "name" in t and "description" in t
            assert "category" in t
            assert "ats_score" in t
            assert "colour_themes" in t
            assert "has_preview" in t
            assert "has_thumbnail" in t

    @pytest.mark.asyncio
    async def test_list_templates_not_shadowed_by_resume_param(self, client):
        """Regression: GET /resume/templates must resolve to the template list,
        not be captured by the /resume/{resume_id} route."""
        resp = await client.get("/api/v1/resume/templates")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert isinstance(body["data"], list)
        assert "templates" not in body.get("detail", "")  # not "Resume not found"

    @pytest.mark.asyncio
    async def test_get_template_returns_detail(self, client):
        resp = await client.get("/api/v1/resume/templates/executive")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["id"] == "executive"
        assert body["data"]["name"] == "Executive Classic"

    @pytest.mark.asyncio
    async def test_get_template_404_for_missing(self, client):
        resp = await client.get("/api/v1/resume/templates/does-not-exist")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_preview_returns_preview_url(self, client):
        resume = _make_resume(full_name="Preview API Test")
        save_resume("tpl-preview-1", resume)
        resp = await client.get(
            "/api/v1/resume/tpl-preview-1/preview?template_id=executive&theme=blue"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["preview_url"].startswith("/api/v1/resume/preview/file/")

    @pytest.mark.asyncio
    async def test_preview_404_for_missing_resume(self, client):
        resp = await client.get(
            "/api/v1/resume/tpl-does-not-exist/preview?template_id=executive"
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_preview_404_for_unknown_template(self, client):
        resume = _make_resume(full_name="Bad Template API Test")
        save_resume("tpl-preview-bad", resume)
        resp = await client.get(
            "/api/v1/resume/tpl-preview-bad/preview?template_id=does-not-exist"
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_serve_preview_file_returns_html(self, client):
        resume = _make_resume(full_name="Preview File API Test")
        save_resume("tpl-preview-file", resume)
        gen = await client.get("/api/v1/resume/tpl-preview-file/preview?template_id=executive")
        assert gen.status_code == 200
        preview_url = gen.json()["data"]["preview_url"]

        resp = await client.get(preview_url)
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")
        assert "Preview File API Test" in resp.text

    @pytest.mark.asyncio
    async def test_serve_preview_file_404_for_missing(self, client):
        resp = await client.get("/api/v1/resume/preview/file/nope.html")
        assert resp.status_code == 404


# ── Recommendation Integration (template metadata) ──────────────────────────────


class TestTemplateRecommendations:
    @pytest.mark.asyncio
    async def test_optimize_returns_recommended_templates(self, client):
        resume = _make_resume()
        resp = await client.post(
            "/api/v1/designer/tpl-recs/optimize",
            json={"resume_data": resume.model_dump(mode="json")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        recs = body["data"]["recommended_templates"]
        assert len(recs) > 0
        for r in recs:
            assert "template_id" in r
            assert "score" in r
        scores = [r["score"] for r in recs]
        assert scores == sorted(scores, reverse=True)
