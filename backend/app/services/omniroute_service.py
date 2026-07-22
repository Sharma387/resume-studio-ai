import json

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class OmniRouteError(Exception):
    pass


class OmniRouteService:
    def __init__(
        self,
        api_url: str = settings.omniroute_api_url,
        api_key: str = settings.omniroute_api_key,
        model: str = settings.omniroute_model,
        timeout: int = settings.omniroute_timeout,
        max_retries: int = settings.omniroute_max_retries,
    ):
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries

    async def send_prompt(self, system: str, user: str) -> str:
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                return await self._call(system, user)
            except httpx.TimeoutException as e:
                logger.warning("OmniRoute timeout (attempt %d/%d)", attempt + 1, self.max_retries + 1)
                last_error = e
            except httpx.HTTPStatusError as e:
                logger.error("OmniRoute HTTP %s (attempt %d/%d)", e.response.status_code, attempt + 1, self.max_retries + 1)
                last_error = e
                if attempt < self.max_retries:
                    continue
                raise OmniRouteError(f"OmniRoute returned {e.response.status_code}") from e
            except Exception as e:
                logger.exception("OmniRoute unexpected error")
                last_error = e
                if attempt < self.max_retries:
                    continue
                raise OmniRouteError(str(e)) from e

        raise OmniRouteError("All retries exhausted") from last_error

    async def _call(self, system: str, user: str) -> str:
        api_key = self.api_key if self.api_key else "not-needed"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.1,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.api_url, headers=headers, json=body)
            response.raise_for_status()
            raw = response.content
            logger.info("OmniRoute raw response (%d bytes): %s", len(raw), raw[:300])
            text = raw.decode("utf-8")
            data = json.loads(text)

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return content.strip()
