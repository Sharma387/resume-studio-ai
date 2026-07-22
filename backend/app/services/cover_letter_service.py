import hashlib
import json
import uuid
from datetime import datetime, timezone

from app.models.resume import Resume
from app.models.cover_letter import CoverLetter, CoverLetterRequest, CoverLetterTone
from app.services.prompt_service import PromptService
from app.services.ai_core import extract_json, call_with_retry, AIServiceUnavailable
from app.services.storage_service import (
    load_resume,
    save_cover_letter,
    load_cover_letter,
    list_cover_letters,
    delete_cover_letter,
)

from app.core.logging import get_logger
logger = get_logger(__name__)


def _hash_jd(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


async def generate(resume_id: str, request: CoverLetterRequest) -> CoverLetter:
    resume = load_resume(resume_id)
    if resume is None:
        raise FileNotFoundError(f"Resume '{resume_id}' not found")

    prompt_service = PromptService()
    resume_json = json.dumps(resume.model_dump(), indent=2, default=str)
    jd_hash = _hash_jd(request.job_description)

    async def build() -> tuple[str, str]:
        return prompt_service.build_cover_letter_prompt(
            resume_json=resume_json,
            job_description=request.job_description,
            company_name=request.company_name,
            role_title=request.role_title,
            hiring_manager=request.hiring_manager,
            tone=request.tone.value if isinstance(request.tone, CoverLetterTone) else request.tone,
        )

    def parse(raw: str) -> CoverLetter:
        cleaned = extract_json(raw)
        data = json.loads(cleaned)
        return CoverLetter(
            id=uuid.uuid4().hex,
            resume_id=resume_id,
            company_name=request.company_name,
            hiring_manager=request.hiring_manager,
            role_title=request.role_title,
            tone=request.tone,
            content=data.get("content", ""),
            subject=data.get("subject"),
            ai_model=None,
            job_description_hash=jd_hash,
        )

    try:
        letter = await call_with_retry(build, parse, service_name="CoverLetter")
        save_cover_letter(letter)
        return letter
    except AIServiceUnavailable as e:
        raise RuntimeError("Cover letter service unavailable after retries") from e


async def update(resume_id: str, letter_id: str, content: str, subject: str | None = None) -> CoverLetter:
    letter = load_cover_letter(resume_id, letter_id)
    if letter is None:
        raise FileNotFoundError(f"Cover letter '{letter_id}' not found")
    letter.content = content
    if subject is not None:
        letter.subject = subject
    letter.updated_at = datetime.now(timezone.utc).isoformat()
    save_cover_letter(letter)
    return letter


async def regenerate(resume_id: str, letter_id: str) -> CoverLetter:
    letter = load_cover_letter(resume_id, letter_id)
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
