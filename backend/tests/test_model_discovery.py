"""Regression tests: model discovery returns unique canonical ids.

The upstream OmniRoute model catalog can list the same canonical model id more
than once; the collection exposed to clients (and ultimately the React admin
model list, which keys on ``model.id``) must contain each canonical id exactly
once while preserving distinct provider/model identities.
"""

from app.services.admin_service import _dedupe_models, discover_models

DUPLICATED_IDS = [
    "gemini/gemini-2.5-flash-native-audio-latest",
    "gemini/gemini-2.5-flash-native-audio-preview-09-2025",
    "gemini/gemini-2.5-flash-native-audio-preview-12-2025",
    "gemini/gemini-3.1-flash-live-preview",
    "gemini/gemini-3.5-live-translate-preview",
    "veo-free/seedance",
    "veo-free/veo",
]


def _model(model_id: str, owned_by: str = "provider") -> dict:
    return {"id": model_id, "object": "model", "owned_by": owned_by}


class TestDedupeModels:
    def test_duplicate_ids_removed_deterministically(self):
        upstream = [_model(model_id) for model_id in DUPLICATED_IDS * 2]
        result = _dedupe_models(upstream)
        ids = [model["id"] for model in result]
        assert len(ids) == len(DUPLICATED_IDS)
        assert len(set(ids)) == len(DUPLICATED_IDS)
        # First occurrence per id is preserved (deterministic order).
        assert ids == DUPLICATED_IDS

    def test_distinct_provider_models_preserved(self):
        upstream = [
            _model("provider-a/model-1", "provider-a"),
            _model("provider-b/model-2", "provider-b"),
            _model("provider-a/model-1", "provider-a"),
        ]
        result = _dedupe_models(upstream)
        assert [model["id"] for model in result] == ["provider-a/model-1", "provider-b/model-2"]
        # Different provider/model identities remain distinct.
        assert result[1]["owned_by"] == "provider-b"

    def test_empty_and_missing_id(self):
        assert _dedupe_models([]) == []
        assert _dedupe_models([{"object": "model"}]) == []


class TestDiscoverModels:
    async def test_discover_models_deduplicates_upstream(self, monkeypatch):
        class FakeResponse:
            def raise_for_status(self) -> None:
                pass

            def json(self) -> dict:
                return {"data": [_model(model_id) for model_id in DUPLICATED_IDS * 2]}

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args) -> bool:
                return False

            async def get(self, url: str) -> FakeResponse:
                return FakeResponse()

        monkeypatch.setattr(
            "app.services.admin_service.httpx.AsyncClient",
            lambda timeout: FakeClient(),
        )
        result = await discover_models()
        ids = [model["id"] for model in result]
        assert len(ids) == len(set(ids)) == len(DUPLICATED_IDS)

    async def test_discover_models_returns_empty_on_error(self, monkeypatch):
        class FailingClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args) -> bool:
                return False

            async def get(self, url: str):
                raise RuntimeError("boom")

        monkeypatch.setattr(
            "app.services.admin_service.httpx.AsyncClient",
            lambda timeout: FailingClient(),
        )
        assert await discover_models() == []
