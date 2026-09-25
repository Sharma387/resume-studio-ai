import json
import uuid
from datetime import UTC, datetime

from app.core.config import settings
from app.core.logging import get_logger
from app.models.match import MatchResult
from app.models.resume import Resume
from app.services.ai_core import AIServiceUnavailable, extract_json
from app.services.ollama_service import compact_resume, run_with_providers
from app.services.prompt_service import PromptService

logger = get_logger(__name__)

MATCH_SYSTEM_PROMPT = """You are an ATS resume matcher. Analyse the candidate's resume against the job description and return ONLY a JSON object with these fields:
- overall_score: number from 0 to 100
- skill_matches: [{"skill": string, "required": bool, "matched": bool, "category": string or null}]
- matched_skills: [string]
- missing_skills: [string]
- recommendations: [{"section": string, "priority": "high" or "medium" or "low", "message": string, "suggestion": string or null}]
- summary: string (2-3 sentences)
- job_title: string or null

Do NOT include id, resume_id, user_id, or created_at — the backend manages those.
Use lowercase null for missing values. Base the analysis strictly on the actual resume content shown."""


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
    prompt_service = PromptService()

    async def build_omniroute_prompt() -> tuple[str, str]:
        resume_json = json.dumps(resume.model_dump(), indent=2, default=str)
        match_schema = json.dumps(MatchResult.model_json_schema(), indent=2)
        return prompt_service.build_match_prompt(resume_json, job_description, match_schema)

    async def build_ollama_prompt() -> tuple[str, str]:
        return (
            MATCH_SYSTEM_PROMPT,
            f"Candidate resume (JSON):\n{compact_resume(resume)}\n\n"
            f"Job title: {job_title or 'Not specified'}\n\n"
            f"Job description:\n{job_description}",
        )

    try:
        return await run_with_providers(
            service_name="Matcher",
            build_ollama_prompt=build_ollama_prompt,
            build_omniroute_prompt=build_omniroute_prompt,
            parse=lambda raw: _parse_match(raw, resume_id, user_id, job_title),
            allow_mock=settings.allow_mock_ai_data,
            mock_factory=lambda: _mock_match(resume_id, job_title, resume, user_id),
        )
    except AIServiceUnavailable as e:
        raise RuntimeError("AI service unavailable. Please try again later.") from e


def _parse_match(raw: str, resume_id: str, user_id: str, job_title: str | None) -> MatchResult:
    """Build a MatchResult from LLM output, filling backend-managed fields."""
    data = json.loads(extract_json(raw))
    for key in ("id", "resume_id", "user_id", "created_at"):
        data.pop(key, None)
    model_job_title = data.pop("job_title", None)
    return MatchResult(
        user_id=user_id,
        id=uuid.uuid4().hex,
        resume_id=resume_id,
        job_title=job_title or model_job_title,
        created_at=datetime.now(UTC).isoformat(),
        **data,
    )
