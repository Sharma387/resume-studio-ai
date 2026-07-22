"""OmniRouteClient — wraps the retry loop shared by all AI services."""

import json
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from pydantic import ValidationError

from app.services.omniroute_service import OmniRouteService, OmniRouteError
from app.services.ai_core.exceptions import AIServiceUnavailable, AIResponseError

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def call_with_retry(
    build_prompt: Callable[[], Awaitable[tuple[str, str]]],
    parse_response: Callable[[str], T],
    omniroute: OmniRouteService | None = None,
    service_name: str = "AI",
) -> T:
    """Execute an AI call with retry logic.

    Args:
        build_prompt: Async callable that returns (system_prompt, user_prompt).
        parse_response: Callable that parses the raw AI response into the desired type.
        omniroute: OmniRouteService instance (created fresh if None).
        service_name: Name for log messages.

    Returns:
        The parsed response.

    Raises:
        AIServiceUnavailable: After all retries are exhausted.
        AIResponseError: When the AI returns invalid data.
    """
    if omniroute is None:
        omniroute = OmniRouteService()

    system, user = await build_prompt()
    last_error: Exception | None = None

    for attempt in range(omniroute.max_retries + 1):
        try:
            raw = await omniroute.send_prompt(system, user)
            return parse_response(raw)
        except json.JSONDecodeError as e:
            logger.warning("%s invalid JSON (attempt %d/%d): %s", service_name, attempt + 1, omniroute.max_retries + 1, e)
            last_error = e
        except ValidationError as e:
            logger.warning("%s validation failed (attempt %d/%d): %s", service_name, attempt + 1, omniroute.max_retries + 1, e)
            last_error = e
        except OmniRouteError as e:
            logger.warning("%s service error (attempt %d/%d): %s", service_name, attempt + 1, omniroute.max_retries + 1, e)
            last_error = e

    raise AIServiceUnavailable(f"{service_name} service unavailable after retries") from last_error
