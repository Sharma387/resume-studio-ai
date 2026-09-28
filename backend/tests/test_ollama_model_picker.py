"""Tests for local model selection (no Ollama server contacted)."""

from __future__ import annotations

import pytest

from app.core.config import settings
from app.services.ollama_service import _is_reasoning_model, _pick_ollama_model

INSTALLED = ["deepseek-coder-v2:16b", "qwen2.5-coder:14b", "qwen3-vl:8b"]
SIZES_GB = {"deepseek-coder-v2:16b": 8.9, "qwen2.5-coder:14b": 9.0, "qwen3-vl:8b": 6.1}

# qwen2.5:3b-instruct is what the picker should reach for on a small box.
SMALL = ["qwen2.5:3b-instruct", "qwen2.5-coder:14b", "qwen3-vl:8b"]
SMALL_SIZES = {"qwen2.5:3b-instruct": 1.9, "qwen2.5-coder:14b": 9.0, "qwen3-vl:8b": 6.1}


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


def _stub_sizes(monkeypatch, sizes: dict[str, float]) -> None:
    monkeypatch.setattr(
        "app.services.ollama_service.httpx.get",
        lambda *a, **k: _Response(sizes),
    )


class TestIsReasoningModel:
    @pytest.mark.parametrize(
        "name",
        ["qwen3-vl:8b", "qwen3:4b", "deepseek-r1:7b", "gpt-oss:20b", "magistral-small:24b"],
    )
    def test_detects_reasoning_families(self, name):
        assert _is_reasoning_model(name) is True

    @pytest.mark.parametrize(
        "name",
        ["qwen2.5:3b-instruct", "qwen2.5-coder:14b", "deepseek-coder-v2:16b", "llama3.2:3b", "gemma2:2b"],
    )
    def test_plain_models_are_not_reasoning(self, name):
        assert _is_reasoning_model(name) is False


class TestPickOllamaModel:
    def test_no_models_returns_none(self):
        assert _pick_ollama_model([]) is None

    def test_prefers_smallest_by_default(self, monkeypatch):
        """A 9GB model on a 16GB machine thrashes; the smallest fits."""
        _stub_sizes(monkeypatch, SMALL_SIZES)
        assert _pick_ollama_model(SMALL) == "qwen2.5:3b-instruct"

    def test_skips_reasoning_model_even_though_it_is_smaller(self, monkeypatch):
        """qwen3-vl:8b is 6.1GB but its hidden thinking truncates the JSON,
        so the 8.9GB plain model still wins."""
        _stub_sizes(monkeypatch, SIZES_GB)
        assert _pick_ollama_model(INSTALLED) == "deepseek-coder-v2:16b"

    def test_reasoning_model_wins_when_it_is_the_only_option(self, monkeypatch):
        _stub_sizes(monkeypatch, SIZES_GB)
        assert _pick_ollama_model(["qwen3-vl:8b"]) == "qwen3-vl:8b"

    def test_explicit_pin_wins(self, monkeypatch):
        """An explicit pin overrides the reasoning-model rule, so the user can
        still opt into one knowingly."""
        monkeypatch.setattr(settings, "ollama_model", "qwen3-vl:8b")
        _stub_sizes(monkeypatch, SIZES_GB)
        assert _pick_ollama_model(SMALL) == "qwen3-vl:8b"

    def test_pin_matches_unqualified_tag(self, monkeypatch):
        monkeypatch.setattr(settings, "ollama_model", "deepseek-coder-v2")
        _stub_sizes(monkeypatch, SIZES_GB)
        assert _pick_ollama_model(INSTALLED) == "deepseek-coder-v2:16b"

    def test_unavailable_pin_falls_back_to_auto(self, monkeypatch):
        monkeypatch.setattr(settings, "ollama_model", "llama3:70b")
        _stub_sizes(monkeypatch, SMALL_SIZES)
        assert _pick_ollama_model(SMALL) == "qwen2.5:3b-instruct"

    def test_survives_a_failing_size_lookup(self, monkeypatch):
        """Discovery must not break when the size probe errors."""

        def _boom(*a, **k):
            raise RuntimeError("connection refused")

        monkeypatch.setattr("app.services.ollama_service.httpx.get", _boom)
        assert _pick_ollama_model(SMALL) == "qwen2.5:3b-instruct"
