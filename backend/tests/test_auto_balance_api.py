"""P3.9 API tests — Auto-balance preview, export, and parity.

Verifies the precedence (request-explicit > auto_balance > persisted > base) and
that preview and export select the identical effective layout + density.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.resume import (
    Award,
    Certification,
    Education,
    Experience,
    Language,
    Project,
    Resume,
    Skill,
)
from app.rendering.content import cvm_from_resume
from app.rendering.content_analyzer import ContentAnalyzer
from app.rendering.layout.layout_balancer import LayoutBalancer
from app.services.storage_service import save_resume


@pytest.fixture
def client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _save_resume_long(user_id="test") -> str:
    """Persist a content-heavy resume that triggers a two-column recommendation."""
    resume_id = uuid.uuid4().hex
    experiences = [
        Experience(
            company=f"Company {i}",
            title=f"Engineer {i}",
            start_date="2020",
            end_date="2023",
            description=["Did work", "More work"],
        )
        for i in range(10)
    ]
    resume = Resume(
        user_id=user_id,
        full_name="Jane Doe",
        email="jane@test.com",
        professional_title="Senior Engineer",
        summary="Very long summary " * 20,
        experience=experiences,
        education=[Education(institution="MIT", degree="BS", field="CS", start_date="2016", end_date="2020")],
        skills=[Skill(category="Languages", skills=["Python", "Go", "Rust"])],
        projects=[
            Project(name=f"Project {i}", description="Desc", url="https://example.com", technologies=["Python"])
            for i in range(5)
        ],
        certifications=[Certification(name=f"Cert {i}", issuer="Org", date="2022") for i in range(3)],
        awards=[Award(name=f"Award {i}", issuer="Org", date="2022") for i in range(2)],
        languages=[
            Language(name="English", proficiency="Native"),
            Language(name="Spanish", proficiency="Professional"),
        ],
    )
    save_resume(resume_id, resume)
    return resume_id


async def _preview(client: AsyncClient, rid: str, **params) -> tuple[dict, str]:
    resp = await client.get(f"/api/v1/resume/{rid}/preview", params=params)
    body = resp.json()
    assert resp.status_code == 200, body
    file_resp = await client.get(body["data"]["preview_url"])
    assert file_resp.status_code == 200
    return body, file_resp.text


class TestAutoBalancePreview:
    async def test_auto_balanced_preview_succeeds(self, client):
        rid = _save_resume_long()
        resp = await client.get(
            f"/api/v1/resume/{rid}/preview", params={"layout_id": "sidebar", "auto_balance": "true"}
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["preview_url"]

    async def test_auto_balanced_preview_uses_balanced_layout(self, client):
        rid = _save_resume_long()
        _, html = await _preview(client, rid, layout_id="sidebar", auto_balance="true")
        # Long content -> two-column recommendation -> sidebar region present.
        assert 'data-region="sidebar"' in html

    async def test_auto_balanced_preview_seeds_persisted_density(self, client):
        # Persist a spacious config; auto_balance seeds it (density survives).
        rid = _save_resume_long()
        await client.put(
            f"/api/v1/resume/{rid}/layout-config", json={"config": {"mode": "single", "density": "spacious"}}
        )
        _, html = await _preview(client, rid, layout_id="sidebar", auto_balance="true")
        assert "density-spacious" in html  # persisted density seeded into balanced layout

    async def test_auto_balanced_preview_preserves_url_and_file(self, client):
        rid = _save_resume_long()
        body, html = await _preview(client, rid, layout_id="sidebar", auto_balance="true")
        assert body["data"]["preview_url"].endswith(".html")
        assert html.strip()

    async def test_explicit_config_bypasses_balancing(self, client):
        rid = _save_resume_long()
        _, html = await _preview(
            client,
            rid,
            layout_id="sidebar",
            layout_config='{"mode":"single","density":"normal"}',
        )
        # Explicit single-column config wins over balancing for long content.
        assert 'data-region="sidebar"' not in html

    async def test_persisted_config_overridden_only_when_auto_balance(self, client):
        rid = _save_resume_long()
        await client.put(
            f"/api/v1/resume/{rid}/layout-config",
            json={"config": {"mode": "single", "density": "spacious"}},
        )
        # Without auto_balance -> persisted (single, spacious).
        _, html_off = await _preview(client, rid, layout_id="sidebar")
        assert 'data-region="sidebar"' not in html_off
        assert "density-spacious" in html_off
        # With auto_balance -> layout (mode) is balanced to two-column, but the
        # persisted density is seeded into the balanced recommendation.
        _, html_on = await _preview(client, rid, layout_id="sidebar", auto_balance="true")
        assert 'data-region="sidebar"' in html_on  # balancer overrode persisted single-column mode
        assert "density-spacious" in html_on  # persisted density preserved via seeding


class TestAutoBalanceExport:
    async def test_auto_balanced_export_with_persisted_config(self, client):
        # Case 12: persisted config present, auto_balance -> balanced, not persisted.
        rid = _save_resume_long()
        await client.put(
            f"/api/v1/resume/{rid}/layout-config",
            json={"config": {"mode": "single", "density": "spacious"}},
        )
        resp = await client.post(
            f"/api/v1/resume/{rid}/export",
            json={"layout_id": "sidebar", "theme_id": "blue", "format": "html", "auto_balance": True},
        )
        assert resp.status_code == 200, resp.json()
        html = resp.text
        assert 'data-region="sidebar"' in html  # balanced two-column (overrides persisted single)
        assert "density-spacious" in html  # persisted density seeded into balanced layout

    async def test_auto_balanced_export_uses_correct_density_html(self, client):
        rid = _save_resume_long()
        resp = await client.post(
            f"/api/v1/resume/{rid}/export",
            json={"layout_id": "sidebar", "theme_id": "blue", "format": "html", "auto_balance": True},
        )
        assert resp.status_code == 200
        # Balanced density is "normal" -> no density-* class emitted.
        assert "density-spacious" not in resp.text
        assert "density-compact" not in resp.text

    async def test_auto_balanced_export_docx_density_none(self, client):
        # Case 14: DOCX retains existing density=None behavior.
        rid = _save_resume_long()
        resp = await client.post(
            f"/api/v1/resume/{rid}/export",
            json={"layout_id": "sidebar", "theme_id": "blue", "format": "docx", "auto_balance": True},
        )
        assert resp.status_code == 200
        assert resp.content


class TestAutoBalanceParity:
    async def test_preview_and_export_same_effective_layout_and_density(self, client):
        # Cases 15/16: identical inputs -> identical effective layout + density.
        rid = _save_resume_long()
        _, preview_html = await _preview(client, rid, layout_id="sidebar", auto_balance="true")
        export_resp = await client.post(
            f"/api/v1/resume/{rid}/export",
            json={"layout_id": "sidebar", "theme_id": "blue", "format": "html", "auto_balance": True},
        )
        assert export_resp.status_code == 200
        export_html = export_resp.text

        # Both resolve to the balanced two-column layout.
        assert 'data-region="sidebar"' in preview_html
        assert 'data-region="sidebar"' in export_html
        # Both use the balanced (normal) density.
        assert "density-spacious" not in preview_html
        assert "density-spacious" not in export_html
        assert "density-compact" not in preview_html
        assert "density-compact" not in export_html


class TestAutoBalanceRationale:
    """P3.11 — surface the deterministic balancing rationale to the preview response."""

    async def test_auto_balance_false_has_no_rationale(self, client):
        rid = _save_resume_long()
        body, _ = await _preview(client, rid, layout_id="sidebar")
        assert "layout_rationale" not in body["data"]
        assert "auto_balance" not in body["data"]
        assert "balanced_layout" not in body["data"]

    async def test_auto_balance_true_returns_rationale(self, client):
        rid = _save_resume_long()
        body, _ = await _preview(client, rid, layout_id="sidebar", auto_balance="true")
        assert body["data"]["auto_balance"] is True
        assert isinstance(body["data"]["layout_rationale"], str)
        assert body["data"]["layout_rationale"].strip()
        assert body["data"]["balanced_layout"]["mode"] == "two_column"
        assert "ratio" in body["data"]["balanced_layout"]
        assert "sidebar" in body["data"]["balanced_layout"]

    async def test_rationale_matches_balance_result(self, client):
        # The rationale + balanced metadata must match the deterministic
        # LayoutBalanceResult for the same resume content (no fabricated text).
        rid = _save_resume_long()
        body, _ = await _preview(client, rid, layout_id="sidebar", auto_balance="true")
        from app.rendering import layout_preview
        from app.services.repositories.factory import get_resume_repository

        resume = get_resume_repository().get_by_id(rid, "test")
        cvm = cvm_from_resume(resume)
        base = layout_preview.resolve_preview_layout("sidebar", None)
        analysis = ContentAnalyzer().analyze(cvm)
        expected = LayoutBalancer().balance(analysis, base)
        assert body["data"]["layout_rationale"] == expected.rationale
        assert body["data"]["balanced_layout"] == {
            "mode": expected.config.mode.value,
            "ratio": expected.config.ratio.value,
            "sidebar": expected.config.sidebar.value,
        }

    async def test_existing_preview_url_unchanged_with_rationale(self, client):
        rid = _save_resume_long()
        body, html = await _preview(client, rid, layout_id="sidebar", auto_balance="true")
        # Preview URL + served file are unaffected by the added rationale fields.
        assert body["data"]["preview_url"].endswith(".html")
        assert html.strip()
        assert 'data-region="sidebar"' in html  # still the balanced layout
