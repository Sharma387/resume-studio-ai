import json

import pytest

from app.models.resume import Resume
from app.services.parser_service import parse_resume, ParseError


def _mock_omniroute(return_value: str | list[Exception], monkeypatch):
    """Replace the OmniRouteService with a mock that returns given values."""

    class FakeOmniRoute:
        def __init__(self):
            self.max_retries = 0 if len(return_value) == 1 else len(return_value) - 1
            self._idx = 0
            self._values = return_value if isinstance(return_value, list) else [return_value]

        async def send_prompt(self, system: str, user: str) -> str:
            val = self._values[self._idx]
            self._idx += 1
            if isinstance(val, Exception):
                raise val
            return val

    import app.services.parser_service as mod
    monkeypatch.setattr(mod, "OmniRouteService", lambda *a, **kw: FakeOmniRoute())


def _valid_json() -> str:
    r = Resume(
        full_name="John Doe",
        email="john@example.com",
        summary="Engineer",
        experience=[],
        education=[],
        projects=[],
        skills=[],
        certifications=[],
    )
    return r.model_dump_json()


@pytest.mark.asyncio
async def test_parse_success(monkeypatch):
    _mock_omniroute(_valid_json(), monkeypatch)
    result = await parse_resume("some text")
    assert result.full_name == "John Doe"
    assert result.email == "john@example.com"


@pytest.mark.asyncio
async def test_parse_retry_on_invalid_json(monkeypatch):
    _mock_omniroute(["invalid json", _valid_json()], monkeypatch)
    result = await parse_resume("text")
    assert result.full_name == "John Doe"


@pytest.mark.asyncio
async def test_parse_retry_on_validation_error(monkeypatch):
    bad = json.dumps({"full_name": "", "email": "bad"})
    _mock_omniroute([bad, _valid_json()], monkeypatch)
    result = await parse_resume("text")
    assert result.full_name == "John Doe"


@pytest.mark.asyncio
async def test_parse_fails_after_all_retries(monkeypatch):
    _mock_omniroute(["bad json", "also bad"], monkeypatch)
    with pytest.raises(ParseError):
        await parse_resume("text")
