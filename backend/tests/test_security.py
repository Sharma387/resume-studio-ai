"""Tests for security headers middleware and CSP frame-ancestors handling."""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.middleware.security import PREVIEW_FILE_PREFIX, SecurityHeadersMiddleware


def _make_app():
    app = FastAPI()

    @app.get("/api/v1/resume/preview/file/demo.html")
    async def preview_file():
        return HTMLResponse("<html><body>preview</body></html>")

    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok"}

    app.add_middleware(SecurityHeadersMiddleware)
    return app


class TestFrameAncestorsParsing:
    def test_space_separated_default(self):
        assert settings.frame_ancestors_list == ["'self'", "http://localhost:5173", "http://127.0.0.1:5173"]

    def test_comma_separated_normalized(self, monkeypatch):
        monkeypatch.setattr(settings, "frame_ancestors", "'self', http://localhost:5173, http://127.0.0.1:5173")
        assert settings.frame_ancestors_list == ["'self'", "http://localhost:5173", "http://127.0.0.1:5173"]

    def test_mixed_separators_normalized(self, monkeypatch):
        monkeypatch.setattr(
            settings, "frame_ancestors", "'self', http://a.example.com http://b.example.com,https://c.example.com"
        )
        assert settings.frame_ancestors_list == [
            "'self'",
            "http://a.example.com",
            "http://b.example.com",
            "https://c.example.com",
        ]

    def test_empty_value_returns_empty_list(self, monkeypatch):
        monkeypatch.setattr(settings, "frame_ancestors", "")
        assert settings.frame_ancestors_list == []


class TestSecurityHeadersMiddleware:
    def test_preview_file_gets_frame_ancestors_csp(self):
        client = TestClient(_make_app())
        res = client.get("/api/v1/resume/preview/file/demo.html")
        assert res.status_code == 200
        csp = res.headers.get("content-security-policy")
        assert csp is not None
        assert csp.startswith("frame-ancestors ")
        assert "'self'" in csp
        assert "http://localhost:5173" in csp
        # No X-Frame-Options that would conflict with the CSP.
        assert "x-frame-options" not in res.headers

    def test_other_routes_get_x_frame_options_deny(self):
        client = TestClient(_make_app())
        res = client.get("/api/v1/health")
        assert res.status_code == 200
        assert res.headers.get("x-frame-options") == "DENY"
        assert "content-security-policy" not in res.headers

    def test_other_security_headers_present(self):
        client = TestClient(_make_app())
        res = client.get("/api/v1/health")
        assert res.headers.get("x-content-type-options") == "nosniff"
        assert res.headers.get("x-xss-protection") == "1; mode=block"
        assert "strict-origin-when-cross-origin" in res.headers.get("referrer-policy", "")
        assert res.headers.get("permissions-policy") is not None

    def test_csp_is_space_separated_even_with_comma_config(self, monkeypatch):
        monkeypatch.setattr(settings, "frame_ancestors", "'self', http://localhost:5173, http://127.0.0.1:5173")
        client = TestClient(_make_app())
        res = client.get("/api/v1/resume/preview/file/demo.html")
        csp = res.headers.get("content-security-policy")
        # The emitted directive must be a valid space-separated source list.
        assert csp == "frame-ancestors 'self' http://localhost:5173 http://127.0.0.1:5173"

    def test_empty_config_falls_back_to_self(self, monkeypatch):
        monkeypatch.setattr(settings, "frame_ancestors", "")
        client = TestClient(_make_app())
        res = client.get("/api/v1/resume/preview/file/demo.html")
        assert res.headers.get("content-security-policy") == "frame-ancestors 'self'"


def test_preview_prefix_constant_matches_route():
    assert PREVIEW_FILE_PREFIX == "/api/v1/resume/preview/file/"
