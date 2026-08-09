"""Integration tests for the new layout-engine preview path (real API).

These exercise the actual preview API endpoint: layout mode (``layout_id``)
renders through the new engine; legacy mode (``template_id``) must remain
compatible.
"""

import re
import uuid
from collections import Counter
from html.parser import HTMLParser

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.resume import Certification as ResumeCertification
from app.models.resume import Education as ResumeEducation
from app.models.resume import Experience as ResumeExperience
from app.models.resume import Resume
from app.models.resume import Skill as ResumeSkill
from app.services.storage_service import save_resume

LAYOUTS = ("executive", "sidebar", "modern", "classic")
THEMES = ("blue", "gold")


class _StructureParser(HTMLParser):
    _VOID = {"hr", "img", "br", "meta", "link", "input"}

    def __init__(self) -> None:
        super().__init__()
        self._stack: list[tuple[str, str | None]] = []
        self.section_regions: dict[str, str | None] = {}

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self._VOID:
            return
        attrs = dict(attrs)
        region = attrs.get("data-region") if tag == "div" else None
        self._stack.append((tag, region))
        if tag == "section":
            enclosing: str | None = None
            for _, region_id in reversed(self._stack[:-1]):
                if region_id:
                    enclosing = region_id
                    break
            self.section_regions[attrs.get("data-section")] = enclosing

    def handle_endtag(self, tag: str) -> None:
        if tag in self._VOID:
            return
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index][0] == tag:
                del self._stack[index:]
                return


def _section_regions(html: str) -> dict[str, str | None]:
    parser = _StructureParser()
    parser.feed(html)
    parser.close()
    return parser.section_regions


def _body_text(html: str) -> str:
    without_style = re.sub(r"<style.*?</style>", "", html, flags=re.S)
    stripped = re.sub(r"<[^>]+>", " ", without_style)
    return " ".join(stripped.split())


def _tokens(html: str) -> Counter:
    return Counter(_body_text(html).split())


@pytest.fixture
def client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _save_resume() -> str:
    resume_id = uuid.uuid4().hex
    resume = Resume(
        user_id="test",
        full_name="Jane Doe",
        email="jane@test.com",
        summary="Full-stack engineer with 8 years building platforms.",
        experience=[
            ResumeExperience(company="Acme", title="Senior Engineer", start_date="2016", current=True),
            ResumeExperience(company="Beta Inc", title="Engineer", start_date="2014", end_date="2016"),
            ResumeExperience(company="Gamma", title="Junior Engineer", start_date="2012", end_date="2014"),
        ],
        education=[ResumeEducation(institution="MIT", degree="B.Sc.", field="Computer Science")],
        skills=[ResumeSkill(category="Languages", skills=["Python", "Go"])],
        certifications=[ResumeCertification(name="AWS Certified", issuer="Amazon")],
    )
    save_resume(resume_id, resume)
    return resume_id


async def _preview(client: AsyncClient, resume_id: str, **params) -> tuple[dict, str]:
    url = f"/api/v1/resume/{resume_id}/preview"
    if params:
        url += "?" + "&".join(f"{key}={value}" for key, value in params.items())
    response = await client.get(url)
    body = response.json()
    assert response.status_code == 200, body
    file_response = await client.get(body["data"]["preview_url"])
    return body, file_response.text


# ── A: new layout preview ─────────────────────────────────────────────────────


class TestLayoutPreview:
    async def test_layout_preview_returns_layout_html(self, client):
        resume_id = _save_resume()
        body, html = await _preview(client, resume_id, layout_id="sidebar", theme="blue")
        assert body["data"]["mode"] == "layout"
        assert body["data"]["layout_id"] == "sidebar"
        assert 'data-region="sidebar"' in html
        assert "Jane Doe" in _body_text(html)


# ── B/C: same resume + different layout → different structure, same content ───


