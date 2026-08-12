"""Phase 3 — legacy compatibility boundary isolation guards.

Covers:

A. Deterministic ``TEMPLATE_TO_LAYOUT`` mapping groups (all 13 legacy ids).
B. Import graph: canonical preview / PDF / admin routers no longer load the
   legacy rendering stack at import time.
C. Runtime proof: canonical preview + canonical export never load
   TemplateRegistry / PreviewService / ResumeRenderingService / Jinja
   HTMLRenderer / ReportLab.
D. ``/resume/template-resolve/{id}`` compatibility endpoint behavior (pure
   mapping, no registry, no fallback).
E. Frontend guard: the canonical UI no longer calls the legacy resume APIs.
F. ``resume_variants.template_id`` is not required by canonical export.
"""

import re
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.resume import Resume
from app.rendering import legacy_templates
from app.services.storage_service import save_resume

_LIVE_LEGACY_BOUNDARY = (
    "app.rendering.registry.template_registry",  # TemplateRegistry
    "app.rendering.service",                     # ResumeRenderingService
    "app.rendering.preview.service",             # PreviewService
    "app.rendering.renderers.html_renderer",     # legacy Jinja HTMLRenderer
    "app.services.pdf_templates",                # ReportLab resume PDF templates
    "jinja2",
)

#: extended boundary for rendering-path probes (canonical preview/export must
#: not load ReportLab either).
_RENDERING_BOUNDARY = _LIVE_LEGACY_BOUNDARY + ("reportlab",)


@pytest.fixture
def client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _save_resume(user_id="test") -> str:
    resume_id = uuid.uuid4().hex
    save_resume(resume_id, Resume(user_id=user_id, full_name="Boundary User", email="b@test.com"))
    return resume_id


