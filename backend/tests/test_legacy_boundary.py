"""Legacy rendering retirement — architectural guard tests.

After the final retirement:

* the canonical preview/export/recommendation/optimize/target-job paths must
  never load any legacy rendering stack (these modules no longer exist);
* retired legacy HTTP endpoints must not be reachable;
* the canonical frontend must not call any retired resume API
  (``/resume/templates``, ``template-resolve``, ``/resume/{id}/pdf``,
  ``/export-pdf``, …);
* canonical export must not depend on ``resume_variants``.
"""

import re
import subprocess
import sys
from pathlib import Path

_LIVE_LEGACY_BOUNDARY = (
    "app.rendering.registry.template_registry",  # TemplateRegistry
    "app.rendering.service",                     # ResumeRenderingService
    "app.rendering.preview.service",             # PreviewService
    "app.rendering.renderers.html_renderer",     # legacy Jinja HTMLRenderer
    "app.rendering.legacy_template_mapping",     # retired template→layout mapping
    "app.services.pdf_templates",                # ReportLab resume PDF templates
    "jinja2",
)

#: extended boundary for rendering-path probes (canonical preview/export must
#: not load ReportLab either).
_RENDERING_BOUNDARY = _LIVE_LEGACY_BOUNDARY + ("reportlab",)


def _spec(module: str):
    """find_spec that treats a missing parent package as an absent module."""
    import importlib.util

    try:
        return importlib.util.find_spec(module)
    except ModuleNotFoundError:
        return None


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


class TestLegacyStackRemoved:
    def test_legacy_rendering_modules_are_removed(self):
        removed = (
            "app.rendering.registry.template_registry",   # TemplateRegistry
            "app.rendering.renderers.html_renderer",      # legacy Jinja HTMLRenderer
            "app.rendering.service",                      # ResumeRenderingService
            "app.rendering.preview.service",              # PreviewService
            "app.rendering.engine.renderer",              # legacy renderer base
            "app.rendering.models",                       # legacy template models
            "app.rendering.legacy_templates",             # retired boundary
            "app.rendering.legacy_template_mapping",      # retired URL mapping
            "app.services.pdf_templates",                 # ReportLab resume templates
            "app.services.pdf_service",
            "app.services.pdf_pipeline",
            "app.services.template_admin_service",
            "app.api.v1.pdf",
        )
        for module in removed:
            assert _spec(module) is None, module
            assert module not in sys.modules, module

    def test_legacy_api_routes_not_registered(self):
        from app.main import app as fastapi_app

        paths = {r.path for r in fastapi_app.routes}
        for retired in (
            "/api/v1/resume/templates",
            "/api/v1/resume/templates/{template_id}",
            "/api/v1/resume/template-resolve/{template_id}",
            "/api/v1/resume/{resume_id}/pdf",
            "/api/v1/resume/{resume_id}/pdf/download",
            "/api/v1/templates",
            "/api/v1/resume/{resume_id}/export-pdf",
            "/api/v1/resume/export/{filename}",
            "/api/v1/admin/templates",
        ):
            assert retired not in paths, retired


class TestCanonicalImportGuard:
    def test_canonical_preview_router_imports_no_legacy_stack(self):
        _run_import_probe("import app.api.v1.rendering")

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


class TestFrontendLegacyApiGuard:
    FORBIDDEN = (
        "/resume/templates",
        "template-resolve",
        "/export-pdf",
        "/resume/{id}/pdf",
        "generatePdf",
        "getPdfDownloadUrl",
        "Legacy Templates",
    )

    def test_canonical_frontend_has_no_legacy_api_calls(self):
        src = Path(__file__).resolve().parents[2] / "frontend" / "src"
        files = sorted(list(src.rglob("*.ts")) + list(src.rglob("*.tsx")))
        assert files, "frontend/src must exist for the guard to run"

        violations: list[str] = []
        for path in files:
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                text = line.strip()
                if any(marker in text for marker in self.FORBIDDEN):
                    violations.append(f"{path.relative_to(src)}:{i}: {text}")
                if re.search(r"/resume/\$\{[^}]+\}/pdf", text) and "cover-letter" not in text:
                    violations.append(f"{path.relative_to(src)}:{i}: {text}")
        assert not violations, "canonical frontend still references retired resume APIs:\n" + "\n".join(violations)


class TestVariantsImportIndependence:
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
