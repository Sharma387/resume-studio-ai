import json
import uuid

from pydantic import ValidationError

from app.core.logging import get_logger
from app.models.resume import Resume
from app.models.writer import ResumeSuggestion, WriterRequest
from app.services.ai_core import AIServiceUnavailable, extract_json_array
from app.services.ollama_service import compact_resume, run_with_providers
from app.services.prompt_service import PromptService
from app.services.repositories.factory import get_resume_repository, get_suggestion_repository

logger = get_logger(__name__)


QUICK_ACTIONS = {
    "strengthen": "Strengthen all bullet points with more impactful language and action verbs.",
    "summary": "Rewrite the professional summary to be more compelling and concise.",
    "grammar": "Fix any grammar, spelling, or punctuation issues throughout the resume.",
    "skills": "Suggest relevant skills I may have missed based on my experience.",
    "achievements": "Add quantifiable achievements and metrics to my experience descriptions.",
    "full": "Do a complete review of my resume and suggest every improvement you can find.",
}

WRITER_SYSTEM_PROMPT = """You are an expert resume writer. Improve the resume based on the user's request. Return ONLY a JSON array of suggestion objects with fields:
- suggestion_type: "phrasing", "grammar", "skills", "summary", "achievement", "completeness", "keyword", or "full_review"
- section: string (resume section: experience, summary, skills, education, etc.)
- field_path: string or null (JSON path to the target field, e.g. "experience.0.description.0")
- original_text: string (existing text being replaced; "" when adding new content)
- suggested_text: string (the improved replacement text)
- reason: string (why this change helps)
- confidence: number from 0 to 1

Do not include id, resume_id, user_id, or created_at — the backend manages those. Use lowercase null. Return 3-6 high-value suggestions."""


async def suggest(resume_id: str, request: WriterRequest, user_id: str) -> list[ResumeSuggestion]:
    resume = get_resume_repository().get_by_id(resume_id)
    if resume is None:
        raise FileNotFoundError(f"Resume '{resume_id}' not found")

    prompt_service = PromptService()
    resume_json = json.dumps(resume.model_dump(), indent=2, default=str)

    async def build_omniroute_prompt() -> tuple[str, str]:
        return prompt_service.build_writer_prompt(resume_json, request.prompt, request.focus_section)

    async def build_ollama_prompt() -> tuple[str, str]:
        focus = request.focus_section or "full resume"
        user_prompt = (
            f"Candidate resume (JSON):\n{compact_resume(resume)}\n\n"
            f"User request: {request.prompt}\n"
            f"Focus section: {focus}"
        )
        return WRITER_SYSTEM_PROMPT, user_prompt

    def parse(raw: str) -> list[ResumeSuggestion]:
        cleaned = extract_json_array(raw)
        data = json.loads(cleaned)
        if not isinstance(data, list):
            data = [data]

        suggestions = []
        for item in data:
            try:
                sug = ResumeSuggestion(
                    id=uuid.uuid4().hex,
                    resume_id=resume_id,
                    user_id=user_id,
                    **{
                        k: v
                        for k, v in item.items()
                        if k in ResumeSuggestion.model_fields and k not in ("id", "resume_id", "user_id", "created_at")
                    },
                )
                get_suggestion_repository().save(sug)
                suggestions.append(sug)
            except ValidationError as e:
                logger.warning("Skipping invalid suggestion: %s", e)
        return suggestions

    try:
        return await run_with_providers(
            service_name="Writer",
            build_ollama_prompt=build_ollama_prompt,
            build_omniroute_prompt=build_omniroute_prompt,
            parse=parse,
            allow_mock=False,
        )
    except AIServiceUnavailable as e:
        raise RuntimeError("AI writer service unavailable after retries") from e


async def accept_suggestion(resume_id: str, suggestion_id: str, user_id: str) -> Resume:
    resume = get_resume_repository().get_by_id(resume_id)
    if resume is None:
        raise FileNotFoundError(f"Resume '{resume_id}' not found")

    suggestion = get_suggestion_repository().get_by_id(resume_id, suggestion_id, user_id)
    if suggestion is None:
        raise FileNotFoundError(f"Suggestion '{suggestion_id}' not found")

    if suggestion.field_path:
        parts = suggestion.field_path.replace("[", ".").replace("]", "").split(".")
        current = resume
        for i, part in enumerate(parts):
            if part.isdigit():
                current = current[int(part)]
            elif hasattr(current, part):
                if i == len(parts) - 1:
                    setattr(current, part, suggestion.suggested_text)
                else:
                    current = getattr(current, part)
            elif isinstance(current, list) and part.lstrip("-").isdigit():
                idx = int(part)
                if i == len(parts) - 1:
                    current[idx] = suggestion.suggested_text
                else:
                    current = current[idx]
    else:
        if suggestion.section == "summary":
            resume.summary = suggestion.suggested_text

    get_resume_repository().save(resume_id, resume)
    get_suggestion_repository().update(resume_id, suggestion_id, user_id=user_id, status="accepted")
    return resume


async def reject_suggestion(resume_id: str, suggestion_id: str, user_id: str) -> None:
    result = get_suggestion_repository().update(resume_id, suggestion_id, user_id=user_id, status="rejected")
    if result is None:
        raise FileNotFoundError(f"Suggestion '{suggestion_id}' not found")


async def regenerate_suggestion(resume_id: str, suggestion_id: str) -> ResumeSuggestion:
    suggestion = get_suggestion_repository().get_by_id(resume_id, suggestion_id)
    if suggestion is None:
        raise FileNotFoundError(f"Suggestion '{suggestion_id}' not found")

    request = WriterRequest(
        prompt=f"Improve the {suggestion.section} section, specifically: {suggestion.reason}",
        focus_section=suggestion.section,
    )
    results = await suggest(resume_id, request, suggestion.user_id)
    return results[0] if results else suggestion
