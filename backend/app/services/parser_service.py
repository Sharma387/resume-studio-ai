import json

from app.core.config import settings  # noqa: F401 — referenced by test monkeypatch
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.models.resume import Certification, Education, Experience, Project, Resume, Skill
from app.services.ai_core import AIServiceUnavailable, extract_json
from app.services.ollama_service import run_with_providers
from app.services.prompt_service import PromptService

logger = get_logger(__name__)

# Compact field instructions sent to Ollama instead of the full 10KB+ JSON
# schema. Local models have small context windows and slower generation, so a
# short prompt parses faster and still validates against the real Resume model
# server-side.
OLLAMA_SCHEMA_INSTRUCTIONS = """Return ONLY a JSON object (no markdown, no commentary) with these fields:

Top-level strings:
- full_name, email, phone, location, linkedin, github, website, professional_title, summary

Arrays (use [] and null when absent):
- education: [{"institution", "degree", "field", "start_date", "end_date", "gpa", "achievements": []}]
- experience: [{"company", "title", "location", "start_date", "end_date", "current": bool, "description": []}]
- projects: [{"name", "description", "url", "technologies": []}]
- skills: [{"category", "skills": []}]
- certifications: [{"name", "issuer", "date", "url"}]
- awards: [{"name", "issuer", "date", "description"}]
- languages: [{"name", "proficiency"}]

Use lowercase null (not None) for missing values. Keep descriptions concise."""


def _salvage_llm_dict(data: dict, text: str) -> dict:
    """Repair common LLM output quirks that would fail strict validation."""
    import re

    if not str(data.get("email") or "").strip() or "@" not in str(data.get("email") or ""):
        match = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
        if match:
            data["email"] = match.group(0)
    return data


class ParseError(AppError):
    """Raised when resume parsing fails irrecoverably."""

    code = "PARSE_ERROR"
    status_code = 422


def _coerce_model_dict(data: dict) -> dict:
    """Normalise LLM-produced fields that the backend overrides.

    ``user_id`` is an internal identifier the backend always sets (see
    ``parse``), so a model emitting ``None`` (it has no knowledge of the
    user's internal ID) must not fail schema validation.
    """
    if not isinstance(data.get("user_id"), str) or not data["user_id"]:
        data["user_id"] = ""
    return data


def _mock_resume() -> Resume:
    return Resume(
        user_id="mock",
        full_name="Alexandra Chen",
        email="alexandra.chen@example.com",
        phone="+1 (555) 123-4567",
        location="San Francisco, CA",
        linkedin="https://linkedin.com/in/alexchen",
        github="https://github.com/alexchen",
        website="https://alexchen.dev",
        summary="Senior full-stack engineer with 6+ years of experience building scalable web applications. "
        "Proficient in React, Python, and cloud infrastructure. Passionate about developer tooling and AI.",
        education=[
            Education(
                institution="University of California, Berkeley",
                degree="Bachelor of Science",
                field="Computer Science",
                start_date="2014-08",
                end_date="2018-05",
                gpa=3.7,
                achievements=["Dean's List 2016, 2017", "Teaching Assistant for Data Structures"],
            ),
        ],
        experience=[
            Experience(
                company="TechCorp Inc.",
                title="Senior Software Engineer",
                location="San Francisco, CA",
                start_date="2021-03",
                end_date=None,
                current=True,
                description=[
                    "Led a team of 5 engineers building a real-time data pipeline processing 10M+ events/day",
                    "Designed and implemented a microservices architecture reducing deployment time by 60%",
                    "Mentored 3 junior engineers through structured code reviews and pair programming",
                ],
            ),
            Experience(
                company="StartupXYZ",
                title="Full Stack Engineer",
                location="Oakland, CA",
                start_date="2018-06",
                end_date="2021-02",
                current=False,
                description=[
                    "Built the core SaaS platform using React, Node.js, and PostgreSQL",
                    "Implemented CI/CD pipelines with GitHub Actions and Docker",
                    "Reduced API response times by 40% through query optimization and caching",
                ],
            ),
        ],
        projects=[
            Project(
                name="Open Source CLI Tool",
                description="A command-line tool for scaffolding React components with built-in best practices",
                url="https://github.com/alexchen/scaffold-react",
                technologies=["TypeScript", "Node.js", "Commander.js"],
            ),
            Project(
                name="AI Resume Analyzer",
                description="An NLP-based tool that analyzes resumes and provides ATS optimization suggestions",
                url="https://github.com/alexchen/resume-analyzer",
                technologies=["Python", "FastAPI", "OpenAI", "React"],
            ),
        ],
        skills=[
            Skill(category="Languages", skills=["TypeScript", "Python", "Go", "SQL"]),
            Skill(category="Frontend", skills=["React", "Next.js", "Tailwind CSS", "Redux"]),
            Skill(category="Backend", skills=["FastAPI", "Node.js", "PostgreSQL", "Redis"]),
            Skill(category="DevOps", skills=["Docker", "Kubernetes", "AWS", "Terraform"]),
        ],
        certifications=[
            Certification(
                name="AWS Solutions Architect – Associate",
                issuer="Amazon Web Services",
                date="2022-11",
                url="https://aws.amazon.com/certification/",
            ),
        ],
    )


async def parse_resume(text: str) -> Resume:
    async def build_ollama_prompt() -> tuple[str, str]:
        return ("You are a resume parser. " + OLLAMA_SCHEMA_INSTRUCTIONS, text)

    async def build_omniroute_prompt() -> tuple[str, str]:
        prompt_service = PromptService()
        schema = json.dumps(Resume.model_json_schema(), indent=2)
        return prompt_service.build_prompt(text, schema)

    def parse(raw: str) -> Resume:
        cleaned = extract_json(raw)
        data = json.loads(cleaned)
        try:
            return Resume(**_coerce_model_dict(data))
        except Exception as ve:
            # LLMs often emit URLs without a scheme or hallucinate the email —
            # repair what we can before giving up on the output.
            logger.warning("Parser output failed validation, attempting salvage: %s", ve)
            return Resume(**_coerce_model_dict(_salvage_llm_dict(data, text)))

    try:
        return await run_with_providers(
            service_name="Parser",
            build_ollama_prompt=build_ollama_prompt,
            build_omniroute_prompt=build_omniroute_prompt,
            parse=parse,
            allow_mock=False,
        )
    except AIServiceUnavailable:
        # Parsing has no mock fallback — surface a clear service error.
        logger.error("AI parsing unavailable: configured providers could not process the resume")
        raise ParseError("AI parsing unavailable. Please try again later.") from None
