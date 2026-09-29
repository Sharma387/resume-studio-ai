"""Tests for provider dispatch over ``AI_PROVIDER_ORDER``.

The section-by-section parse holds a fixed ``(system, user)`` pair and wants the
model's text back verbatim, so it cannot use ``run_with_providers`` (which needs
a per-service prompt builder and a parser). ``chat_providers`` is the same
ordering reduced to that case — without it, ``AI_PROVIDER_ORDER`` silently did
nothing for the parse, and "OmniRoute first" was not honoured at all.
"""

import httpx
import pytest

from app.core.config import settings
from app.services.ollama_service import chat_providers


@pytest.fixture
def _order(monkeypatch):
    def _set(value: str) -> None:
        monkeypatch.setattr(settings, "ai_provider_order", value)

    return _set


@pytest.fixture
def _omniroute(monkeypatch):
    """Record OmniRoute attempts and control the reply."""
    calls: list[dict] = []
    box = {"reply": "from omniroute", "error": None}

    class FakeService:
        def __init__(self, **kwargs):
            self.init_kwargs = kwargs
            self.max_retries = 99

        async def send_prompt(self, system, user):
            calls.append({"system": system, "user": user, "timeout": self.init_kwargs.get("timeout")})
            if box["error"] is not None:
                raise box["error"]
            return box["reply"]

    import app.services.ollama_service as module

    monkeypatch.setattr(module, "OmniRouteService", FakeService)
    return calls, box


@pytest.fixture
def _ollama(monkeypatch):
    calls: list[dict] = []
    box = {"reply": "from ollama", "error": None}

    async def fake_chat_ollama(system, user, **kwargs):
        calls.append({"system": system, "user": user, **kwargs})
        if box["error"] is not None:
            raise box["error"]
        return box["reply"]

    import app.services.ollama_service as module

    monkeypatch.setattr(module, "chat_ollama", fake_chat_ollama)
    return calls, box


class TestOrdering:
    async def test_omniroute_first_wins(self, _order, _omniroute, _ollama):
        _order("omniroute,ollama")
        omni_calls, _ = _omniroute
        ollama_calls, _ = _ollama
        result = await chat_providers("sys", "user", service_name="Parser")
        assert result == "from omniroute"
        assert len(omni_calls) == 1
        assert ollama_calls == []

    async def test_ollama_first_wins(self, _order, _omniroute, _ollama):
        _order("ollama,omniroute")
        omni_calls, _ = _omniroute
        ollama_calls, _ = _ollama
        result = await chat_providers("sys", "user", service_name="Parser")
        assert result == "from ollama"
        assert len(ollama_calls) == 1
        assert omni_calls == []

    async def test_falls_back_to_ollama_when_omniroute_raises(self, _order, _omniroute, _ollama):
        _order("omniroute,ollama")
        _, omni_box = _omniroute
        omni_box["error"] = httpx.ConnectError("gateway down")
        ollama_calls, _ = _ollama
        assert await chat_providers("sys", "user") == "from ollama"
        assert len(ollama_calls) == 1

    async def test_falls_back_when_omniroute_returns_nothing(self, _order, _omniroute, _ollama):
        _order("omniroute,ollama")
        _, omni_box = _omniroute
        omni_box["reply"] = "   "
        ollama_calls, _ = _ollama
        assert await chat_providers("sys", "user") == "from ollama"
        assert len(ollama_calls) == 1

    async def test_falls_back_when_ollama_first_fails(self, _order, _omniroute, _ollama):
        _order("ollama,omniroute")
        _, ollama_box = _ollama
        ollama_box["error"] = RuntimeError("ollama down")
        omni_calls, _ = _omniroute
        assert await chat_providers("sys", "user") == "from omniroute"
        assert len(omni_calls) == 1

    async def test_none_when_every_provider_fails(self, _order, _omniroute, _ollama):
        _order("omniroute,ollama")
        _, omni_box = _omniroute
        _, ollama_box = _ollama
        omni_box["error"] = RuntimeError("gateway down")
        ollama_box["error"] = RuntimeError("ollama down")
        assert await chat_providers("sys", "user") is None


class TestArguments:
    async def test_omniroute_retry_is_disabled(self, _order, _omniroute):
        """The chunk loop owns retries; doubling them doubles the wait."""
        _order("omniroute")
        calls, _ = _omniroute
        await chat_providers("sys", "user")
        assert calls[0]["timeout"] == settings.omniroute_timeout

    async def test_omniroute_timeout_is_overridable(self, _order, _omniroute):
        _order("omniroute")
        calls, _ = _omniroute
        await chat_providers("sys", "user", timeout=42)
        assert calls[0]["timeout"] == 42

    async def test_ollama_receives_num_predict_and_temperature(self, _order, _ollama):
        _order("ollama")
        calls, _ = _ollama
        await chat_providers("sys", "user", timeout=7, num_predict=123, temperature=0.1)
        assert calls[0]["num_predict"] == 123
        assert calls[0]["temperature"] == 0.1
        assert calls[0]["timeout"] == 7

    async def test_ollama_omits_num_predict_when_not_given(self, _order, _ollama):
        _order("ollama")
        calls, _ = _ollama
        await chat_providers("sys", "user")
        assert "num_predict" not in calls[0]

    async def test_prompt_is_passed_through_verbatim(self, _order, _omniroute):
        _order("omniroute")
        calls, _ = _omniroute
        await chat_providers("SYSTEM TEXT", "USER TEXT")
        assert calls[0]["system"] == "SYSTEM TEXT"
        assert calls[0]["user"] == "USER TEXT"


class TestMisconfiguration:
    async def test_no_providers_configured_returns_none(self, _order):
        _order("")
        assert await chat_providers("sys", "user") is None

    async def test_unknown_provider_is_skipped(self, _order, _ollama):
        _order("mystery,ollama")
        calls, _ = _ollama
        assert await chat_providers("sys", "user") == "from ollama"
        assert len(calls) == 1
