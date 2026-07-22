import json
import logging
import uuid

from pydantic import ValidationError

from app.models.resume import Resume
from app.models.writer import ResumeSuggestion, WriterRequest
from app.services.prompt_service import PromptService
from app.services.ai_core import extract_json_array, call_with_retry, AIServiceUnavailable
from app.services.storage_service import (
    load_resume,
    save_resume,
    save_writer_suggestion,
    load_writer_suggestion,
    update_writer_suggestion,
)

logger = logging.getLogger(__name__)


QUICK_ACTIONS = {
    "strengthen": "Strengthen all bullet points with more impactful language and action verbs.",
    "summary": "Rewrite the professional summary to be more compelling and concise.",
    "grammar": "Fix any grammar, spelling, or punctuation issues throughout the resume.",
    "skills": "Suggest relevant skills I may have missed based on my experience.",
    "achievements": "Add quantifiable achievements and metrics to my experience descriptions.",
    "full": "Do a complete review of my resume and suggest every improvement you can find.",
}


async def suggest(resume_id: str, request: WriterRequest) -> list[ResumeSuggestion]:
    resume = load_resume(resume_id)
    if resume is None:
        raise FileNotFoundError(f"Resume '{resume_id}' not found")

    prompt_service = PromptService()
    resume_json = json.dumps(resume.model_dump(), indent=2, default=str)

    async def build() -> tuple[str, str]:
        return prompt_service.build_writer_prompt(resume_json, request.prompt, request.focus_section)

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
                    **{k: v for k, v in item.items() if k in ResumeSuggestion.model_fields and k not in ("id", "resume_id", "created_at")},
                )
                save_writer_suggestion(sug)
                suggestions.append(sug)
            except ValidationError as e:
                logger.warning("Skipping invalid suggestion: %s", e)
        return suggestions

    try:
        return await call_with_retry(build, parse, service_name="Writer")
    except AIServiceUnavailable as e:
        raise RuntimeError("AI writer service unavailable after retries") from e


async def accept_suggestion(resume_id: str, suggestion_id: str) -> Resume:
    resume = load_resume(resume_id)
    if resume is None:
        raise FileNotFoundError(f"Resume '{resume_id}' not found")

    suggestion = load_writer_suggestion(resume_id, suggestion_id)
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

    save_resume(resume_id, resume)
    update_writer_suggestion(resume_id, suggestion_id, status="accepted")
    return resume


async def reject_suggestion(resume_id: str, suggestion_id: str) -> None:
    result = update_writer_suggestion(resume_id, suggestion_id, status="rejected")
    if result is None:
        raise FileNotFoundError(f"Suggestion '{suggestion_id}' not found")


async def regenerate_suggestion(resume_id: str, suggestion_id: str) -> ResumeSuggestion:
    suggestion = load_writer_suggestion(resume_id, suggestion_id)
    if suggestion is None:
        raise FileNotFoundError(f"Suggestion '{suggestion_id}' not found")

    request = WriterRequest(
        prompt=f"Improve the {suggestion.section} section, specifically: {suggestion.reason}",
        focus_section=suggestion.section,
    )
    results = await suggest(resume_id, request)
    return results[0] if results else suggestion
