import json
import logging
import re

from pydantic import ValidationError

from app.core.config import settings
from app.models.resume import Resume
from app.models.match import Recommendation
from app.services.prompt_service import PromptService
from app.services.omniroute_service import OmniRouteService, OmniRouteError

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> str:
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end > brace_start:
        return text[brace_start : brace_end + 1]
    return text.strip()


async def apply_suggestion(resume: Resume, recommendation: Recommendation) -> Resume:
    prompt_service = PromptService()
    omniroute = OmniRouteService()

    resume_json = json.dumps(resume.model_dump(), indent=2, default=str)
    schema_json = json.dumps(Resume.model_json_schema(), indent=2)

    system = (
        "You are a resume optimization AI. Your task is to apply a specific improvement suggestion "
        "to a resume and return the updated resume as JSON.\n\n"
        f"Resume JSON schema:\n{schema_json}\n\n"
        "Rules:\n"
        "- Output ONLY the modified resume as valid JSON. No markdown, no explanations.\n"
        "- Only change the parts of the resume that are relevant to the suggestion.\n"
        "- Keep all other fields exactly as they are.\n"
        "- If the suggestion adds a skill, add it to the appropriate skill category.\n"
        "- If the suggestion updates the summary, only modify the summary field.\n"
        "- Maintain the exact same JSON structure."
    )

    user = (
        f"Current resume (JSON):\n{resume_json}\n\n"
        f"Suggestion to apply:\n"
        f"Section: {recommendation.section}\n"
        f"Message: {recommendation.message}\n"
        f"Suggested change: {recommendation.suggestion or recommendation.message}\n\n"
        "Return the complete updated resume as JSON."
    )

    last_error: Exception | None = None
    for attempt in range(omniroute.max_retries + 1):
        try:
            raw = await omniroute.send_prompt(system, user)
            cleaned = _extract_json(raw)
            data = json.loads(cleaned)
            return Resume(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning("Suggestion apply failed (attempt %d/%d): %s", attempt + 1, omniroute.max_retries + 1, e)
            last_error = e
        except OmniRouteError as e:
            logger.warning("OmniRoute error (attempt %d/%d): %s", attempt + 1, omniroute.max_retries + 1, e)
            last_error = e

    logger.warning("Suggestion apply failed after retries; returning original resume unchanged")
    return resume
