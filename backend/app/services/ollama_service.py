"""Shared local-Ollama fallback for AI services.

OmniRoute (the configured cloud AI gateway) is often unavailable in local dev,
so services that currently only talk to OmniRoute fail outright. This module
lets any service fall back to a locally-running Ollama model with a compact,
small-context prompt (local models are capped at small context windows and are
slow, so prompt size matters).

Model preference: deepseek-coder-v2:16b is ~2x faster than qwen2.5-coder:14b on
resume parsing and has a very large context window, so it is chosen first.
"""

import json
from collections.abc import Awaitable, Callable

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.models.resume import Resume
from app.services.ai_core.client import call_with_retry
from app.services.ai_core.exceptions import AIServiceUnavailable

logger = get_logger(__name__)

OLLAMA_BASE = "http://localhost:11434"
OLLAMA_TIMEOUT = 180
# num_predict is a MAX token cap, not a target — short outputs finish early.
# 3500 was too low: verbose generations (e.g. full-resume JSON) got truncated
# mid-document and failed to parse. 8192 covers the worst case at no cost to
# small outputs like match scores or cover letters.
OLLAMA_NUM_PREDICT = 8192


def _pick_ollama_model(models: list[str]) -> str | None:
    """Prefer the model that generates fastest for resume-shaped tasks."""
    if not models:
        return None

    def rank(m: str) -> int:
        ml = m.lower()
        if "deepseek" in ml:
            return 0
        if "qwen" in ml:
            return 1
        return 2

    return min(models, key=rank)


async def detect_ollama_model() -> str | None:
    """Return the best available Ollama model name, or None if Ollama is down."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{OLLAMA_BASE}/api/tags")
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])]
                model = _pick_ollama_model(models)
                if model:
                    logger.info("Using local Ollama model %s", model)
                    return model
    except Exception as e:
        logger.warning("Ollama discovery failed: %s", e)
    return None


async def generate_with_ollama(
    model: str,
    system: str,
    user: str,
    *,
    timeout: int = OLLAMA_TIMEOUT,
    num_predict: int = OLLAMA_NUM_PREDICT,
) -> str:
    """Single-shot Ollama completion. Raises AIServiceUnavailable on failure."""
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"num_predict": num_predict},
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(f"{OLLAMA_BASE}/v1/chat/completions", json=body, timeout=timeout)
        if r.status_code == 200:
            content = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            if content.strip():
                return content
        logger.warning("Ollama generation returned status %s", getattr(r, "status_code", "n/a"))
    except Exception as e:
        logger.warning("Ollama generation failed: %s", e)
    raise AIServiceUnavailable("local Ollama could not complete the request")


async def chat_ollama(
    system: str,
    user: str,
    *,
    timeout: int = OLLAMA_TIMEOUT,
    num_predict: int = OLLAMA_NUM_PREDICT,
    parse: Callable[[str], object] | None = None,
) -> object | None:
    """Run an Ollama call with model auto-selection.

    Returns the parsed result (via ``parse`` if given, else the raw text), or
    None when Ollama is unavailable or the output is unusable. Retries once
    when the model output fails to parse (LLMs occasionally emit malformed
    JSON), but does not re-run a failed generation (that would double the
    worst-case latency for an already-slow local model).
    """
    model = await detect_ollama_model()
    if model is None:
        return None
    try:
        raw = await generate_with_ollama(model, system, user, timeout=timeout, num_predict=num_predict)
    except AIServiceUnavailable:
        return None
    if parse is None:
        return raw
    try:
        return parse(raw)
    except Exception as e:
        logger.warning("Could not parse Ollama output; retrying once: %s", e)
    try:
        raw = await generate_with_ollama(model, system, user, timeout=timeout, num_predict=num_predict)
    except AIServiceUnavailable:
        return None
    try:
        return parse(raw)
    except Exception as e:
        logger.warning("Could not parse Ollama output on retry: %s", e)
        return None


def compact_resume(resume: Resume, max_chars: int = 6000) -> str:
    """A lean JSON representation of a resume for LLM prompts.

    Local models have small context windows, so the full ``model_dump()`` (which
    can be 15KB+) is replaced by the most match-relevant fields, with experience
    bullets trimmed.
    """
    data = {
        "full_name": resume.full_name,
        "professional_title": resume.professional_title,
        "email": resume.email,
        "phone": resume.phone,
        "location": resume.location,
        "summary": resume.summary,
        "experience": [
            {
                "company": e.company,
                "title": e.title,
                "location": e.location,
                "start": e.start_date,
                "end": e.end_date,
                "current": e.current,
                "description": (e.description or [])[:2],
            }
            for e in resume.experience
        ],
        "education": [
            {
                "institution": e.institution,
                "degree": e.degree,
                "field": e.field,
                "start": e.start_date,
                "end": e.end_date,
            }
            for e in resume.education
        ],
        "skills": [{"category": s.category, "skills": s.skills} for s in resume.skills],
        "certifications": [c.name for c in resume.certifications if c.name],
        "projects": [{"name": p.name, "description": (p.description or "")[:200]} for p in resume.projects][:5],
    }
    rendered = json.dumps(data, default=str)
    if len(rendered) > max_chars:
        # Trim harder: single bullet per experience entry
        data["experience"] = [
            {
                "company": e.company,
                "title": e.title,
                "start": e.start_date,
                "end": e.end_date,
                "current": e.current,
                "description": (e.description or [])[:1],
            }
            for e in resume.experience
        ]
        rendered = json.dumps(data, default=str)
    # Final safety: hard truncate (may cut JSON, but it's only prompt context)
    return rendered[:max_chars]


async def run_with_providers[T](
    *,
    service_name: str,
    build_ollama_prompt: Callable[[], Awaitable[tuple[str, str]]] | None = None,
    build_omniroute_prompt: Callable[[], Awaitable[tuple[str, str]]] | None = None,
    parse: Callable[[str], T],
    allow_mock: bool = False,
    mock_factory: Callable[[], T] | None = None,
) -> T:
    """Try AI providers in the order from ``settings.ai_provider_order``.

    Supported providers:
    - "ollama"      — local model via :func:`chat_ollama` (None result = failure)
    - "omniroute"   — cloud gateway via :func:`call_with_retry` (raises on failure)

    A provider without a matching prompt builder is skipped. When every provider
    fails and ``allow_mock`` is set, ``mock_factory`` is used as the last resort.
    """
    order = settings.ai_providers
    if not order:
        raise AIServiceUnavailable(f"{service_name}: no AI providers configured (set AI_PROVIDER_ORDER)")

    last_error: Exception | None = None
    for provider in order:
        try:
            if provider == "ollama" and build_ollama_prompt is not None:
                system, user = await build_ollama_prompt()
                result = await chat_ollama(system, user, parse=parse)
                if result is not None:
                    logger.info("%s handled by local Ollama", service_name)
                    return result
                logger.warning("%s: Ollama produced no usable output; trying next provider", service_name)
            elif provider == "omniroute" and build_omniroute_prompt is not None:
                logger.info("%s handled by OmniRoute", service_name)
                return await call_with_retry(build_omniroute_prompt, parse, service_name=service_name)
        except AIServiceUnavailable as e:
            last_error = e
            logger.warning("%s unavailable on provider '%s'; trying next", service_name, provider)

    if allow_mock and mock_factory is not None:
        logger.warning("%s failed on all providers; returning mock data", service_name)
        return mock_factory()

    raise AIServiceUnavailable(
        f"{service_name} failed on all configured providers ({settings.ai_provider_order})"
    ) from last_error