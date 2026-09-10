import json
import uuid
from datetime import UTC, datetime

from app.core.config import settings
from app.core.logging import get_logger
from app.models.match import MatchResult
from app.models.resume import Resume
from app.services.ai_core import AIServiceUnavailable, call_with_retry, extract_json
from app.services.prompt_service import PromptService

logger = get_logger(__name__)


def _mock_match(resume_id: str, job_title: str | None, resume: Resume, user_id: str) -> MatchResult:
    return MatchResult(
        user_id=user_id,
        id=uuid.uuid4().hex,
        resume_id=resume_id,
        job_title=job_title or "Software Engineer",
        overall_score=72.5,
        matched_skills=["Python", "React", "AWS", "Docker"],
        missing_skills=["Kubernetes", "GraphQL"],
        skill_matches=[
            {"skill": "Python", "required": True, "matched": True, "category": "Languages"},
            {"skill": "React", "required": True, "matched": True, "category": "Frontend"},
            {"skill": "AWS", "required": True, "matched": True, "category": "Cloud"},
            {"skill": "Docker", "required": True, "matched": True, "category": "DevOps"},
            {"skill": "Kubernetes", "required": True, "matched": False, "category": "DevOps"},
            {"skill": "GraphQL", "required": False, "matched": False, "category": "API"},
        ],
        recommendations=[
            {
                "section": "skills",
                "priority": "high",
                "message": "Add Kubernetes experience to demonstrate cloud orchestration proficiency",
                "suggestion": "Include any container orchestration projects or certifications",
            },
            {
                "section": "experience",
                "priority": "medium",
                "message": "Highlight API design experience to strengthen GraphQL alignment",
                "suggestion": "Mention REST or GraphQL API projects in your experience section",
            },
        ],
        summary=f"{resume.full_name}'s resume matches core technical requirements. "
        f"The overall fit is strong for a senior engineer position, "
        f"with room to improve in cloud orchestration and API technologies.",
        created_at=datetime.now(UTC).isoformat(),
    )


async def analyze_match(
    resume_id: str, job_title: str | None, job_description: str, resume: Resume, user_id: str
) -> MatchResult:
    if "localhost" not in settings.omniroute_api_url and not settings.omniroute_api_key:
        if settings.allow_mock_ai_data:
            logger.info("Mock AI data enabled; returning mock match")
            return _mock_match(resume_id, job_title, resume, user_id)
        raise RuntimeError("AI service is not configured. Set OMNIROUTE_API_URL or ALLOW_MOCK_AI_DATA=true.")

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
        result.created_at = datetime.now(UTC).isoformat()
        return result

    try:
        return await call_with_retry(build, parse, service_name="Matcher")
    except AIServiceUnavailable:
        if settings.allow_mock_ai_data:
            logger.warning("AI matching failed; returning mock match")
            return _mock_match(resume_id, job_title, resume, user_id)
        raise RuntimeError("AI service unavailable. Please try again later.")
