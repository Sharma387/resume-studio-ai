"""Regression tests for ai_core.call_with_retry.

Guards against the NameError ('settings' undefined) and verifies that
settings.ai_model_auto is evaluated without error. Behavior of the retry /
fallback loop is preserved (real OmniRouteService is used; only the network
call is stubbed).
"""

import pytest

from app.core.config import settings
from app.services.ai_core.client import call_with_retry
from app.services.ai_core.exceptions import AIServiceUnavailable
from app.services.omniroute_service import OmniRouteError, OmniRouteService


async def test_call_with_retry_no_nameerror_evaluates_settings(monkeypatch):
    # settings must be defined; toggling ai_model_auto must not raise NameError.
    monkeypatch.setattr(settings, "ai_model_auto", True)

    async def fake_send(self, system, user):
        return "RAW"

    monkeypatch.setattr(OmniRouteService, "send_prompt", fake_send)

    async def build():
        return ("sys", "usr")

    # omniroute=None exercises internal instantiation; branch still skipped
    # because omniroute is no longer None afterwards.
    result = await call_with_retry(build, lambda raw: raw, omniroute=None)
    assert result == "RAW"


async def test_call_with_retry_uses_explicit_omniroute(monkeypatch):
    monkeypatch.setattr(settings, "ai_model_auto", False)

    async def fake_send(self, system, user):
        return "RESULT"

    monkeypatch.setattr(OmniRouteService, "send_prompt", fake_send)

    class _Fake:
        max_retries = 0

        async def send_prompt(self, system, user):
            return "EXPLICIT"

    async def build():
        return ("s", "u")

    result = await call_with_retry(build, lambda raw: raw, omniroute=_Fake())
    assert result == "EXPLICIT"


async def test_call_with_retry_raises_after_failures(monkeypatch):
    monkeypatch.setattr(settings, "ai_model_auto", True)

    async def boom(self, system, user):
        raise OmniRouteError("down")

    monkeypatch.setattr(OmniRouteService, "send_prompt", boom)

    async def build():
        return ("s", "u")

    with pytest.raises(AIServiceUnavailable):
        await call_with_retry(build, lambda raw: raw, omniroute=None)
