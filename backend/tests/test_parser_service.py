import json

import pytest

from app.models.resume import Resume
from app.services.parser_service import parse_resume, ParseError
from app.services.ai_core.exceptions import AIServiceUnavailable


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


def _enable_mock(monkeypatch):
    monkeypatch.setattr("app.services.parser_service.settings.allow_mock_ai_data", True)

def _mock_call_with_retry(return_values: list, monkeypatch):
    """Replace call_with_retry with a mock that returns given values."""
    _enable_mock(monkeypatch)
    idx = 0

    async def fake_call_with_retry(build_prompt, parse_response, omniroute=None, service_name="AI"):
        nonlocal idx
        import json
        from pydantic import ValidationError
        for attempt in range(len(return_values)):
            if idx >= len(return_values):
                from app.services.ai_core.exceptions import AIServiceUnavailable
                raise AIServiceUnavailable("exhausted")
            val = return_values[idx]
            idx += 1
            if isinstance(val, Exception):
                raise val
            try:
                return parse_response(val)
            except (json.JSONDecodeError, ValidationError):
                if idx >= len(return_values):
                    from app.services.ai_core.exceptions import AIServiceUnavailable
                    raise AIServiceUnavailable("exhausted after retries")
                continue
        from app.services.ai_core.exceptions import AIServiceUnavailable
        raise AIServiceUnavailable("exhausted")

    monkeypatch.setattr("app.services.parser_service.call_with_retry", fake_call_with_retry)


@pytest.mark.asyncio
async def test_parse_success(monkeypatch):
    _mock_call_with_retry([_valid_json()], monkeypatch)
    result = await parse_resume("some text")
    assert result.full_name == "John Doe"
    assert result.email == "john@example.com"


@pytest.mark.asyncio
async def test_parse_retry_on_invalid_json(monkeypatch):
    _mock_call_with_retry(["invalid json", _valid_json()], monkeypatch)
    result = await parse_resume("text")
    assert result.full_name == "John Doe"


@pytest.mark.asyncio
async def test_parse_retry_on_validation_error(monkeypatch):
    bad = json.dumps({"full_name": "", "email": "bad"})
    _mock_call_with_retry([bad, _valid_json()], monkeypatch)
    result = await parse_resume("text")
    assert result.full_name == "John Doe"


@pytest.mark.asyncio
async def test_parse_falls_back_to_mock_after_retries(monkeypatch):
    _mock_call_with_retry([AIServiceUnavailable("failed"), AIServiceUnavailable("failed")], monkeypatch)
    result = await parse_resume("text")
    assert result.full_name == "Alexandra Chen"
