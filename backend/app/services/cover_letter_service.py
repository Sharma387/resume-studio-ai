import hashlib
import json
import uuid
from datetime import UTC, datetime

from app.core.logging import get_logger
from app.models.cover_letter import CoverLetter, CoverLetterRequest, CoverLetterTone
from app.services.ai_core import AIServiceUnavailable, extract_json
from app.services.ollama_service import compact_resume, run_with_providers
from app.services.prompt_service import PromptService
from app.services.repositories.factory import get_cover_letter_repository, get_resume_repository

logger = get_logger(__name__)

COVER_LETTER_SYSTEM_PROMPT = """You are a professional cover letter writer. Write a compelling, personalised cover letter for the candidate based on their resume and the job description.

Return ONLY a JSON object with exactly two fields:
- "subject": string — a concise email subject line
- "content": string — the full letter, 3-4 short paragraphs, using "\\n" for line breaks between paragraphs

Do not include any other fields or commentary outside the JSON."""


def _hash_jd(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


async def generate(resume_id: str, request: CoverLetterRequest, user_id: str) -> CoverLetter:
    resume = get_resume_repository().get_by_id(resume_id)
    if resume is None:
        raise FileNotFoundError(f"Resume '{resume_id}' not found")

    prompt_service = PromptService()
    resume_json = json.dumps(resume.model_dump(), indent=2, default=str)
    jd_hash = _hash_jd(request.job_description)
    tone = request.tone.value if isinstance(request.tone, CoverLetterTone) else request.tone

    async def build_omniroute_prompt() -> tuple[str, str]:
        return prompt_service.build_cover_letter_prompt(
            resume_json=resume_json,
            job_description=request.job_description,
            company_name=request.company_name,
            role_title=request.role_title,
            hiring_manager=request.hiring_manager,
            tone=tone,
        )

    async def build_ollama_prompt() -> tuple[str, str]:
        user_prompt = (
            f"Write a cover letter with tone: {tone}.\n\n"
            f"Candidate resume (JSON):\n{compact_resume(resume)}\n\n"
            f"Company: {request.company_name or 'the company'}\n"
            f"Role: {request.role_title or 'the position'}\n"
            f"Hiring manager: {request.hiring_manager or 'Hiring Manager'}\n\n"
            f"Job description:\n{request.job_description}"
        )
        return COVER_LETTER_SYSTEM_PROMPT, user_prompt

    try:
        letter = await run_with_providers(
            service_name="CoverLetter",
            build_ollama_prompt=build_ollama_prompt,
            build_omniroute_prompt=build_omniroute_prompt,
            parse=lambda raw: _parse_cover_letter(raw, resume_id, request, tone, user_id, jd_hash),
            allow_mock=False,
        )
    except AIServiceUnavailable as e:
        raise RuntimeError("Cover letter service unavailable after retries") from e

    if not letter.content.strip():
        raise RuntimeError("Cover letter service returned an empty letter")
    get_cover_letter_repository().save(letter)
    return letter


async def update(resume_id: str, letter_id: str, content: str, subject: str | None = None) -> CoverLetter:
    letter = get_cover_letter_repository().get_by_id(resume_id, letter_id)
    if letter is None:
        raise FileNotFoundError(f"Cover letter '{letter_id}' not found")
    letter.content = content
    if subject is not None:
        letter.subject = subject
    letter.updated_at = datetime.now(UTC).isoformat()
    get_cover_letter_repository().save(letter)
    return letter


def _parse_cover_letter(
    raw: str,
    resume_id: str,
    request: CoverLetterRequest,
    tone: str,
    user_id: str,
    jd_hash: str,
) -> CoverLetter:
    data = json.loads(extract_json(raw)) or {}
    return CoverLetter(
        id=uuid.uuid4().hex,
        resume_id=resume_id,
        company_name=request.company_name,
        hiring_manager=request.hiring_manager,
        role_title=request.role_title,
        tone=request.tone,
        user_id=user_id,
        content=data.get("content", ""),
        subject=data.get("subject"),
        ai_model=None,
        job_description_hash=jd_hash,
    )


async def regenerate(resume_id: str, letter_id: str) -> CoverLetter:
    letter = get_cover_letter_repository().get_by_id(resume_id, letter_id)
    if letter is None:
        raise FileNotFoundError(f"Cover letter '{letter_id}' not found")
    request = CoverLetterRequest(
        job_description=f"Regenerate: {letter.content[:100]}",
        company_name=letter.company_name,
        hiring_manager=letter.hiring_manager,
        role_title=letter.role_title,
        tone=letter.tone,
    )
    return await generate(resume_id, request)
