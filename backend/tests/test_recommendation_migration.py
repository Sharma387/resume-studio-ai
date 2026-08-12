"""Phase 2 — business services decoupled from legacy rendering.

Proves:

A. ``recommendation_service``, the optimize path (``app.api.v1.designer``),
   and the target-job/recommendations path (``app.api.v1.variants``) no
   longer import the legacy rendering stack (TemplateRegistry,
   ResumeRenderingService, PreviewService, Jinja HTMLRenderer, ReportLab).
B. Behavioral contracts for /recommendations, /optimize, and /target-job are
   preserved, including the legacy ``template_id`` compatibility field.
"""

import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.resume import Resume
from app.rendering import legacy_templates
from app.rendering.layout_preview import default_layout_registry
from app.services.recommendation_service import recommend
from app.services.storage_service import save_resume

_BANNED = (
    "app.rendering.registry.template_registry",  # TemplateRegistry
    "app.rendering.service",                     # ResumeRenderingService
    "app.rendering.preview.service",             # PreviewService
    "app.rendering.renderers.html_renderer",     # legacy Jinja HTMLRenderer
    "app.services.pdf_templates",                # ReportLab resume PDF templates
    "reportlab",
    "jinja2",
)


@pytest.fixture
def client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _resume(**overrides) -> Resume:
    data = dict(
        user_id="test",
        full_name="Sharma Rajasekar",
        email="sharma@test.com",
        professional_title="Senior Software Engineering Lead",
        summary="Transformation leader focused on distributed systems and platform reliability.",
        experience=[
            {"company": "Acme Corporation", "title": "Senior Software Engineering Lead",
             "start_date": "2021", "current": True,
             "description": ["Led a 12-engineer platform organization", "Reduced latency by 40%"]},
            {"company": "Beta Inc", "title": "Transformation Programme Manager",
             "start_date": "2018", "end_date": "2021", "description": ["Built a distributed scheduler"]},
        ],
        education=[{"institution": "Carnegie Mellon University", "degree": "Master of Science", "field": "Computer Science"}],
        skills=[{"category": "Languages", "skills": ["Python", "Go", "Rust"]}],
    )
    data.update(overrides)
    return Resume(**data)


def _resume_data(**overrides) -> dict:
    return _resume(**overrides).model_dump(mode="json")


def _save_resume(user_id="test") -> str:
    resume_id = uuid.uuid4().hex
    save_resume(resume_id, _resume())
    return resume_id