class TestLayoutChangesStructure:
    async def test_layouts_produce_different_structures_same_content(self, client):
        resume_id = _save_resume()
        results = {}
        for layout in LAYOUTS:
            _, html = await _preview(client, resume_id, layout_id=layout, theme="blue")
            results[layout] = html

        for layout in LAYOUTS:
            assert "skills" in _section_regions(results[layout])

        # Structure differs by layout.
        assert _section_regions(results["executive"])["skills"] == "main"
        assert _section_regions(results["sidebar"])["skills"] == "sidebar"
        assert _section_regions(results["modern"])["skills"] == "secondary"
        assert _section_regions(results["classic"])["skills"] == "main"

        # Content identical across layouts.
        counters = [_tokens(results[layout]) for layout in LAYOUTS]
        assert counters[0] == counters[1] == counters[2] == counters[3]
        for layout in LAYOUTS:
            body = _body_text(results[layout])
            assert "Jane Doe" in body
            assert "Senior Engineer — Acme (2016 – Present)" in body
            assert "Engineer — Beta Inc (2014 – 2016)" in body
            assert "Junior Engineer — Gamma (2012 – 2014)" in body


# ── D: theme changes appearance, not structure ────────────────────────────────


class TestThemeSeparation:
    async def test_theme_changes_tokens_not_structure(self, client):
        resume_id = _save_resume()
        _, blue_html = await _preview(client, resume_id, layout_id="sidebar", theme="blue")
        _, gold_html = await _preview(client, resume_id, layout_id="sidebar", theme="gold")

        assert _section_regions(blue_html) == _section_regions(gold_html)
        assert "--primary: #2563eb" in blue_html
        assert "--primary: #b98a2f" in gold_html


# ── E: legacy preview compatibility ───────────────────────────────────────────


class TestLegacyCompatibility:
    async def test_legacy_template_preview_still_works(self, client):
        resume_id = _save_resume()
        response = await client.get(f"/api/v1/resume/{resume_id}/preview?template_id=executive")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert "mode" not in body["data"]  # legacy shape unchanged
        file_response = await client.get(body["data"]["preview_url"])
        assert file_response.status_code == 200
        legacy_html = file_response.text
        assert "Jane Doe" in legacy_html
        # Legacy output uses the legacy structure, not the new engine regions.
        assert "data-region" not in legacy_html


# ── F/G: error handling ───────────────────────────────────────────────────────


class TestErrors:
    async def test_unknown_layout_returns_404(self, client):
        resume_id = _save_resume()
        response = await client.get(f"/api/v1/resume/{resume_id}/preview?layout_id=nope")
        assert response.status_code == 404
        assert "Layout 'nope' not found" in response.json()["detail"]

    async def test_unknown_resume_returns_404(self, client):
        response = await client.get("/api/v1/resume/nonexistent/preview?layout_id=sidebar")
        assert response.status_code == 404
        assert "Resume not found" in response.json()["detail"]


# ── H: determinism ────────────────────────────────────────────────────────────


class TestDeterminism:
    async def test_same_request_reuses_cache(self, client):
        resume_id = _save_resume()
        first, html_first = await _preview(client, resume_id, layout_id="sidebar", theme="blue")
        second, html_second = await _preview(client, resume_id, layout_id="sidebar", theme="blue")
        assert first["data"]["preview_url"] == second["data"]["preview_url"]
        assert html_first == html_second


# ── I: CSP/iframe for the new preview files ───────────────────────────────────


class TestCSPIframe:
    async def test_layout_preview_file_allows_framing(self, client):
        resume_id = _save_resume()
        body, _ = await _preview(client, resume_id, layout_id="modern", theme="blue")
        file_response = await client.get(body["data"]["preview_url"])
        csp = file_response.headers.get("content-security-policy", "")
        assert "frame-ancestors" in csp
        assert "http://127.0.0.1:5173" in csp
        assert file_response.headers.get("x-frame-options") != "DENY"


# ── Preview file security (path containment) ──────────────────────────────────


class TestPreviewFileSecurity:
    async def test_preview_file_rejects_directory_and_traversal_names(self, client):
        # A directory-resolving name and traversal attempts must not be served.
        for bad in ("..", "%2e%2e", "..%2F..%2F..%2Fetc%2Fpasswd", "%2e%2e%2f%2e%2e"):
            response = await client.get(f"/api/v1/resume/preview/file/{bad}")
            assert response.status_code == 404, f"{bad} -> {response.status_code}"

    async def test_valid_preview_file_still_served(self, client):
        resume_id = _save_resume()
        body, html = await _preview(client, resume_id, layout_id="executive", theme="blue")
        assert 'data-region="main"' in html
