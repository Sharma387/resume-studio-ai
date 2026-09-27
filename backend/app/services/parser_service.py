import json

from app.core.config import settings  # noqa: F401 — referenced by test monkeypatch
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.models.resume import Certification, Education, Experience, Project, Resume, Skill
from app.services.ai_core import AIServiceUnavailable, extract_json
from app.services.ollama_service import chat_ollama, run_with_providers
from app.services.prompt_service import PromptService
from app.services.resume_chunk_parser import merge_chunks, parse_chunk, verify_completeness
from app.services.resume_chunker import chunk_resume

logger = get_logger(__name__)

# Compact field instructions sent to Ollama instead of the full 10KB+ JSON
# schema. Local models have small context windows and slower generation, so a
# short prompt parses faster and still validates against the real Resume model
# server-side.
OLLAMA_SCHEMA_INSTRUCTIONS = """You are a resume parser. Convert the resume text into a single JSON object (no markdown, no commentary).

Be COMPLETE AND FAITHFUL: capture EVERY detail. Never omit, merge, shorten, or paraphrase any role, bullet point, achievement, certification, award, or education entry. Preserve numbers, dates, amounts (e.g. $5M+, 60+, 25+), acronyms, and metric details exactly as written.

Return ONLY a JSON object with these fields:

Top-level strings:
- full_name, email, phone, location, linkedin, github, website, professional_title, summary
  - summary: the resume's professional summary/profile paragraph, verbatim.
  - linkedin/github/website: full URL when present (e.g. "https://linkedin.com/in/..."); null otherwise.

Arrays (use [] and null when absent):
- education: [{"institution", "degree", "field", "start_date", "end_date", "gpa", "achievements": []}]
  - achievements: EVERY bullet listed under the degree, verbatim.
- experience: [{"company", "title", "location", "start_date", "end_date", "current": bool, "description": []}]
  - Include EVERY role in the resume (all jobs, past and early-career roles, and study roles), in resume order.
  - description: EVERY bullet/achievement for the role, verbatim — do not truncate or merge.
- projects: [{"name", "description", "url", "technologies": []}]
- skills: [{"category", "skills": []}] — group skills exactly as the resume groups them.
- certifications: [{"name", "issuer", "date", "url", "category", "values": []}]
  - One entry per named credential (e.g. PRINCE2 Practitioner, Certified Scrum Master, ITIL) with issuer if given.
  - ALSO one entry per grouping heading (e.g. category "AI & Emerging Technologies", values = each listed item).
- awards: [{"name", "issuer", "date", "description"}] — EVERY award; include the year in name or date and the issuing company.
- languages: [{"name", "proficiency"}]

Use lowercase null (not None) for missing values."""


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


async def _parse_single_shot(text: str) -> Resume:
    """Parse the entire resume in one AI call (legacy path)."""
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

    return await run_with_providers(
        service_name="Parser",
        build_ollama_prompt=build_ollama_prompt,
        build_omniroute_prompt=build_omniroute_prompt,
        parse=parse,
        allow_mock=False,
    )


async def _parse_chunked(text: str) -> Resume | None:
    """Parse the resume section-by-section and merge the results.

    Each section is a small, independent AI call, so the model produces a
    small JSON per call. This is both far faster on a local model and far
    more complete than a single call, which overruns the context window and
    truncates roles/bullets. Returns None if no usable provider is present.
    """
    chunks = chunk_resume(text, max_chars=settings.parse_max_chunk_chars)
    if not chunks:
        return None

    # Thin wrapper over the provider dispatch that returns raw text.
    async def call(system: str, user: str) -> str:
        result = await chat_ollama(
            system,
            user,
            timeout=settings.parse_chunk_timeout,
            num_predict=settings.parse_chunk_num_predict,
        )
        if result is None:
            raise AIServiceUnavailable("no provider returned output for chunk parse")
        return result if isinstance(result, str) else str(result)

    results: list[tuple[str, dict]] = []
    for chunk in chunks:
        section = chunk["section"]
        data = await parse_chunk(section, chunk["text"], call)
        if not data:
            # A single dropped chunk silently loses a whole section, so give it
            # one more chance before moving on.
            logger.info("Chunk %s produced nothing; retrying once", section)
            data = await parse_chunk(section, chunk["text"], call)
        results.append((section, data))

    merged = merge_chunks(results)
    if not (merged.get("full_name") and merged.get("email")):
        logger.warning("Chunked parse produced no identity; trying single-shot")
        return None

    # Best-effort completeness audit against the source text.
    if settings.parse_verify_completeness:
        missing = await verify_completeness(text, merged, call)
        if missing:
            logger.warning("Completeness audit flagged %d possibly-missing facts", len(missing))
            for fact in missing:
                logger.warning("  possibly missing: %s", fact[:160])

    try:
        return Resume(**_coerce_model_dict(merged))
    except Exception as ve:  # noqa: BLE001
        logger.warning("Chunked merge failed validation: %s", ve)
        return None


async def parse_resume(text: str) -> Resume:
    if settings.parse_chunked:
        try:
            resume = await _parse_chunked(text)
            if resume is not None:
                return resume
            logger.warning("Chunked parse returned nothing; falling back to single-shot")
        except AIServiceUnavailable:
            if not settings.parse_chunk_fallback_single_shot:
                raise
            logger.warning("Chunked parse hit no provider; falling back to single-shot")
        except Exception as e:  # noqa: BLE001 - never let chunking break parsing
            logger.warning("Chunked parse failed (%s); falling back to single-shot", e)

    if not settings.parse_chunked and not settings.parse_chunk_fallback_single_shot:
        return await _parse_single_shot(text)

    try:
        return await _parse_single_shot(text)
    except AIServiceUnavailable:
        # Parsing has no mock fallback — surface a clear service error.
        logger.error("AI parsing unavailable: configured providers could not process the resume")
        raise ParseError("AI parsing unavailable. Please try again later.") from None