def _run_import_probe(module: str) -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    script = f"""
import sys
before = set(sys.modules)
import {module}
new = set(sys.modules) - before
banned = {_BANNED!r}
loaded = sorted(m for m in new if any(m == b or m.startswith(b + ".") for b in banned))
assert not loaded, f"{{module}} imports legacy rendering stack: {{loaded}}"
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


# ── A. Import-graph proofs ────────────────────────────────────────────────────


class TestRecommendationImportGraph:
    def test_recommendation_service_imports_no_legacy_rendering(self):
        _run_import_probe("app.services.recommendation_service")

    def test_optimize_path_imports_no_legacy_rendering(self):
        _run_import_probe("app.api.v1.designer")

    def test_business_endpoints_import_no_legacy_rendering(self):
        # variants hosts /recommendations and /target-job.
        _run_import_probe("app.api.v1.variants")


# ── B. Recommendations behavior ───────────────────────────────────────────────


class TestRecommendationsBehavior:
    def test_valid_resume_recommends_canonical_layouts(self):
        recs = recommend(_resume())
        assert len(recs) == len(default_layout_registry().list())
        assert recs
        scores = [r["score"] for r in recs]
        assert scores == sorted(scores, reverse=True)
        registry_ids = set(default_layout_registry().list())
        for r in recs:
            assert 0 <= r["score"] <= 100
            assert r["layout_id"] in registry_ids
            assert "template_id" in r
            assert "name" in r and r["name"]
            assert "category" in r
            assert "ats_score" in r
            assert "best_for" in r

    def test_legacy_template_id_compat_resolves_back_to_layout(self):
        recs = recommend(_resume())
        compat = {r["template_id"] for r in recs if r["template_id"] is not None}
        assert compat == {
            "executive", "executive-elite", "consulting-pro",
            "modern-ats", "minimal-professional",
        }
        for r in recs:
            if r["template_id"] is not None:
                assert legacy_templates.resolve_legacy_template(r["template_id"]) == r["layout_id"]

    def test_empty_resume_still_returns_all_layouts(self):
        recs = recommend(Resume(user_id="test", full_name="Edge", email="edge@test.com"))
        assert len(recs) == len(default_layout_registry().list())
        for r in recs:
            assert 0 <= r["score"] <= 100

    def test_technical_resume_ranks_ats_layouts_first(self):
        recs = recommend(_resume())
        assert recs[0]["layout_id"] in ("classic", "minimal")

    @pytest.mark.asyncio
    async def test_recommendations_endpoint_contract(self, client):
        rid = _save_resume()
        response = await client.get(f"/api/v1/resume/{rid}/recommendations")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        data = body["data"]
        assert isinstance(data, list) and data
        assert "layout_id" in data[0]
        assert "template_id" in data[0]

    @pytest.mark.asyncio
    async def test_recommendations_unknown_resume_404(self, client):
        response = await client.get("/api/v1/resume/does-not-exist/recommendations")
        assert response.status_code == 404


# ── C. Optimize behavior ──────────────────────────────────────────────────────


class TestOptimizeBehavior:
    @pytest.mark.asyncio
    async def test_optimize_returns_ats_and_layout_recommendations(self, client):
        response = await client.post(
            "/api/v1/designer/any-variant/optimize",
            json={"resume_data": _resume_data()},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        ats = body["data"]["ats"]
        assert "overall_score" in ats
        assert "suggestions" in ats
        recs = body["data"]["recommended_templates"]
        assert recs
        scores = [r["score"] for r in recs]
        assert scores == sorted(scores, reverse=True)
        for r in recs:
            assert "template_id" in r
            assert "layout_id" in r

    @pytest.mark.asyncio
    async def test_optimize_vestigial_variant_id_ignored(self, client):
        """The endpoint keys off body.resume_data; variant_id is vestigial."""
        response = await client.post(
            "/api/v1/designer/not-a-real-variant/optimize",
            json={"resume_data": _resume_data()},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_optimize_missing_resume_data_fails(self):
        """Pre-existing behavior: ``Resume(**{})`` raises an unhandled
        ``ValidationError`` that the global handler maps to 500. Not changed
        by this phase."""
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/designer/x/optimize",
                json={"resume_data": {}},
            )
        assert response.status_code == 500


# ── D. Target-job behavior ────────────────────────────────────────────────────


class TestTargetJobBehavior:
    @pytest.mark.asyncio
    async def test_valid_target_job_contract(self, client):
        rid = _save_resume()
        response = await client.post(
            "/api/v1/resume/target-job",
            json={"resume_id": rid, "job_description": "Python, Go and platform engineering."},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        data = body["data"]
        for key in ("matched_keywords", "missing_keywords", "match_rate", "total_keywords"):
            assert key in data

    @pytest.mark.asyncio
    async def test_target_job_unknown_resume_404(self, client):
        response = await client.post(
            "/api/v1/resume/target-job",
            json={"resume_id": "does-not-exist", "job_description": "anything"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_target_job_invalid_body_422(self, client):
        response = await client.post("/api/v1/resume/target-job", json={"resume_id": "r"})
        assert response.status_code == 422


# ── E. Legacy compatibility smoke (endpoints retained, not migrated) ──────────


class TestLegacyCompatibilitySmoke:
    """The decoupling of recommendation/optimize/target-job must not have
    disturbed the retained legacy compatibility surface."""

    @pytest.mark.asyncio
    async def test_legacy_template_preview_still_works(self, client):
        for template_id in ("executive", "executive-elite"):
            rid = _save_resume()
            response = await client.get(f"/api/v1/resume/{rid}/preview?template_id={template_id}")
            assert response.status_code == 200
            body = response.json()
            assert body["success"] is True
            assert "mode" not in body["data"]  # legacy preview shape

    @pytest.mark.asyncio
    async def test_resume_templates_endpoints_still_work(self, client):
        listing = await client.get("/api/v1/resume/templates")
        assert listing.status_code == 200
        assert len(listing.json()["data"]) >= 12
        detail = await client.get("/api/v1/resume/templates/executive")
        assert detail.status_code == 200
        assert detail.json()["data"]["layout_id"] == "executive"

    def test_admin_template_service_still_works(self):
        from app.services import template_admin_service as tas

        assert len(tas.list_templates()) >= 12
        assert "executive" in tas.get_categories() or bool(tas.get_categories())

    @pytest.mark.asyncio
    async def test_legacy_reportlab_pdf_still_works(self, client):
        rid = _save_resume()
        generated = await client.post(f"/api/v1/resume/{rid}/pdf?template=executive")
        assert generated.status_code == 200
        download = await client.get(generated.json()["downloadUrl"])
        assert download.status_code == 200
        assert download.headers["content-type"] == "application/pdf"
