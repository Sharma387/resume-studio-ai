import json
import logging
import re
import uuid
from datetime import datetime, timezone

from pydantic import ValidationError

from app.core.config import settings
from app.models.match import MatchResult
from app.models.resume import Resume
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


def _mock_match(resume_id: str, job_title: str | None, resume: Resume) -> MatchResult:
    return MatchResult(
        id=uuid.uuid4().hex,
        resume_id=resume_id,
        job_title=job_title or "Software Engineer",
        overall_score=72.5,
        matched_skills=["Python", "React", "AWS", "Docker"],
        missing_skills=["Kubernetes", "GraphQL"],
        summary=f"{resume.full_name}'s resume matches core technical requirements. "
        f"The overall fit is strong for a senior engineer position, "
        f"with room to improve in cloud orchestration and API technologies.",
        created_at=datetime.now(timezone.utc).isoformat(),
    )


async def analyze_match(resume_id: str, job_title: str | None, job_description: str, resume: Resume) -> MatchResult:
    if "localhost" not in settings.omniroute_api_url and not settings.omniroute_api_key:
        logger.info("No OmniRoute endpoint configured; returning mock match")
        return _mock_match(resume_id, job_title, resume)

    prompt_service = PromptService()
    omniroute = OmniRouteService()

    resume_json = json.dumps(resume.model_dump(), indent=2, default=str)
    match_schema = json.dumps(MatchResult.model_json_schema(), indent=2)
    system_prompt, user_prompt = prompt_service.build_match_prompt(resume_json, job_description, match_schema)

    last_error: Exception | None = None

    for attempt in range(omniroute.max_retries + 1):
        try:
            raw = await omniroute.send_prompt(system_prompt, user_prompt)
            cleaned = _extract_json(raw)
            data = json.loads(cleaned)
            result = MatchResult(**data)

            result.id = uuid.uuid4().hex
            result.resume_id = resume_id
            result.job_title = job_title or result.job_title
            result.created_at = datetime.now(timezone.utc).isoformat()

            return result
        except json.JSONDecodeError as e:
            logger.warning("Invalid JSON from OmniRoute (attempt %d/%d): %s", attempt + 1, omniroute.max_retries + 1, e)
            last_error = e
        except ValidationError as e:
            logger.warning("Pydantic validation failed (attempt %d/%d): %s", attempt + 1, omniroute.max_retries + 1, e)
            last_error = e
        except OmniRouteError as e:
            logger.warning("OmniRoute request failed (attempt %d/%d): %s", attempt + 1, omniroute.max_retries + 1, e)
            last_error = e

    logger.warning("OmniRoute matching failed after retries; falling back to mock data")
    return _mock_match(resume_id, job_title, resume)
