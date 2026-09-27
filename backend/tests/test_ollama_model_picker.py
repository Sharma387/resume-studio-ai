"""Tests for local model selection (no Ollama server contacted)."""

from __future__ import annotations

import pytest

from app.core.config import settings
from app.services.ollama_service import _pick_ollama_model

INSTALLED = ["deepseek-coder-v2:16b", "qwen2.5-coder:14b", "qwen3-vl:8b"]
SIZES_GB = {"deepseek-coder-v2:16b": 8.9, "qwen2.5-coder:14b": 9.0, "qwen3-vl:8b": 6.1}


class _Response:
    status_code = 200

    def __init__(self, sizes: dict[str, float]):
        self._sizes = sizes

    def json(self):
        return {"models": [{"name": n, "size": int(gb * 1e9)} for n, gb in self._sizes.items()]}


@pytest.fixture(autouse=True)
def _no_pin(monkeypatch):
    """Default to auto-selection; individual tests opt into pinning."""
    monkeypatch.setattr(settings, "ollama_model", "")


class TestPickOllamaModel:
    def test_no_models_returns_none(self):
        assert _pick_ollama_model([]) is None

    def test_prefers_smallest_by_default(self, monkeypatch):
        """A 9GB model on a 16GB machine thrashes; the smallest fits."""
        monkeypatch.setattr(
            "app.services.ollama_service.httpx.get",
            lambda *a, **k: _Response(SIZES_GB),
        )
        assert _pick_ollama_model(INSTALLED) == "qwen3-vl:8b"

    def test_explicit_pin_wins(self, monkeypatch):
        monkeypatch.setattr(settings, "ollama_model", "deepseek-coder-v2:16b")
        monkeypatch.setattr(
            "app.services.ollama_service.httpx.get",
            lambda *a, **k: _Response(SIZES_GB),
        )
        assert _pick_ollama_model(INSTALLED) == "deepseek-coder-v2:16b"

    def test_pin_matches_unqualified_tag(self, monkeypatch):
        monkeypatch.setattr(settings, "ollama_model", "deepseek-coder-v2")
        assert _pick_ollama_model(INSTALLED) == "deepseek-coder-v2:16b"

    def test_unavailable_pin_falls_back_to_size(self, monkeypatch):
        monkeypatch.setattr(settings, "ollama_model", "llama3:70b")
        monkeypatch.setattr(
            "app.services.ollama_service.httpx.get",
            lambda *a, **k: _Response(SIZES_GB),
        )
        assert _pick_ollama_model(INSTALLED) == "qwen3-vl:8b"

    def test_survives_a_failing_size_lookup(self, monkeypatch):
        """Discovery must not break when the size probe errors."""
        def _boom(*a, **k):
            raise RuntimeError("connection refused")

        monkeypatch.setattr("app.services.ollama_service.httpx.get", _boom)
        assert _pick_ollama_model(INSTALLED) in INSTALLED
