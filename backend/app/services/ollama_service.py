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
from app.services.ai_core.exceptions import AIServiceUnavailable, ResponseTruncated
from app.services.omniroute_service import OmniRouteService

logger = get_logger(__name__)

OLLAMA_BASE = "http://localhost:11434"
OLLAMA_TIMEOUT = 180
# num_predict is a MAX token cap, not a target — short outputs finish early.
# 3500 was too low: verbose generations (e.g. full-resume JSON) got truncated
# mid-document and failed to parse.
OLLAMA_NUM_PREDICT = 8192
# Pinned explicitly rather than inherited from the server: Ollama.app hard-codes
# 4096, and a request that silently defaults to a bigger window makes the model
# reserve memory it cannot spare, which starves the box and stalls generation.
OLLAMA_NUM_CTX = 4096


# Model families that emit hidden "thinking" tokens before answering. They are
# a poor fit for the structured JSON extraction this app does: the thinking is
# charged against num_predict, so a modest cap truncates the response mid-JSON
# and the parse fails, and neither the `think` flag nor
# `chat_template_kwargs.enable_thinking` suppressed it on Ollama 0.34.
_REASONING_FAMILIES = ("qwen3", "qwen3-vl", "deepseek-r1", "r1-", "magistral-small", "gpt-oss", "phi4-reasoning")


def _is_reasoning_model(name: str) -> bool:
    lowered = name.lower()
    return any(family in lowered for family in _REASONING_FAMILIES)


def _pick_ollama_model(models: list[str]) -> str | None:
    """Choose the local model to use, honouring an explicit preference first.

    ``AI_OLLAMA_MODEL`` pins a model by name and always wins. Otherwise two
    rules apply, in order:

    1. Avoid reasoning models, whose hidden thinking eats the token budget and
       truncates the JSON this app depends on.
    2. Among what is left, prefer the smallest: on a 16GB machine a 9GB model
       plus its context cache exhausts RAM and swap and generation crawls.
    """
    if not models:
        return None

    preferred = settings.ollama_model.strip()
    if preferred:
        for name in models:
            if name == preferred or name.split(":")[0] == preferred.split(":")[0]:
                return name

    try:
        response = httpx.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        sizes = {
            entry.get("name"): float(entry.get("size", 0)) / 1e9
            for entry in response.json().get("models", [])
        }
    except Exception:  # noqa: BLE001 - size is only a tiebreak hint
        sizes = {}

    # Prefer a non-reasoning model, then the smallest; unknown sizes sort last.
    return min(
        models,
        key=lambda name: (
            _is_reasoning_model(name),
            sizes.get(name, 99.0),
        ),
    )


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
    temperature: float | None = None,
) -> str:
    """Single-shot Ollama completion. Raises AIServiceUnavailable on failure.

    Uses Ollama's native ``/api/chat`` rather than the OpenAI-compatible
    ``/v1/chat/completions`` shim, for two reasons measured on this setup:

    * The shim ignored the request entirely and timed out, while the native
      endpoint returned in seconds.
    * Only the native endpoint honours ``chat_template_kwargs.enable_thinking``.
      Reasoning models (Qwen3 and friends) otherwise spend the whole
      ``num_predict`` budget on hidden thinking tokens and return an empty
      ``content`` — which is what made every parse chunk fail.

    ``temperature`` is left to the server's default unless a caller asks for
    something. Structured extraction wants it near zero, but the creative
    services (cover letter, interview coach) share this function and need
    variety — pinning it globally made every generated letter read the same.
    """
    options: dict = {"num_predict": num_predict, "num_ctx": OLLAMA_NUM_CTX}
    if temperature is not None:
        options["temperature"] = temperature
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        # Belt and braces: `think` is the documented switch, and the chat
        # template kwarg is what actually takes effect on this Ollama build.
        "think": False,
        "chat_template_kwargs": {"enable_thinking": False},
        "options": options,
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(f"{OLLAMA_BASE}/api/chat", json=body, timeout=timeout)
        if r.status_code == 200:
            payload = r.json()
            message = payload.get("message", {}) or {}

            # A generation that stopped because it reached ``num_predict`` comes
            # back with done_reason="length" and a body cut mid-structure. That
            # is not a bad response, it is a small cap, and it must not be
            # mistaken for one: handing this text on makes it fail JSON parsing
            # as an anonymous invalid response, which loses the whole section.
            # Raising here is what lets the caller retry with more room.
            done_reason = payload.get("done_reason")
            if done_reason == "length":
                raise ResponseTruncated(
                    "Ollama generation hit the num_predict cap and was cut off",
                    tokens=payload.get("eval_count"),
                    num_predict=num_predict,
                )

            content = (message.get("content") or "").strip()
            if content:
                return content
            # A model that ignored the thinking switch may still have emitted
            # usable output in its reasoning field; use it rather than nothing.
            fallback = (message.get("thinking") or "").strip()
            if fallback:
                return fallback
            logger.warning("Ollama returned an empty completion (thinking disabled)")
        else:
            logger.warning("Ollama generation returned status %s", getattr(r, "status_code", "n/a"))
    except ResponseTruncated:
        # Deliberately not folded into AIServiceUnavailable below: the model is
        # healthy and the answer is recoverable with a bigger cap, so reporting
        # this as an outage would send the caller down the wrong path.
        raise
    except httpx.TimeoutException:
        # Say so plainly: an empty exception message here previously hid a
        # 7-minute timeout behind "Ollama generation failed: ".
        logger.warning("Ollama generation timed out after %ss", timeout)
    except Exception as e:
        logger.warning("Ollama generation failed: %s: %s", type(e).__name__, e)
    raise AIServiceUnavailable("local Ollama could not complete the request")


