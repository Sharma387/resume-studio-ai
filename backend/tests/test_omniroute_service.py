import pytest
import httpx

from app.services.omniroute_service import OmniRouteService, OmniRouteError


@pytest.mark.asyncio
async def test_send_prompt_success():
    svc = OmniRouteService(
        api_url="http://localhost:0/v1/fake",
        api_key="test-key",
        model="test-model",
        timeout=5,
        max_retries=0,
    )

    class FakeResponse:
        status_code = 200
        content = b'{"choices": [{"message": {"content": "hello"}}]}'
        def raise_for_status(self):
            pass

    class FakeClient:
        def __init__(self, *a, **kw):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            pass
        async def post(self, *a, **kw):
            return FakeResponse()

    original = httpx.AsyncClient
    httpx.AsyncClient = FakeClient
    try:
        result = await svc.send_prompt("system", "user")
        assert result == "hello"
    finally:
        httpx.AsyncClient = original


@pytest.mark.asyncio
async def test_retry_on_timeout():
    call_count = 0

    class FakeClient:
        def __init__(self, *a, **kw):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            pass
        async def post(self, *a, **kw):
            nonlocal call_count
            call_count += 1
            raise httpx.TimeoutException("timed out")

    original = httpx.AsyncClient
    httpx.AsyncClient = FakeClient
    try:
        svc = OmniRouteService(
            api_url="http://localhost:0/v1/fake",
            api_key="key",
            model="m",
            timeout=5,
            max_retries=2,
        )
        with pytest.raises(OmniRouteError):
            await svc.send_prompt("s", "u")
        assert call_count == 3
    finally:
        httpx.AsyncClient = original
