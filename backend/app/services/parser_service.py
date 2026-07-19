import json
import logging

from pydantic import ValidationError

from app.models.resume import Resume
from app.services.prompt_service import PromptService
from app.services.omniroute_service import OmniRouteService, OmniRouteError

logger = logging.getLogger(__name__)


class ParseError(Exception):
    pass


async def parse_resume(text: str) -> Resume:
    prompt_service = PromptService()
    omniroute = OmniRouteService()

    schema = json.dumps(Resume.model_json_schema(), indent=2)
    system_prompt, user_prompt = prompt_service.build_prompt(text, schema)

    last_error: Exception | None = None

    for attempt in range(omniroute.max_retries + 1):
        try:
            raw = await omniroute.send_prompt(system_prompt, user_prompt)
            data = json.loads(raw)
            return Resume(**data)
        except json.JSONDecodeError as e:
            logger.warning("Invalid JSON from OmniRoute (attempt %d/%d): %s", attempt + 1, omniroute.max_retries + 1, e)
            last_error = e
        except ValidationError as e:
            logger.warning("Pydantic validation failed (attempt %d/%d): %s", attempt + 1, omniroute.max_retries + 1, e)
            last_error = e
        except OmniRouteError as e:
            raise ParseError(str(e)) from e

    raise ParseError("Failed to parse resume after retries") from last_error
