"""AI Model Router — automatically discovers, probes, and ranks available AI models
across OmniRoute and local Ollama providers, with failover and caching."""

import asyncio
import json
import time

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.services.ai_core.exceptions import AIServiceUnavailable

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Model candidate data class
# ---------------------------------------------------------------------------


class ModelCandidate:
    """A candidate AI model from a specific provider, with probe metadata."""

    __slots__ = (
        "provider",
        "model",
        "reachable",
        "latency_ms",
        "http_status",
        "error",
        "content",
        "last_checked",
    )

    def __init__(
        self,
        provider: str,
        model: str,
        reachable: bool | None = None,
        latency_ms: float | None = None,
        http_status: int | None = None,
        error: str | None = None,
        content: str | None = None,
        last_checked: float | None = None,
    ):
        self.provider = provider
        self.model = model
        self.reachable = reachable
        self.latency_ms = latency_ms
        self.http_status = http_status
        self.error = error
        self.content = content
        self.last_checked = last_checked or time.time()


# ---------------------------------------------------------------------------
# Provider specification
# ---------------------------------------------------------------------------


class ProviderSpec:
    """Specification for an AI provider (OmniRoute or Ollama)."""

    __slots__ = ("name", "base_url", "models", "api_key")

    def __init__(self, name: str, base_url: str, models: list[str], api_key: str = ""):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.models = models  # list of candidate model ids
        self.api_key = api_key


# ---------------------------------------------------------------------------
# Singleton router instance (created on first access)
# ---------------------------------------------------------------------------

_router: "AIModelRouter | None" = None


async def get_router() -> "AIModelRouter":
    global _router
    if _router is None:
        _router = AIModelRouter()
    return _router


# ---------------------------------------------------------------------------
# AIModelRouter class
# ---------------------------------------------------------------------------


