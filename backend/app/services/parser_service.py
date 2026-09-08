import json

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.models.resume import Certification, Education, Experience, Project, Resume, Skill
from app.services.ai_core import AIServiceUnavailable, call_with_retry, extract_json
from app.services.prompt_service import PromptService
import httpx

logger = get_logger(__name__)


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
    # ── Ollama-first probe ──────────────────────────────────────────────
    # Discover available local Ollama models
    ollama_models: list[str] = []
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get("http://localhost:11434/api/tags")
            if r.status_code == 200:
                data = r.json()
                ollama_models = [m["name"] for m in data.get("models", [])]
    except Exception as e:
        logger.warning("Ollama discovery failed: %s", e)

    # Use the first available Ollama model (prefer qwen2 if present)
    ollama_model: str | None = None
    for model in ollama_models or []:
        if "qwen" in model.lower():
            ollama_model = model
            break
    if ollama_model is None and ollama_models:
        ollama_model = ollama_models[0]

    # Probe the chosen Ollama model with a tiny completion
    ollama_success: bool | None = None
    ollama_error: str | None = None
    parsed_resume: Resume | None = None
    if ollama_model:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                body = json.dumps(
                    {"model": ollama_model, "messages": [{"role": "user", "content": "Reply with the single word: OK"}], "stream": False}
                )
                r = await client.post("http://localhost:11434/v1/chat/completions", headers={"Content-Type": "application/json"}, data=body, timeout=5)
                if r.status_code == 200:
                    d = r.json()
                    content = d.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    if content.upper() == "OK":
                        ollama_success = True
                        # Try to parse as Resume
                        try:
                            cleaned = extract_json(d.get("choices", [{}])[0].get("message", {}).get("content", ""))
                            data = json.loads(cleaned)
                            parsed_resume = Resume(**_coerce_model_dict(data))
                        except Exception:
                            ollama_success = True  # completion succeeded, just not a valid Resume schema
                    else:
                        ollama_success = False
                else:
                    ollama_success = False
                ollama_error = f"HTTP {r.status_code}"
        except Exception as e:
            ollama_success = False
            ollama_error = str(e)

    # ── Fallthrough: existing OmniRoute path ─────────────────────────────
    if not ollama_success:
        # Existing call_with_retry logic
        prompt_service = PromptService()
        schema = json.dumps(Resume.model_json_schema(), indent=2)

        async def build() -> tuple[str, str]:
            return prompt_service.build_prompt(text, schema)

        def parse(raw: str) -> Resume:
            cleaned = extract_json(raw)
            data = json.loads(cleaned)
            return Resume(**_coerce_model_dict(data))

        try:
            return await call_with_retry(build, parse, service_name="Parser")
        except AIServiceUnavailable:
            # No mock data – raise a clear service-unavailable error
            logger.error(
                "AI parsing unavailable: Ollama and OmniRoute could not process the resume",
                ollama_model=ollama_model,
                ollama_error=ollama_error,
            )
            raise ParseError("AI parsing unavailable. Please try again later.") from None
    else:
        # Ollama succeeded – return the real parsed resume
        if parsed_resume is not None:
            logger.info("Ollama parsing succeeded", model=ollama_model, name=parsed_resume.full_name)
            return parsed_resume
        # If we got here without a parsed resume but ollama_success=True,
        # still try the existing path as fallback
        prompt_service = PromptService()
        schema = json.dumps(Resume.model_json_schema(), indent=2)

        async def build() -> tuple[str, str]:
            return prompt_service.build_prompt(text, schema)

        def parse(raw: str) -> Resume:
            cleaned = extract_json(raw)
            data = json.loads(cleaned)
            return Resume(**_coerce_model_dict(data))

        try:
            return await call_with_retry(build, parse, service_name="Parser")
        except AIServiceUnavailable:
            logger.error(
                "AI parsing unavailable: Ollama and OmniRoute could not process the resume",
                ollama_model=ollama_model,
                ollama_error=ollama_error,
            )
            raise ParseError("AI parsing unavailable. Please try again later.") from None