async def chat_ollama(
    system: str,
    user: str,
    *,
    timeout: int = OLLAMA_TIMEOUT,
    num_predict: int = OLLAMA_NUM_PREDICT,
    temperature: float | None = None,
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
        raw = await generate_with_ollama(
            model, system, user, timeout=timeout, num_predict=num_predict, temperature=temperature
        )
    except ResponseTruncated:
        # Never reported as "unavailable": the cap was the problem, so the caller
        # has to be told to retry with a larger one rather than to give up.
        raise
    except AIServiceUnavailable:
        return None
    if parse is None:
        return raw
    try:
        return parse(raw)
    except Exception as e:
        logger.warning("Could not parse Ollama output; retrying once: %s", e)
    try:
        raw = await generate_with_ollama(
            model, system, user, timeout=timeout, num_predict=num_predict, temperature=temperature
        )
    except ResponseTruncated:
        raise
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


async def chat_providers(
    system: str,
    user: str,
    *,
    service_name: str = "AI",
    timeout: int | None = None,
    num_predict: int | None = None,
    temperature: float | None = None,
) -> str | None:
    """Raw-text completion dispatched over ``AI_PROVIDER_ORDER``.

    :func:`run_with_providers` needs a per-service prompt builder and a parser,
    which the section-by-section parse does not have: it holds a fixed
    ``(system, user)`` pair and wants the model's text back verbatim. This is the
    same ordering, reduced to that case, so a provider that is configured first
    is genuinely tried first.

    Returns the first provider's output, or None when every configured provider
    failed, so the caller can decide whether to retry or give up.
    """
    order = settings.ai_providers
    if not order:
        logger.warning("%s: no AI providers configured (set AI_PROVIDER_ORDER)", service_name)
        return None

    for provider in order:
        try:
            if provider == "omniroute":
                service = OmniRouteService(timeout=timeout or settings.omniroute_timeout)
                # One attempt only: the chunk loop owns retries, and letting both
                # retry multiplies the wall-clock wait for a dead gateway.
                service.max_retries = 0
                content = await service.send_prompt(system, user)
                if content and content.strip():
                    return content.strip()
                logger.warning("%s: OmniRoute returned no content; trying next provider", service_name)
            elif provider == "ollama":
                result = await chat_ollama(
                    system,
                    user,
                    timeout=timeout or OLLAMA_TIMEOUT,
                    **({"num_predict": num_predict} if num_predict is not None else {}),
                    temperature=temperature,
                )
                if isinstance(result, str) and result.strip():
                    return result
                logger.warning("%s: Ollama produced no usable output; trying next provider", service_name)
            else:
                logger.warning("%s: unknown provider %r in AI_PROVIDER_ORDER; skipping", service_name, provider)
        except ResponseTruncated:
            # Propagated rather than treated as a provider failure. Falling
            # through here would hand the truncated text to the next provider
            # and lose the signal that the cap needs raising; and retrying the
            # next provider is not the fix, because every provider here is
            # called with the same num_predict.
            raise
        except Exception as exc:
            logger.warning("%s: provider %r failed (%s); trying next", service_name, provider, exc)
    return None


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
