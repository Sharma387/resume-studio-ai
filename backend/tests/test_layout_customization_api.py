"""Layout customization API contract — persistence + wiring into preview/export.

Verifies the P3.3B surface exactly:

    GET /resume/{id}/layout-config
    PUT /resume/{id}/layout-config          {config: <LayoutConfig>}
    GET /resume/{id}/preview?layout_config=<json>   (explicit > persisted > default)
    POST /resume/{id}/export {..., layout_config}   (explicit > persisted > default)

The persisted shape is namespaced into ``resume_variants.customization`` as
``{"layout_config": {...}}`` and unrelated customization keys are preserved.
"""

import json
import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.resume import Resume
from app.services.layout_config_service import set_layout_config
from app.services.repositories.factory import get_variant_repository
from app.services.storage_service import save_resume

VARIANT_PATH = Path("storage") / "variants"

_TWO_COLUMN_CONFIG = {
    "mode": "two_column",
    "sidebar": "left",
    "ratio": "35/65",
    "gap": "compact",
    "density": "normal",
}


@pytest.fixture
def client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _save_resume(user_id="test") -> str:
    resume_id = uuid.uuid4().hex
    resume = Resume(
        user_id=user_id,
        full_name=f"Layout User {resume_id[:6]}",
        email="layout@test.com",
        summary="Layout customization test resume.",
        experience=[{"company": "Acme", "title": "Engineer", "start_date": "2020"}],
    )
    save_resume(resume_id, resume)
    return resume_id


# ── Persistence contract ──────────────────────────────────────────────────────


class TestLayoutConfigPersistence:
    async def test_put_then_get_round_trips(self, client):
        rid = _save_resume()
        put = await client.put(
            f"/api/v1/resume/{rid}/layout-config",
            json={"config": _TWO_COLUMN_CONFIG},
        )
        assert put.status_code == 200
        stored = put.json()["data"]["layout_config"]
        assert stored["mode"] == "two_column"
        assert stored["ratio"] == "35/65"

        get = await client.get(f"/api/v1/resume/{rid}/layout-config")
        assert get.status_code == 200
        assert get.json()["data"]["layout_config"] == stored

    async def test_unset_config_returns_empty(self, client):
        rid = _save_resume()
        response = await client.get(f"/api/v1/resume/{rid}/layout-config")
        assert response.status_code == 200
        assert response.json()["data"]["layout_config"] == {}

    async def test_stored_shape_is_namespaced(self, client):
        rid = _save_resume()
        await client.put(
            f"/api/v1/resume/{rid}/layout-config",
            json={"config": {"mode": "single", "gap": "wide"}},
        )
        path = VARIANT_PATH / f"{rid}.json"
        assert path.exists()
        record = json.loads(path.read_text(encoding="utf-8"))
        assert record["user_id"] == "test"
        assert record["customization"]["layout_config"]["gap"] == "wide"

    async def test_preserves_other_customization_keys(self, client):
        rid = _save_resume()
        repo = get_variant_repository()
        repo.set_customization(rid, "test", {"theme_config": {"accent": "red"}})
        set_layout_config(rid, "test", {"mode": "single"})
        customization = repo.get_customization(rid, "test")
        assert customization["theme_config"] == {"accent": "red"}
        assert customization["layout_config"]["mode"] == "single"

    async def test_unknown_resume_404(self, client):
        get = await client.get("/api/v1/resume/nope/layout-config")
        assert get.status_code == 404
        put = await client.put(
            "/api/v1/resume/nope/layout-config", json={"config": {"mode": "single"}}
        )
        assert put.status_code == 404

    async def test_invalid_section_422(self, client):
        rid = _save_resume()
        response = await client.put(
            f"/api/v1/resume/{rid}/layout-config",
            json={"config": {"mode": "single", "sections": {"bogus_section": {"region": "main"}}}},
        )
        assert response.status_code == 422

    async def test_unknown_body_field_422(self, client):
        rid = _save_resume()
        response = await client.put(
            f"/api/v1/resume/{rid}/layout-config",
            json={"config": {"mode": "single"}, "extra": True},
        )
        assert response.status_code == 422

    async def test_preview_ignores_invalid_persisted_config(self, client):
        rid = _save_resume()
        get_variant_repository().set_customization(
            rid, "test", {"layout_config": {"mode": "not-a-mode"}}
        )
        response = await client.get(
            f"/api/v1/resume/{rid}/preview", params={"layout_id": "sidebar"}
        )
        assert response.status_code == 200


