import json
import re
import time

from app.core.config import settings  # noqa: F401 — referenced by test monkeypatch
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.models.resume import Certification, Education, Experience, Project, Resume, Skill
from app.services.ai_core import AIServiceUnavailable, extract_json
from app.services.ollama_service import chat_ollama, run_with_providers
from app.services.prompt_service import PromptService
from app.services.resume_chunk_parser import merge_chunks, parse_chunk, verify_sections
from app.services.resume_chunker import chunk_resume

logger = get_logger(__name__)

# How long one completeness-audit call is expected to take, used to decide how
# many sections still fit in the remaining time budget. Measured at roughly 15s
# on a small local model; 30 leaves headroom for a busy machine.
_AUDIT_SECONDS_PER_SECTION = 30

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


def _gpa_as_float(value: object) -> float | None:
    """Coerce a model-supplied GPA to the 0.0-4.0 float the schema expects.

    Resumes express this many ways — ``3.8``, ``"3.8"``, ``"A-"``, ``"85%"``,
    ``"4.0/5.0"`` — and pydantic rejects anything non-numeric or out of range.
    Returning ``None`` for the unrepresentable ones keeps the education entry
    (and the rest of the resume) instead of failing the whole parse.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if 0.0 <= float(value) <= 4.0 else None
    text = str(value)
    # A ratio like "4.0/5.0" is on a different scale. Rescaling it would be a
    # guess, and reporting 4.0 for a 4-out-of-5 result would be plain wrong, so
    # only a 4-point denominator is interpreted.
    ratio = re.search(r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)", text)
    if ratio:
        denominator = float(ratio.group(2))
        if denominator == 4.0:
            number = float(ratio.group(1))
            return number if 0.0 <= number <= 4.0 else None
        return None
    # Pull the first number out of strings like "3.8" or "GPA: 3.8".
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return None  # e.g. "A-" — a letter grade has no numeric equivalent
    number = float(match.group(0))
    return number if 0.0 <= number <= 4.0 else None


def _prune_invalid_entries(data: dict, errors: list[dict]) -> bool:
    """Remove or blank the specific entries pydantic rejected.

    Returns True when something changed. A single malformed value — a letter
    grade in a numeric GPA field, a role missing its title — must cost only
    that value, not the entire parse; otherwise one bad field discards a
    resume that was otherwise parsed perfectly.
    """
    # pydantic reports every offending index against the *original* list, so
    # removals have to be applied highest-index-first. Deleting in report
    # order would shift the remaining targets and drop healthy entries.
    doomed: dict[str, set[int]] = {}
    changed = False
    for error in errors:
        loc = list(error.get("loc") or ())
        if not loc:
            continue
        # e.g. ("experience", 3, "title") -> drop that one role, keep the rest.
        if len(loc) >= 2 and isinstance(loc[0], str) and isinstance(loc[1], int):
            doomed.setdefault(loc[0], set()).add(loc[1])
            continue
        # e.g. ("gpa",) -> blank an optional scalar. Only report a change when
        # the value really differs, otherwise a required field that is already
        # None looks "repaired" forever and the loop never makes progress.
        if len(loc) == 1 and isinstance(loc[0], str) and loc[0] in data:
            if data[loc[0]] is not None:
                data[loc[0]] = None
                changed = True

    for field, indices in doomed.items():
        items = data.get(field)
        if not isinstance(items, list):
            continue
        for index in sorted(indices, reverse=True):
            if 0 <= index < len(items):
                del items[index]
                changed = True
    return changed


def _build_resume_lenient(data: dict) -> Resume | None:
    """Build a ``Resume``, shedding only the entries that fail validation.

    Repairs loop because dropping one entry can expose another: removing a
    list item shifts the indices of everything after it. Gives up after a few
    rounds rather than oscillating.
    """
    import copy

    from pydantic import ValidationError

    # Deep copy: the pruning below edits nested lists, and the caller's merged
    # dict is still used for the completeness audit afterwards.
    payload = _coerce_model_dict(copy.deepcopy(data))
    for entry in payload.get("education") or []:
        if isinstance(entry, dict) and "gpa" in entry:
            entry["gpa"] = _gpa_as_float(entry["gpa"])

    for _ in range(4):
        try:
            return Resume(**payload)
        except ValidationError as ve:
            errors = ve.errors()
            if not _prune_invalid_entries(payload, errors):
                logger.warning("Merged resume could not be validated: %s", ve)
                return None
            logger.info("Dropped %d invalid entries while merging the parsed resume", len(errors))
        except Exception as ve:  # noqa: BLE001
            logger.warning("Merged resume could not be validated: %s", ve)
            return None
    logger.warning("Merged resume still invalid after repeated repairs")
    return None


_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
_LINKEDIN_RE = re.compile(r"(?:https?://)?(?:[\w-]+\.)?linkedin\.com/[\w-]+/?", re.I)


def _correct_identity_from_source(data: dict, text: str) -> dict:
    """Override identity fields the model transcribed wrongly.

    The contact header is a *transcription* task, not a reasoning one, and a
    small local model reliably gets it subtly wrong — on the real resume it
    rendered the email as ``sharma.rajasekhar@`` and invented a location
    ("Bangalore" for a candidate based in Auckland). The extracted text is
    authoritative for these fields, so a value the model produced that cannot
    be found verbatim in the source is replaced by the one that can.

    Only fields that are actually present in the source are touched; nothing is
    invented here, and a correct model output is left exactly as it was.
    """
    header = "\n".join(text.splitlines()[:6])

    email_match = _EMAIL_RE.search(text)
    if email_match and str(data.get("email") or "").strip().lower() != email_match.group(0).lower():
        logger.info("Using the email from the source text (%s)", email_match.group(0))
        data["email"] = email_match.group(0)

    # A phone number is likewise a literal token.
    model_phone = str(data.get("phone") or "").strip()
    if model_phone:
        digits = re.sub(r"\D", "", model_phone)
        # Accept a match on digits alone: punctuation varies between the model
        # and the source, but the digits must be the same number.
        if len(digits) >= 8 and digits not in re.sub(r"\D", "", text):
            phone_match = _PHONE_RE.search(header)
            if phone_match:
                logger.info("Using the phone number from the source text")
                data["phone"] = phone_match.group(0).strip()

    # A linkedin URL must appear in the source; otherwise drop the invention.
    linkedin = str(data.get("linkedin") or "").strip()
    if linkedin and "linkedin.com" not in text.lower():
        logger.info("Dropping a linkedin URL that is not in the source text")
        data["linkedin"] = None

    # Location is free text, so it is only corrected when the model's value is
    # absent from the *contact line* and that line offers an unambiguous
    # candidate. Scoping the search to the contact line matters: an early
    # role's location ("Bangalore" on the Amadeus job) appears later in the
    # body, so a whole-document search would wrongly consider the model's
    # answer verified.
    location = str(data.get("location") or "").strip()
    if location:
        # The contact line is the one carrying an email address. Matching on a
        # separator alone would pick the job-title line, which also uses "|".
        contact_line = ""
        for line in text.splitlines()[:6]:
            if "@" in line:
                contact_line = line
                break

        if contact_line and location.lower() not in contact_line.lower():
            segments = [s.strip() for s in re.split(r"[|•·]", contact_line)]
            name = str(data.get("full_name") or "").strip()
            for segment in segments:
                if not segment or "@" in segment or "linkedin" in segment.lower():
                    continue
                # Skip the candidate's own name and a job title.
                if name and segment.upper() == name.upper():
                    continue
                if re.search(r"\b(manager|lead|director|engineer|consultant|specialist|officer)\b",
                             segment, re.I):
                    continue
                # A location is words and commas, not digits or a bare acronym.
                if not re.search(r"[A-Za-z]{3}", segment) or re.search(r"\d{4,}", segment):
                    continue
                if 2 <= len(segment) <= 60:
                    logger.info("Using the location from the source text (%s)", segment)
                    data["location"] = segment
                    return data
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
        # LLMs often emit URLs without a scheme, hallucinate the email, or put
        # a letter grade in the numeric GPA field. Repair what we can, and shed
        # only the entries that stay broken, rather than losing the whole
        # document to one bad value.
        resume = _build_resume_lenient(_salvage_llm_dict(data, text))
        if resume is None:
            # Nothing could be salvaged. Re-run strict validation purely to
            # raise the canonical ValidationError, which is the signal the
            # provider dispatcher uses to retry the generation.
            Resume(**_coerce_model_dict(data))
            raise ValueError("parser output could not be validated after repair")  # pragma: no cover
        return resume

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
    # Near-zero temperature: this is transcription, not composition, so a
    # wandering model can only invent detail.
    async def call(system: str, user: str) -> str:
        result = await chat_ollama(
            system,
            user,
            timeout=settings.parse_chunk_timeout,
            num_predict=settings.parse_chunk_num_predict,
            temperature=0.1,
        )
        if result is None:
            raise AIServiceUnavailable("no provider returned output for chunk parse")
        return result if isinstance(result, str) else str(result)

    results: list[tuple[str, dict]] = []
    chunks_used: list[dict] = []
    consecutive_failures = 0
    budget = settings.parse_time_budget
    started = time.monotonic()
    parsed = 0

    for index, chunk in enumerate(chunks, start=1):
        if time.monotonic() - started > budget:
            logger.warning(
                "Parse time budget (%ss) reached after %d/%d chunks; returning partial result",
                budget, index - 1, len(chunks),
            )
            break

        section = chunk["section"]
        data = await parse_chunk(section, chunk["text"], call)
        if not data:
            # Retry only while the failures look isolated. A run of failures
            # means the provider is unhealthy, and retrying each chunk just
            # multiplies the wait by two for no gain.
            if consecutive_failures < settings.parse_max_consecutive_failures:
                logger.info("Chunk %d/%d (%s) produced nothing; retrying once", index, len(chunks), section)
                data = await parse_chunk(section, chunk["text"], call)

        if data:
            consecutive_failures = 0
            parsed += 1
        else:
            consecutive_failures += 1
            if consecutive_failures >= settings.parse_max_consecutive_failures:
                logger.error(
                    "Abandoning parse: %d chunks failed in a row (%d/%d done)",
                    consecutive_failures, parsed, len(chunks),
                )
                break
        results.append((section, data))
        chunks_used.append(chunk)

    merged = merge_chunks(results)
    _correct_identity_from_source(merged, text)
    if not any(merged.get(key) for key in ("full_name", "summary", "experience", "education")):
        logger.warning("Chunked parse produced nothing usable (%d/%d chunks)", parsed, len(chunks))
        return None

    if parsed < len(chunks):
        logger.warning(
            "Partial parse: %d/%d sections succeeded; the result is incomplete",
            parsed, len(chunks),
        )

    # Best-effort completeness audit. Done per section against the exact text
    # each section came from: auditing the whole resume in one call overflows
    # the model context and produces false "missing" reports for facts that are
    # in the output. Off by default because it roughly doubles the parse time
    # (one extra call per section) — enable it to check fidelity on a resume
    # you suspect is being parsed incompletely.
    if settings.parse_verify_completeness:
        remaining = budget - (time.monotonic() - started)
        if remaining < _AUDIT_SECONDS_PER_SECTION:
            logger.info(
                "Completeness audit skipped: only %ds of the %ds budget remains, "
                "and it needs one model call per section",
                max(0, int(remaining)), budget,
            )
        else:
            pairs = [
                (section, chunk["text"], data)
                for (section, data), chunk in zip(results, chunks_used)
                if data
            ]
            # One extra call per section, so cover only what still fits. A
            # fidelity check is never worth making the user wait indefinitely.
            max_calls = int(remaining // _AUDIT_SECONDS_PER_SECTION)
            findings = await verify_sections(pairs, call, max_calls=max_calls)
            if findings:
                logger.warning("Completeness audit flagged %d possibly-missing facts", len(findings))
                for fact in findings:
                    logger.warning("  possibly missing: %s", fact[:160])

    try:
        return _build_resume_lenient(merged)
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
