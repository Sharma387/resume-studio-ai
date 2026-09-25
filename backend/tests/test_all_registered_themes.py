"""Production hardening: every registered theme renders and exports cleanly.

Themes are enumerated from the ACTUAL registry (``/resume/themes``) — no
hardcoded assumptions about theme ids. For every registered theme we verify
theme tokens are applied to the output (colors differ), structure is theme-
independent, preview/export succeed, and unknown themes produce a controlled
404 — never a fallback to a default.
"""

import re
import uuid
from html.parser import HTMLParser
from io import BytesIO

import pytest
from httpx import ASGITransport, AsyncClient
from pypdf import PdfReader

from app.main import app
from app.models.resume import Resume
from app.rendering.theme.reference_themes import REFERENCE_THEMES
from app.services.storage_service import save_resume

REGISTERED_THEME_IDS = tuple(theme.theme_id for theme in REFERENCE_THEMES)
DEFAULT_THEME_ID = REGISTERED_THEME_IDS[0]


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


def _body_text(html: str) -> str:
    without_style = re.sub(r"<style.*?</style>", "", html, flags=re.S)
    stripped = re.sub(r"<[^>]+>", " ", without_style)
    return " ".join(stripped.split())


def _pdf_text(data: bytes) -> str:
    return " ".join((page.extract_text() or "") for page in PdfReader(BytesIO(data)).pages)


def _docx_joined(data: bytes) -> str:
    from docx import Document

    doc = Document(BytesIO(data))
    parts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                parts.append(cell.text)
    return "\n".join(parts)


def _primary_color(theme_id: str) -> str:
    for theme in REFERENCE_THEMES:
        if theme.theme_id == theme_id:
            return theme.tokens.colors.primary
    raise AssertionError(f"theme {theme_id!r} not registered")


@pytest.fixture
def client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _save_resume() -> str:
    resume_id = uuid.uuid4().hex
    resume = Resume(
        user_id="dev-user",
        full_name="Jane Doe",
        email="jane@test.com",
        professional_title="Senior Software Engineer",
        summary="Full-stack engineer with 8 years building platforms.",
        experience=[{"company": "Acme", "title": "Senior Engineer", "start_date": "2016", "current": True}],
        education=[{"institution": "MIT", "degree": "B.Sc.", "field": "Computer Science"}],
        skills=[{"category": "Languages", "skills": ["Python", "Go"]}],
    )
    save_resume(resume_id, resume)
    return resume_id


async def _preview(client: AsyncClient, resume_id: str, **params) -> tuple[dict, str]:
    url = f"/api/v1/resume/{resume_id}/preview"
    if params:
        url += "?" + "&".join(f"{key}={value}" for key, value in params.items())
    response = await client.get(url)
    body = response.json()
    assert response.status_code == 200, (params, body)
    file_response = await client.get(body["data"]["preview_url"])
    assert file_response.status_code == 200
    return body, file_response.text


async def _export(client: AsyncClient, resume_id: str, body: dict) -> tuple[int, bytes]:
    response = await client.post(f"/api/v1/resume/{resume_id}/export", json=body)
    return response.status_code, response.content


@pytest.mark.asyncio
async def test_registry_lists_all_reference_themes(client):
    response = await client.get("/api/v1/resume/themes")
    assert response.status_code == 200
    ids = {item["theme_id"] for item in response.json()["data"]}
    assert ids == set(REGISTERED_THEME_IDS)
    assert len(ids) >= 2


@pytest.mark.asyncio
async def test_every_registered_theme_previews_and_exports(client):
    resume_id = _save_resume()
    for theme_id in REGISTERED_THEME_IDS:
        # Preview: 200 + theme tokens actually applied.
        _, html = await _preview(client, resume_id, layout_id="sidebar", theme=theme_id)
        assert f"--primary: {_primary_color(theme_id)}" in html, theme_id
        assert "Jane Doe" in _body_text(html)

        # Export: valid artifacts with resume content across all three formats.
        for fmt in ("pdf", "docx", "html"):
            status, content = await _export(
                client, resume_id, {"layout_id": "sidebar", "theme_id": theme_id, "format": fmt}
            )
            assert status == 200, (theme_id, fmt)
            if fmt == "pdf":
                assert content[:5] == b"%PDF-"
                assert "Jane Doe" in _pdf_text(content)
            elif fmt == "docx":
                assert content[:2] == b"PK"
                assert "Jane Doe" in _docx_joined(content)
            else:
                assert f"--primary: {_primary_color(theme_id)}" in content.decode("utf-8")
                assert "Jane Doe" in content.decode("utf-8")


@pytest.mark.asyncio
async def test_themes_change_tokens_not_structure(client):
    resume_id = _save_resume()
    _, blue_html = await _preview(client, resume_id, layout_id="sidebar", theme="blue")
    _, gold_html = await _preview(client, resume_id, layout_id="sidebar", theme="gold")
    blue_parser = _StructureParser()
    blue_parser.feed(blue_html)
    gold_parser = _StructureParser()
    gold_parser.feed(gold_html)
    assert blue_parser.section_regions == gold_parser.section_regions
    assert _primary_color("blue") != _primary_color("gold")
    assert f"--primary: {_primary_color('blue')}" in blue_html
    assert f"--primary: {_primary_color('gold')}" in gold_html


@pytest.mark.asyncio
async def test_unknown_theme_404_preview_and_export(client):
    resume_id = _save_resume()
    response = await client.get(f"/api/v1/resume/{resume_id}/preview?layout_id=sidebar&theme=no_such_theme")
    assert response.status_code == 404
    assert "Theme" in response.json()["detail"]
    for fmt in ("pdf", "docx", "html"):
        status, _ = await _export(
            client, resume_id, {"layout_id": "sidebar", "theme_id": "no_such_theme", "format": fmt}
        )
        assert status == 404, fmt


@pytest.mark.asyncio
async def test_preview_defaults_to_first_registered_theme(client):
    resume_id = _save_resume()
    body, html = await _preview(client, resume_id, layout_id="sidebar")
    assert body["data"]["preview_url"]
    assert f"--primary: {_primary_color(DEFAULT_THEME_ID)}" in html
