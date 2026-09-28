"""Generation options must fit the kind of work being asked of the model.

The creative services (cover letter, writer, interview coach) share the
provider path with the parser. When temperature was pinned low for the parser
it applied to all of them, so every generated cover letter came back in the
same mould — a silent quality regression in features nobody was testing.
"""

from __future__ import annotations

import pytest

from app.services import ollama_service


class _Recorder:
    """Captures the request body sent to Ollama."""

    def __init__(self, reply: str = "some text"):
        self.reply = reply
        self.bodies: list[dict] = []

    async def __call__(self, model, system, user, **kwargs):
        return self.reply

    def install(self, monkeypatch):
        recorder = self

        class _Client:
            def __init__(self, **kw):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def post(self, url, json=None, **kw):
                recorder.bodies.append({"url": url, **json})
                return _Response(recorder.reply)

        monkeypatch.setattr(ollama_service.httpx, "AsyncClient", _Client)


class _Response:
    def __init__(self, reply: str):
        self.status_code = 200
        self._reply = reply

    def json(self):
        return {"message": {"content": self._reply}}


@pytest.mark.asyncio
async def test_temperature_is_left_to_the_server_by_default(monkeypatch):
    """A caller that says nothing about temperature must not have one imposed
    on it — that is what made creative output repetitive."""
    rec = _Recorder()
    rec.install(monkeypatch)

    await ollama_service.generate_with_ollama("m", "sys", "user")

    assert "temperature" not in rec.bodies[0]["options"]


@pytest.mark.asyncio
async def test_a_caller_can_ask_for_determinism(monkeypatch):
    rec = _Recorder()
    rec.install(monkeypatch)

    await ollama_service.generate_with_ollama("m", "sys", "user", temperature=0.1)

    assert rec.bodies[0]["options"]["temperature"] == 0.1


@pytest.mark.asyncio
async def test_the_parser_asks_for_determinism(monkeypatch):
    """Parsing is transcription; a wandering model only invents detail."""
    calls: list[dict] = []

    async def fake_chat(system, user, **kwargs):
        calls.append(kwargs)
        return '{"skills": []}'

    monkeypatch.setattr("app.services.parser_service.chat_ollama", fake_chat)

    from app.services.parser_service import _parse_chunked

    await _parse_chunked(
        "RAJASEKAR SHARMA\n"
        "Senior Project Manager\n"
        "a@b.com\n\n"
        "CORE COMPETENCIES\n- Programme Management\n- Vendor Management\n"
    )

    assert calls, "the parser should have made at least one chunk call"
    assert all(call.get("temperature") == 0.1 for call in calls)


@pytest.mark.asyncio
async def test_the_context_window_is_always_pinned(monkeypatch):
    """Ollama.app defaults to 4096; a larger inherited window reserves memory
    the box does not have and stalls generation."""
    rec = _Recorder()
    rec.install(monkeypatch)

    await ollama_service.generate_with_ollama("m", "sys", "user")

    assert rec.bodies[0]["options"]["num_ctx"] == ollama_service.OLLAMA_NUM_CTX


@pytest.mark.asyncio
async def test_the_native_endpoint_is_used(monkeypatch):
    """The /v1 shim ignored the request and timed out on this setup."""
    rec = _Recorder()
    rec.install(monkeypatch)

    await ollama_service.generate_with_ollama("m", "sys", "user")

    assert rec.bodies[0]["url"].endswith("/api/chat")
