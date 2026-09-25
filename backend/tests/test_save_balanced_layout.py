"""P3.12 — Save the auto-balanced layout as the persisted LayoutConfig.

The user explicitly persists the effective balanced LayoutConfig (not the
LayoutDefinition, not the rationale) via the existing PUT /layout-config
endpoint. Verifies precedence/preview/export parity are unaffected.
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
from app.services.storage_service import save_resume


@pytest.fixture
def client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _save_resume_long(user_id="dev-user") -> str:
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


async def _preview_body(client: AsyncClient, rid: str, **params) -> dict:
    resp = await client.get(f"/api/v1/resume/{rid}/preview", params=params)
    assert resp.status_code == 200, resp.json()
    return resp.json()["data"]


class TestSaveBalancedLayout:
    async def test_preview_exposes_balanced_config(self, client):
        rid = _save_resume_long()
        data = await _preview_body(client, rid, layout_id="sidebar", auto_balance="true")
        assert "balanced_config" in data
        cfg = data["balanced_config"]
        assert cfg["mode"] == "two_column"
        assert "ratio" in cfg and "sidebar" in cfg

    async def test_no_balanced_config_when_auto_balance_off(self, client):
        rid = _save_resume_long()
        data = await _preview_body(client, rid, layout_id="sidebar")
        assert "balanced_config" not in data

    async def test_save_balanced_layout_persists(self, client):
        rid = _save_resume_long()
        data = await _preview_body(client, rid, layout_id="sidebar", auto_balance="true")
        balanced = data["balanced_config"]
        resp = await client.put(f"/api/v1/resume/{rid}/layout-config", json={"config": balanced})
        assert resp.status_code == 200, resp.json()
        stored = resp.json()["data"]["layout_config"]
        assert stored["mode"] == balanced["mode"]
        assert stored["ratio"] == balanced["ratio"]
        assert stored["sidebar"] == balanced["sidebar"]

    async def test_saved_config_has_balance_fields(self, client):
        rid = _save_resume_long()
        balanced = (await _preview_body(client, rid, layout_id="sidebar", auto_balance="true"))["balanced_config"]
        await client.put(f"/api/v1/resume/{rid}/layout-config", json={"config": balanced})
        stored = (await client.get(f"/api/v1/resume/{rid}/layout-config")).json()["data"]["layout_config"]
        assert stored["mode"] == "two_column"
        assert stored["ratio"] == balanced["ratio"]
        assert stored["sidebar"] == balanced["sidebar"]

    async def test_saved_config_preserves_density_gap_sections(self, client):
        rid = _save_resume_long()
        await client.put(
            f"/api/v1/resume/{rid}/layout-config",
            json={
                "config": {
                    "mode": "single",
                    "density": "spacious",
                    "gap": "wide",
                    "sections": {"summary": {"order": 5}},
                }
            },
        )
        balanced = (await _preview_body(client, rid, layout_id="sidebar", auto_balance="true"))["balanced_config"]
        assert balanced["density"] == "spacious"
        assert balanced["gap"] == "wide"
        assert "sections" in balanced
        await client.put(f"/api/v1/resume/{rid}/layout-config", json={"config": balanced})
        stored = (await client.get(f"/api/v1/resume/{rid}/layout-config")).json()["data"]["layout_config"]
        assert stored["density"] == "spacious"
        assert stored["gap"] == "wide"
        assert stored["mode"] == "two_column"  # balancer overrode persisted single-column mode

    async def test_rationale_not_persisted(self, client):
        rid = _save_resume_long()
        data = await _preview_body(client, rid, layout_id="sidebar", auto_balance="true")
        assert "layout_rationale" in data  # rationale surfaced in preview only
        balanced = data["balanced_config"]
        assert "layout_rationale" not in balanced
        await client.put(f"/api/v1/resume/{rid}/layout-config", json={"config": balanced})
        stored = (await client.get(f"/api/v1/resume/{rid}/layout-config")).json()["data"]["layout_config"]
        assert "layout_rationale" not in stored
        assert "balanced_layout" not in stored

    async def test_layout_definition_not_persisted(self, client):
        rid = _save_resume_long()
        balanced = (await _preview_body(client, rid, layout_id="sidebar", auto_balance="true"))["balanced_config"]
        await client.put(f"/api/v1/resume/{rid}/layout-config", json={"config": balanced})
        stored = (await client.get(f"/api/v1/resume/{rid}/layout-config")).json()["data"]["layout_config"]
        allowed = {"mode", "sidebar", "ratio", "density", "gap", "sections"}
        assert set(stored.keys()) <= allowed
        assert "grid" not in stored and "regions" not in stored and "metadata" not in stored

    async def test_save_failure_keeps_existing_config(self, client):
        rid = _save_resume_long()
        balanced = (await _preview_body(client, rid, layout_id="sidebar", auto_balance="true"))["balanced_config"]
        await client.put(f"/api/v1/resume/{rid}/layout-config", json={"config": balanced})
        bad = await client.put(f"/api/v1/resume/{rid}/layout-config", json={"config": {"mode": "bogus"}})
        assert bad.status_code == 422
        stored = (await client.get(f"/api/v1/resume/{rid}/layout-config")).json()["data"]["layout_config"]
        assert stored["mode"] == "two_column"  # unchanged from the valid save

    async def test_after_save_auto_balance_off_uses_saved(self, client):
        rid = _save_resume_long()
        balanced = (await _preview_body(client, rid, layout_id="sidebar", auto_balance="true"))["balanced_config"]
        await client.put(f"/api/v1/resume/{rid}/layout-config", json={"config": balanced})
        data = await _preview_body(client, rid, layout_id="sidebar")
        assert "balanced_config" not in data  # no new balance, uses saved
        file_resp = await client.get(data["preview_url"])
        assert file_resp.status_code == 200
        assert 'data-region="sidebar"' in file_resp.text  # saved two-column config applied
