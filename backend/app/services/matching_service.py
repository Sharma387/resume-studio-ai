import json
import logging
import uuid
from datetime import datetime, timezone

from app.core.config import settings
from app.models.match import MatchResult
from app.models.resume import Resume
from app.services.prompt_service import PromptService
from app.services.ai_core import extract_json, call_with_retry, AIServiceUnavailable

logger = logging.getLogger(__name__)


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

    async def build() -> tuple[str, str]:
        resume_json = json.dumps(resume.model_dump(), indent=2, default=str)
        match_schema = json.dumps(MatchResult.model_json_schema(), indent=2)
        return prompt_service.build_match_prompt(resume_json, job_description, match_schema)

    def parse(raw: str) -> MatchResult:
        cleaned = extract_json(raw)
        data = json.loads(cleaned)
        result = MatchResult(**data)
        result.id = uuid.uuid4().hex
        result.resume_id = resume_id
        result.job_title = job_title or result.job_title
        result.created_at = datetime.now(timezone.utc).isoformat()
        return result

    try:
        return await call_with_retry(build, parse, service_name="Matcher")
    except AIServiceUnavailable:
        logger.warning("OmniRoute matching failed after retries; falling back to mock data")
        return _mock_match(resume_id, job_title, resume)