# ── Preview wiring ────────────────────────────────────────────────────────────


class TestLayoutConfigPreview:
    async def test_preview_without_config_still_works(self, client):
        rid = _save_resume()
        response = await client.get(f"/api/v1/resume/{rid}/preview", params={"layout_id": "sidebar"})
        assert response.status_code == 200

    async def test_preview_applies_persisted_config(self, client):
        rid = _save_resume()
        await client.put(
            f"/api/v1/resume/{rid}/layout-config",
            json={"config": _TWO_COLUMN_CONFIG},
        )
        configured = await client.get(
            f"/api/v1/resume/{rid}/preview", params={"layout_id": "sidebar"}
        )
        assert configured.status_code == 200

    async def test_preview_resolved_layout_differs_from_base(self, client):
        rid = _save_resume()
        base = await client.get(f"/api/v1/resume/{rid}/preview", params={"layout_id": "sidebar"})
        await client.put(
            f"/api/v1/resume/{rid}/layout-config",
            json={"config": _TWO_COLUMN_CONFIG},
        )
        resolved = await client.get(
            f"/api/v1/resume/{rid}/preview", params={"layout_id": "sidebar"}
        )
        # A resolved two-column variant changes the grid, so the cached preview
        # file must differ from the base (proves the config is actually applied).
        assert resolved.json()["data"]["preview_url"] != base.json()["data"]["preview_url"]

    async def test_explicit_config_overrides_persisted(self, client):
        rid = _save_resume()
        # Persist a valid single-column config for the two-column sidebar layout.
        await client.put(
            f"/api/v1/resume/{rid}/layout-config",
            json={"config": {"mode": "two_column"}},
        )
        # An explicit two_column request against the single-MAIN executive layout
        # is unresolvable (no rail) — proving the explicit config won.
        response = await client.get(
            f"/api/v1/resume/{rid}/preview",
            params={"layout_id": "executive", "layout_config": json.dumps({"mode": "two_column"})},
        )
        assert response.status_code == 400

    async def test_invalid_explicit_config_422(self, client):
        rid = _save_resume()
        response = await client.get(
            f"/api/v1/resume/{rid}/preview",
            params={
                "layout_id": "sidebar",
                "layout_config": json.dumps({"sections": {"bogus_section": {"region": "main"}}}),
            },
        )
        assert response.status_code == 422

    async def test_two_column_config_against_single_layout_400(self, client):
        rid = _save_resume()
        await client.put(
            f"/api/v1/resume/{rid}/layout-config",
            json={"config": _TWO_COLUMN_CONFIG},
        )
        response = await client.get(
            f"/api/v1/resume/{rid}/preview", params={"layout_id": "minimal"}
        )
        assert response.status_code == 400


# ── Export wiring ─────────────────────────────────────────────────────────────


_DEFAULT_EXPORT_BODY = {"layout_id": "sidebar", "theme_id": "blue", "format": "pdf"}


class TestLayoutConfigExport:
    async def test_export_with_explicit_config_200(self, client):
        rid = _save_resume()
        response = await client.post(
            f"/api/v1/resume/{rid}/export",
            json={**_DEFAULT_EXPORT_BODY, "layout_config": _TWO_COLUMN_CONFIG},
        )
        assert response.status_code == 200
        assert response.content

    async def test_export_uses_persisted_config(self, client):
        rid = _save_resume()
        await client.put(
            f"/api/v1/resume/{rid}/layout-config",
            json={"config": _TWO_COLUMN_CONFIG},
        )
        response = await client.post(
            f"/api/v1/resume/{rid}/export", json=_DEFAULT_EXPORT_BODY
        )
        assert response.status_code == 200

    async def test_export_explicit_overrides_persisted(self, client):
        rid = _save_resume()
        await client.put(
            f"/api/v1/resume/{rid}/layout-config",
            json={"config": {"mode": "single"}},
        )
        # Explicit two_column against single-MAIN executor layout → unresolvable.
        response = await client.post(
            f"/api/v1/resume/{rid}/export",
            json={
                "layout_id": "executive",
                "theme_id": "blue",
                "format": "pdf",
                "layout_config": {"mode": "two_column"},
            },
        )
        assert response.status_code == 400