def _run_import_probe(script_body: str, banned: tuple[str, ...] = _LIVE_LEGACY_BOUNDARY) -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    script = (
        "import sys\n"
        "before = set(sys.modules)\n"
        + script_body
        + "\n"
        "new = set(sys.modules) - before\n"
        f"banned = {banned!r}\n"
        "loaded = sorted(m for m in new if any(m == b or m.startswith(b + '.') for b in banned))\n"
        "assert not loaded, f'legacy stack loaded: {loaded}'\n"
        'print("OK")\n'
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=str(backend_dir),
        timeout=180,
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


# ── A. Deterministic mapping groups (Step 6) ──────────────────────────────────


class TestCanonicalMappingDeterminism:
    EXPECTED_GROUPS = {
        "executive": {"executive", "finance-executive", "corporate-blue"},
        "sidebar": {"executive-elite"},
        "modern": {"consulting-pro", "software-engineer", "technology-lead", "creative-portfolio"},
        "classic": {"modern-ats", "government-standard", "healthcare-professional", "academic-research"},
        "minimal": {"minimal-professional"},
    }

    def test_all_13_legacy_templates_map_deterministically(self):
        covered = set(legacy_templates.TEMPLATE_TO_LAYOUT)
        assert len(covered) == 13
        assert covered == set(legacy_templates.LEGACY_TEMPLATE_IDS)
        grouped: dict[str, set[str]] = {}
        for template_id in legacy_templates.LEGACY_TEMPLATE_IDS:
            layout = legacy_templates.resolve_legacy_template(template_id)
            grouped.setdefault(layout, set()).add(template_id)
        assert grouped == self.EXPECTED_GROUPS

    def test_lookup_resolves_to_expected_layouts(self):
        checks = {
            "executive": "executive",
            "finance-executive": "executive",
            "corporate-blue": "executive",
            "executive-elite": "sidebar",
            "consulting-pro": "modern",
            "software-engineer": "modern",
            "technology-lead": "modern",
            "creative-portfolio": "modern",
            "modern-ats": "classic",
            "government-standard": "classic",
            "healthcare-professional": "classic",
            "academic-research": "classic",
            "minimal-professional": "minimal",
        }
        for template_id, expected in checks.items():
            assert legacy_templates.resolve_legacy_template(template_id) == expected
            assert legacy_templates.TEMPLATE_TO_LAYOUT[template_id] == expected

    def test_unknown_template_has_no_fallback(self):
        with pytest.raises(legacy_templates.UnknownLegacyTemplateError):
            legacy_templates.resolve_legacy_template("does-not-exist")

    def test_layout_to_template_reverse_map_stays_consistent(self):
        for layout_id, template_id in legacy_templates.LAYOUT_TO_TEMPLATE.items():
            if template_id is None:
                continue
            assert legacy_templates.resolve_legacy_template(template_id) == layout_id


# ── B/C. Import-graph guards (Steps 8, 9, 12) ─────────────────────────────────


class TestCanonicalApiImportGuard:
    def test_canonical_preview_router_imports_no_legacy_stack(self):
        _run_import_probe("import app.api.v1.rendering")

    def test_legacy_pdf_router_does_not_leak_legacy_at_import(self):
        _run_import_probe("import app.api.v1.pdf")

    def test_admin_console_does_not_load_legacy_at_startup(self):
        _run_import_probe("import app.api.v1.admin")

    def test_canonical_preview_runtime_imports_no_legacy_stack(self):
        _run_import_probe(
            "import app.rendering.layout_preview as lp\n"
            "import app.rendering.layout_html\n"
            "from app.models.resume import Resume\n"
            "r = Resume(user_id='t', full_name='X', email='x@t.com')\n"
            "lp.render_layout_preview_html(r, 'executive', 'blue')",
            banned=_RENDERING_BOUNDARY,
        )

    def test_canonical_export_runtime_imports_no_legacy_stack(self):
        _run_import_probe(
            "from app.rendering import export_service as es\n"
            "import app.rendering.layout_preview as lp\n"
            "from app.models.resume import Resume\n"
            "r = Resume(user_id='t', full_name='X', email='x@t.com')\n"
            "out = es.export_resume(r, layout_id='executive', theme_id='blue', output_format=es.ExportFormat.HTML)\n"
            "assert out.content",
            banned=_RENDERING_BOUNDARY,
        )


# ── D. /resume/template-resolve behavior ──────────────────────────────────────


class TestTemplateResolveEndpoint:
    @pytest.mark.asyncio
    async def test_resolves_legacy_template_to_canonical_layout(self, client):
        response = await client.get("/api/v1/resume/template-resolve/executive-elite")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["template_id"] == "executive-elite"
        assert body["data"]["layout_id"] == "sidebar"
        assert body["data"]["theme_id"] == legacy_templates.DEFAULT_LEGACY_THEME

    @pytest.mark.asyncio
    async def test_unknown_template_rejected_without_fallback(self, client):
        response = await client.get("/api/v1/resume/template-resolve/does-not-exist")
        assert response.status_code == 404


# ── E. Frontend legacy API guard (Step 12) ────────────────────────────────────


class TestFrontendLegacyApiGuard:
    def test_canonical_frontend_does_not_call_legacy_resume_apis(self):
        src = Path(__file__).resolve().parents[2] / "frontend" / "src"
        files = sorted(src.rglob("*.ts")) + sorted(src.rglob("*.tsx"))
        assert files, "frontend/src must exist for the guard to run"

        violations: list[str] = []
        for path in files:
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                text = line.strip()
                if any(marker in text for marker in ("/resume/templates", "/export-pdf", "generatePdf", "getPdfDownloadUrl")):
                    violations.append(f"{path.relative_to(src)}:{i}: {text}")
                if re.search(r"/resume/\$\{[^}]+\}/pdf", text) and "cover-letter" not in text:
                    violations.append(f"{path.relative_to(src)}:{i}: {text}")
        assert not violations, "canonical frontend still calls legacy resume APIs:\n" + "\n".join(violations)

    def test_frontend_still_uses_compat_resolve_for_template_redirect(self):
        designer = Path(__file__).resolve().parents[2] / "frontend" / "src" / "pages" / "TemplateDesignerPage.tsx"
        text = designer.read_text(encoding="utf-8")
        assert "/resume/template-resolve/" in text  # explicit ?template= compatibility path
        assert "/resume/templates" not in text


# ── F. resume_variants not required by canonical export (Step 11) ─────────────


class TestVariantsIndependence:
    def test_canonical_export_does_not_import_resume_variants(self):
        backend_dir = Path(__file__).resolve().parents[1]
        script = (
            "import sys\n"
            "before = set(sys.modules)\n"
            "import app.rendering.export_service as es\n"
            "import app.rendering.layout_preview as lp\n"
            "new = set(sys.modules) - before\n"
            "hits = [m for m in new if m.startswith('app.services.resume_variants') or m.startswith('app.db.models.variant')]\n"
            "assert not hits, hits\n"
            'print("OK")\n'
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            cwd=str(backend_dir),
            timeout=180,
        )
        assert result.returncode == 0, result.stderr
        assert "OK" in result.stdout
