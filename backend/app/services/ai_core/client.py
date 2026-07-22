"""call_with_retry — shared retry loop for all AI services."""

import json
from collections.abc import Awaitable, Callable
from typing import TypeVar

from pydantic import ValidationError

from app.core.logging import get_logger
from app.services.omniroute_service import OmniRouteService, OmniRouteError
from app.services.ai_core.exceptions import AIServiceUnavailable

logger = get_logger(__name__)

T = TypeVar("T")


async def call_with_retry(
    build_prompt: Callable[[], Awaitable[tuple[str, str]]],
    parse_response: Callable[[str], T],
    omniroute: OmniRouteService | None = None,
    service_name: str = "AI",
) -> T:
    """Execute an AI call with retry logic."""
    if omniroute is None:
        omniroute = OmniRouteService()

    system, user = await build_prompt()
    last_error: Exception | None = None

    for attempt in range(omniroute.max_retries + 1):
        try:
            raw = await omniroute.send_prompt(system, user)
            return parse_response(raw)
        except json.JSONDecodeError as e:
            logger.warning("%s invalid JSON (attempt %d/%d)", service_name, attempt + 1, omniroute.max_retries + 1, error=str(e))
            last_error = e
        except ValidationError as e:
            logger.warning("%s validation failed (attempt %d/%d)", service_name, attempt + 1, omniroute.max_retries + 1, error=str(e))
            last_error = e
        except OmniRouteError as e:
            logger.warning("%s service error (attempt %d/%d)", service_name, attempt + 1, omniroute.max_retries + 1, error=str(e))
            last_error = e

    raise AIServiceUnavailable(f"{service_name} service unavailable after retries") from last_error