class AIModelRouter:
    """Discovers AI model candidates from OmniRoute and Ollama, probes them,
    ranks them by reachability + latency, and dispatches completions with
    automatic failover."""

    def __init__(self):
        # Cache of ranked candidates; refreshed every ai_route_cache_ttl seconds.
        self._cache: list[ModelCandidate] | None = None
        self._cache_at: float = 0.0
        # Track which candidates have been marked as failed (for quick skip).
        self._failed: set[tuple[str, str]] = set()  # (provider, model)
        # Provider specifications (set at init; immutable).
        self.providers: list[ProviderSpec] = self._default_providers()

    # ── Provider definitions ──────────────────────────────────────────────

    def _default_providers(self) -> list[ProviderSpec]:
        """Build the list of providers to query."""
        # OmniRoute
        omni_url = settings.omniroute_api_url.rstrip("/v1")  # e.g. http://localhost:20128
        omni_models: list[str] = []
        # Always include the configured model as a concrete candidate
        if settings.omniroute_model and settings.omniroute_model not in (
            "auto/best-fast",
            "auto/best-coding",
            "auto/best-reasoning",
        ):
            omni_models.append(settings.omniroute_model)
        # Limit to probe limit
        omni_models = omni_models[: settings.ai_probe_limit]

        # Ollama — we'll fill model names during discover_candidates from /api/tags
        ollama_models: list[str] = []

        return [
            ProviderSpec(
                name="omniroute",
                base_url=omni_url,
                models=omni_models,
                api_key=settings.omniroute_api_key or "not-needed",
            ),
            ProviderSpec(
                name="ollama",
                base_url=settings.ollama_api_url.rstrip("/v1/chat/completions"),
                models=ollama_models,
                api_key="",
            ),
        ]

    # ── Candidate discovery ───────────────────────────────────────────────

    async def discover_candidates(self) -> list[ModelCandidate]:
        """Probe all candidate models from both providers and return ranked list."""
        async with asyncio.Semaphore(settings.ai_probe_limit or 10):
            omni_tasks = []
            for m in self.providers[0].models:
                if m:
                    omni_tasks.append(self._probe_omni(self.providers[0], m))
            ollama_tasks = []
            for m in self.providers[1].models:
                if m:
                    ollama_tasks.append(self._probe_ollama(self.providers[1], m))

            # If no concrete models listed (e.g. auto combos), probe the configured omni model as health check.
            if not omni_tasks:
                omni_tasks.append(self._probe_omni(self.providers[0], settings.omniroute_model or "auto/best-fast"))

            results: list[ModelCandidate] = []
            omni_results: list[ModelCandidate | BaseException] = await asyncio.gather(
                *omni_tasks, return_exceptions=True
            )
            for r in omni_results:
                if isinstance(r, BaseException):
                    logger.warning("OmniRoute probe error", error=str(r))
                else:
                    results.append(r)

            ollama_results: list[ModelCandidate | BaseException] = await asyncio.gather(
                *ollama_tasks, return_exceptions=True
            )
            for r in ollama_results:
                if isinstance(r, BaseException):
                    logger.warning("Ollama probe error", error=str(r))
                else:
                    results.append(r)

            # Rank: omni working first (by latency), then ollama working (by latency).
            working = [c for c in results if c.reachable]
            not_working = [c for c in results if not c.reachable]
            working.sort(key=lambda c: c.latency_ms or float("inf"))
            not_working.sort(key=lambda c: c.latency_ms or float("inf"))
            return working + not_working

    # ── Probing ───────────────────────────────────────────────────────────

    async def _probe_omni(self, provider: ProviderSpec, model: str) -> ModelCandidate:
        """Probe a single OmniRoute model with a tiny completion."""
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=settings.ai_probe_timeout) as client:
                body = {
                    "model": model,
                    "messages": [{"role": "user", "content": "Reply with the single word: OK"}],
                    "stream": False,
                    "temperature": 0.0,
                }
                resp = await client.post(
                    f"{provider.base_url}/chat/completions",
                    json=body,
                )
                latency = (time.time() - start) * 1000
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                        if content.upper() == "OK":
                            return ModelCandidate(
                                provider="omniroute",
                                model=model,
                                reachable=True,
                                latency_ms=latency,
                                http_status=resp.status_code,
                                content=content,
                            )
                    except (json.JSONDecodeError, KeyError, TypeError):
                        pass
                return ModelCandidate(
                    provider="omniroute",
                    model=model,
                    reachable=False,
                    latency_ms=latency,
                    http_status=resp.status_code,
                    error=f"Status {resp.status_code} or unexpected content",
                )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return ModelCandidate(
                provider="omniroute",
                model=model,
                reachable=False,
                latency_ms=latency,
                error=str(e),
            )

    async def _probe_ollama(self, provider: ProviderSpec, model: str) -> ModelCandidate:
        """Probe a single Ollama model with a tiny completion."""
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=settings.ai_probe_timeout) as client:
                body = {
                    "model": model,
                    "messages": [{"role": "user", "content": "OK"}],
                    "stream": False,
                }
                resp = await client.post(
                    f"{provider.base_url}/v1/chat/completions",
                    json=body,
                )
                latency = (time.time() - start) * 1000
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                        if content.upper() == "OK":
                            return ModelCandidate(
                                provider="ollama",
                                model=model,
                                reachable=True,
                                latency_ms=latency,
                                http_status=resp.status_code,
                                content=content,
                            )
                    except (json.JSONDecodeError, KeyError, TypeError):
                        pass
                return ModelCandidate(
                    provider="ollama",
                    model=model,
                    reachable=False,
                    latency_ms=latency,
                    http_status=resp.status_code,
                    error=f"Status {resp.status_code} or unexpected content",
                )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return ModelCandidate(
                provider="ollama",
                model=model,
                reachable=False,
                latency_ms=latency,
                error=str(e),
            )

    # ── Ranking & selection ───────────────────────────────────────────────

    def _rank_candidates(self, candidates: list[ModelCandidate]) -> list[ModelCandidate]:
        """Rank candidates: working ones first (by latency), then non-working."""
        working = [c for c in candidates if c.reachable]
        not_working = [c for c in candidates if not c.reachable]
        working.sort(key=lambda c: c.latency_ms or float("inf"))
        not_working.sort(key=lambda c: c.latency_ms or float("inf"))
        return working + not_working

    # ── Public API ────────────────────────────────────────────────────────

    async def get_candidates(self) -> list[ModelCandidate]:
        """Return the cached ranked candidates, refreshing if TTL elapsed."""
        now = time.time()
        if self._cache is None or now - self._cache_at > settings.ai_route_cache_ttl:
            async with asyncio.Lock():
                # Double-check after acquiring lock
                if self._cache is None or now - self._cache_at > settings.ai_route_cache_ttl:
                    self._cache = await self.discover_candidates()
                    self._cache_at = now
        return self._cache or []

    async def complete(self, system: str, user: str) -> str:
        """Try candidates in ranked order; return the first successful response.
        Raises AIServiceUnavailable if no candidate succeeds."""

        ranked = await self.get_candidates()
        for candidate in ranked:
            # Skip explicitly failed ones (already marked)
            if (candidate.provider, candidate.model) in self._failed:
                continue

            try:
                content = await self._chat_with(candidate, system, user)
                if content and content.strip():
                    # Record success latency for future ranking
                    self._record(candidate, time.time())
                    return content.strip()
            except Exception as e:
                logger.warning(
                    "Router candidate failed %s/%s: %s",
                    candidate.provider,
                    candidate.model,
                    e,
                )
                self._failed.add((candidate.provider, candidate.model))

        # All candidates exhausted
        raise AIServiceUnavailable("All AI providers failed after automatic failover")

    async def _chat_with(self, candidate: ModelCandidate, system: str, user: str) -> str:
        """Send a chat completion to the given candidate and return the raw content."""
        if candidate.provider == "omniroute":
            return await self._call_omniroute(candidate, system, user)
        elif candidate.provider == "ollama":
            return await self._call_ollama(candidate, system, user)
        raise ValueError(f"Unknown provider: {candidate.provider}")

    async def _call_omniroute(self, candidate: ModelCandidate, system: str, user: str) -> str:
        """Call OmniRoute via the singleton service."""
        async with httpx.AsyncClient(timeout=settings.omniroute_timeout) as client:
            api_url = settings.omniroute_api_url.rstrip("/")  # e.g. http://localhost:20128/v1/chat/completions
            body = {
                "model": candidate.model,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "stream": False,
                "temperature": 0.1,
            }
            # Add api_key if present; otherwise "not-needed"
            headers = {}
            if settings.omniroute_api_key:
                headers["Authorization"] = f"Bearer {settings.omniroute_api_key}"
            resp = await client.post(api_url, json=body, headers=headers)
            if resp.status_code != 200:
                raise Exception(f"OmniRoute HTTP {resp.status_code}")
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content.strip() if content else ""

    async def _call_ollama(self, candidate: ModelCandidate, system: str, user: str) -> str:
        """Call Ollama via its OpenAI-compatible endpoint."""
        provider = next((p for p in self.providers if p.name == "ollama"), None)
        base_url = provider.base_url if provider else settings.ollama_api_url.rstrip("/v1/chat/completions")
        async with httpx.AsyncClient(timeout=settings.omniroute_timeout) as client:
            body = {
                "model": candidate.model,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "stream": False,
            }
            resp = await client.post(
                f"{base_url}/v1/chat/completions",
                json=body,
            )
            if resp.status_code != 200:
                raise Exception(f"Ollama HTTP {resp.status_code}")
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content.strip() if content else ""

    # ── Cache management ──────────────────────────────────────────────────

    def _record(self, candidate: ModelCandidate, t: float):
        """Update internal tracking; called after a successful dispatch."""
        pass

    async def refresh(self) -> list[ModelCandidate]:
        """Force a fresh discovery+probe cycle. Returns the new ranked list."""
        async with asyncio.Lock():
            self._cache = await self.discover_candidates()
            self._cache_at = time.time()
        return self._cache or []

    async def status(self) -> dict:
        """Return status for admin endpoints."""
        cached = self._cache or []
        working = [c for c in cached if c.reachable]
        not_working = [c for c in cached if not c.reachable]
        return {
            "cache_ttl_seconds": settings.ai_route_cache_ttl,
            "candidates": [
                {
                    "provider": c.provider,
                    "model": c.model,
                    "reachable": c.reachable,
                    "latency_ms": c.latency_ms,
                    "http_status": c.http_status,
                    "error": c.error,
                }
                for c in cached
            ],
            "working_count": len(working),
            "not_working_count": len(not_working),
            "active_provider": working[0].provider if working else None,
            "active_model": working[0].model if working else None,
        }


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------


async def verify_now() -> dict:
    """Run a one-off discovery+probe cycle and return the status dict."""
    router = AIModelRouter()
    await router.refresh()
    return await router.status()


async def route_complete(system: str, user: str) -> str:
    """Convenience: dispatch through the global router instance."""
    router = AIModelRouter()
    await router.refresh()
    return await router.complete(system, user)
