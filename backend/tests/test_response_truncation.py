"""A truncated response must never become a clean empty chunk.

The concrete failure, measured on the real V4.1 resume: the certifications
chunk needs up to 2157 output tokens while ``parse_chunk_num_predict`` was
2000, so Ollama stopped with ``done_reason="length"`` on roughly 40% of runs
and handed back text cut mid-JSON. ``parse_chunk`` parsed that, failed, and
returned ``{}`` — indistinguishable from "the model produced nothing". Three
genuine certifications (PRINCE2, CSM, ITIL) and every tool category in that
section vanished, and the failure surfaced only as a log line that looked like
an ordinary incomplete parse.

Two things made it invisible rather than merely wrong:

* ``done_reason`` and ``eval_count`` were read from the Ollama response and
  immediately discarded, so nothing downstream could tell a small cap from a
  broken provider;
* truncation was therefore folded into the same ``AIServiceUnavailable`` /
  ``{}`` path as a genuine outage, so the only available retry was the same
  call at the same cap — which returns the same cut-off response.

The required flow is: ``done_reason=length`` → explicit truncation failure →
retry with a larger cap → complete JSON → normal merge. These tests pin each
link, and the closing test pins the arithmetic that makes the cap sufficient.
"""

from __future__ import annotations

import time

import pytest

from app.core.config import settings
from app.services import ollama_service, parser_service
from app.services.ai_core.exceptions import AIServiceUnavailable, ResponseTruncated
from app.services.resume_chunk_parser import parse_chunk

# Recorded on the real V4.1 fixture, qwen2.5:3b-instruct, num_ctx 4096,
# temperature 0.1, measured via Ollama's eval_count. The chunk's output came
# back as either 1986 tokens (31 certifications + 6 skill groups) or 2157
# (35 certifications + 5 groups) depending on how the model chose to
# enumerate, and the 2157 mode is what truncated at a cap of 2000.
#
# This is a recorded worst case, not a value a test may assume the model will
# keep producing: the assertions below check margin against it rather than
# equality with it.
_MEASURED_WORST_CASE_OUTPUT = 2157
# The largest prompt+input across all 18 chunks of that fixture: the
# certifications chunk again. Re-measured after the certifications prompt grew
# its line-level classification rule and worked example (Option 2): 397 -> 510
# tokens, verified against Ollama's prompt_eval_count on the same fixture.
# Any further prompt change must re-measure this, or the context-window guard
# below would be checking a number that no longer describes the parse.
_MEASURED_MAX_PROMPT_INPUT = 510

# Partial JSON of the shape Ollama emits when it is cut off mid-document.
TRUNCATED_BODY = (
    '{"certifications": [{"name": "PRINCE2 Practitioner", "category": "Professional Credentials"}, '
    '{"name": "ITIL Foundation", "category": "Professional "'
)


class _Response:
    def __init__(self, payload: dict, status: int = 200):
        self.status_code = status
        self._payload = payload

    def json(self):
        return self._payload


class _Transport:
    """Fake ``httpx.AsyncClient`` that replays a scripted sequence of replies.

    Each reply is either a payload dict (what Ollama's ``/api/chat`` returned)
    or an exception to raise. Requests are recorded so a test can assert on the
    cap that was actually used for each attempt.
    """

    def __init__(self, replies: list):
        self.replies = list(replies)
        self.requests: list[dict] = []

    def install(self, monkeypatch) -> None:
        transport = self

        class _Client:
            def __init__(self, **kw):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def post(self, url, json=None, **kw):
                transport.requests.append({"url": url, **(json or {})})
                if not transport.replies:
                    raise AssertionError("no scripted reply left")
                reply = transport.replies.pop(0)
                if isinstance(reply, Exception):
                    raise reply
                return _Response(reply)

        monkeypatch.setattr(ollama_service.httpx, "AsyncClient", _Client)


def _truncated_reply(tokens: int = 1986, cap: int = 2000) -> dict:
    """What Ollama returns when it stops because it reached ``num_predict``."""
    return {
        "message": {"content": TRUNCATED_BODY},
        "done_reason": "length",
        "eval_count": tokens,
        "total_duration": 1,
    }


def _complete_reply(content: str, tokens: int = 900, cap: int = 3500) -> dict:
    return {
        "message": {"content": content},
        "done_reason": "stop",
        "eval_count": tokens,
        "total_duration": 1,
    }


class TestTruncationDetection:
    @pytest.mark.asyncio
    async def test_done_reason_length_raises_response_truncated(self, monkeypatch):
        """Ollama's own completion reason is the signal; it must survive."""
        transport = _Transport([_truncated_reply(tokens=1986, cap=2000)])
        transport.install(monkeypatch)

        with pytest.raises(ResponseTruncated) as excinfo:
            await ollama_service.generate_with_ollama(
                "qwen2.5:3b-instruct", "sys", "user", num_predict=2000
            )

        exc = excinfo.value
        assert exc.tokens == 1986, "observed output token count must be carried"
        assert exc.num_predict == 2000, "the cap that caused it must be carried"
        assert "num_predict" in str(exc)

    @pytest.mark.asyncio
    async def test_done_reason_stop_is_not_truncation(self, monkeypatch):
        """A normal completion must keep returning its text as before."""
        transport = _Transport([_complete_reply('{"summary": "ok"}')])
        transport.install(monkeypatch)

        out = await ollama_service.generate_with_ollama("m", "sys", "user")
        assert out == '{"summary": "ok"}'

    @pytest.mark.asyncio
    async def test_eval_count_is_exposed_when_available(self, monkeypatch):
        transport = _Transport([_truncated_reply(tokens=2157)])
        transport.install(monkeypatch)

        with pytest.raises(ResponseTruncated) as excinfo:
            await ollama_service.generate_with_ollama("m", "sys", "user", num_predict=2000)
        assert excinfo.value.tokens == 2157

    async def test_parse_chunk_does_not_return_empty_for_a_truncated_call(self):
        """The central invariant: truncation is not `{}`.

        ``parse_chunk`` is handed the call, so this exercises the layer where
        the old code collapsed the failure into a clean empty dict.
        """
        section = "certifications"

        async def truncated_call(system, user):
            raise ResponseTruncated(
                "Ollama generation hit the num_predict cap",
                tokens=1986,
                num_predict=2000,
            )

        with pytest.raises(ResponseTruncated) as excinfo:
            await parse_chunk(section, "chunk text", truncated_call)

        # Explicit, not `{}`.
        assert excinfo.value is not None
        # And it must say which section was lost, so the log is actionable.
        assert excinfo.value.section == "certifications"
        assert "certifications" in excinfo.value.describe()
        assert "1986/2000" in excinfo.value.describe()

    async def test_parse_chunk_tags_the_section_it_was_cut_in(self):
        async def call(system, user):
            raise ResponseTruncated("cut off", tokens=12, num_predict=2000)

        with pytest.raises(ResponseTruncated) as excinfo:
            await parse_chunk("awards", "text", call)
        assert excinfo.value.section == "awards"


class TestExceptionDistinction:
    @pytest.mark.asyncio
    async def test_truncation_is_not_a_service_unavailable(self, monkeypatch):
        """A healthy model that answered too long must not be called an outage.

        Reporting it as unavailable would send the caller down the
        "provider is down" path instead of the "raise the cap" one, which is
        the path that can actually fix the failure.
        """
        transport = _Transport([_truncated_reply()])
        transport.install(monkeypatch)

        with pytest.raises(ResponseTruncated) as excinfo:
            await ollama_service.generate_with_ollama("m", "sys", "user")

        assert not isinstance(excinfo.value, AIServiceUnavailable)

    @pytest.mark.asyncio
    async def test_ch_ollama_propagates_rather_than_returning_none(self, monkeypatch):
        """`except AIServiceUnavailable: return None` must not swallow it.

        Returning None would send the caller into the "no provider produced
        output" path, which retries at the same cap.
        """
        transport = _Transport([_truncated_reply()])
        transport.install(monkeypatch)
        monkeypatch.setattr(
            ollama_service, "detect_ollama_model", lambda: _async_value("m")
        )

        with pytest.raises(ResponseTruncated):
            await ollama_service.chat_ollama("sys", "user", num_predict=2000)

    @pytest.mark.asyncio
    async def test_chat_providers_propagates_instead_of_trying_next_provider(
        self, monkeypatch
    ):
        """Falling through to the next provider would lose the signal.

        Every provider here is called with the same num_predict, so the next
        one would truncate the same way and nothing would be learned.
        """
        transport = _Transport([_truncated_reply()])
        transport.install(monkeypatch)
        monkeypatch.setattr(
            ollama_service, "detect_ollama_model", lambda: _async_value("m")
        )

        with pytest.raises(ResponseTruncated):
            await ollama_service.chat_providers("sys", "user", num_predict=2000)

    @pytest.mark.asyncio
    async def test_a_genuine_provider_failure_is_still_unavailable(self, monkeypatch):
        """Network trouble must keep taking the old path, not the new one."""
        import httpx

        transport = _Transport([httpx.ConnectError("connection refused")])
        transport.install(monkeypatch)

        with pytest.raises(AIServiceUnavailable):
            await ollama_service.generate_with_ollama("m", "sys", "user")

    @pytest.mark.asyncio
    async def test_a_bad_status_is_still_unavailable(self, monkeypatch):
        transport = _Transport([_Response({}, status=500)])
        transport.install(monkeypatch)

        with pytest.raises(AIServiceUnavailable):
            await ollama_service.generate_with_ollama("m", "sys", "user")

    @pytest.mark.asyncio
    async def test_an_ordinary_empty_completion_is_still_unavailable(self, monkeypatch):
        """Empty content with done_reason=stop is not truncation."""
        transport = _Transport([{"message": {"content": ""}, "done_reason": "stop"}])
        transport.install(monkeypatch)

        with pytest.raises(AIServiceUnavailable):
            await ollama_service.generate_with_ollama("m", "sys", "user")


def _async_value(value):
    async def _inner():
        return value

    return _inner()


# ---------------------------------------------------------------------------
# The required flow: truncated -> retry at a larger cap -> complete -> merge
# ---------------------------------------------------------------------------

RESUME_TEXT = """RAJASEKAR SHARMA
Senior Project Manager
sharma.rajasekar@gmail.com

PROFESSIONAL SUMMARY
Senior project manager with two decades of delivery experience.

CERTIFICATIONS & PROFESSIONAL DEVELOPMENT
Professional Credentials: PMP | PRINCE2 Practitioner | Scrum Master

PROFESSIONAL EXPERIENCE
Senior Project Manager, Transdev Auckland, 2020 - Present
- Delivered a $4M programme across 12 sites
"""

# What the chunk loop should end up with once the retry succeeds.
GOOD_CERTS = '{"certifications": [{"name": "PMP", "category": "Professional Credentials"}, {"name": "PRINCE2 Practitioner", "category": "Professional Credentials"}]}'
GOOD_SUMMARY = '{"summary": "Senior project manager with two decades of delivery experience."}'
GOOD_EXPERIENCE = (
    '{"experience": [{"title": "Senior Project Manager", "company": "Transdev Auckland", '
    '"start_date": "2020", "end_date": "Present", '
    '"description": ["Delivered a $4M programme across 12 sites"]}]}'
)


def _payload_for(system: str) -> str:
    from app.services.resume_chunk_parser import CHUNK_PROMPTS

    if CHUNK_PROMPTS["certifications"] in system:
        return GOOD_CERTS
    if CHUNK_PROMPTS["summary"] in system:
        return GOOD_SUMMARY
    if CHUNK_PROMPTS["experience"] in system:
        return GOOD_EXPERIENCE
    if CHUNK_PROMPTS["header"] in system:
        return '{"full_name": "Rajasekar Sharma", "email": "sharma.rajasekar@gmail.com"}'
    return "{}"


def _section_of(system: str) -> str:
    from app.services.resume_chunk_parser import CHUNK_PROMPTS

    for name, text in CHUNK_PROMPTS.items():
        if text and text in system:
            return name
    return "unknown"


class _CapRecorder:
    """Stands in for ``chat_providers``, scripting truncation per section.

    ``truncate_on`` maps a section name to how many of that section's attempts
    are cut off — so the scenario is described as "certifications truncates
    twice" rather than by call position, which would depend on chunk order and
    on whether other chunks happened to retry. Every call's ``num_predict`` is
    recorded so a test can assert on the cap actually used.
    """

    def __init__(self, truncate_on: dict[str, int] | None = None):
        self.remaining = dict(truncate_on or {})
        self.caps: list[int | None] = []
        self.sections: list[str] = []

    async def __call__(
        self, system, user, *, service_name="AI", timeout=None, num_predict=None, temperature=None
    ):
        section = _section_of(system)
        self.sections.append(section)
        self.caps.append(num_predict)
        if self.remaining.get(section, 0) > 0:
            self.remaining[section] -= 1
            raise ResponseTruncated(
                "Ollama generation hit the num_predict cap",
                tokens=2157,
                num_predict=num_predict,
            )
        return _payload_for(system)

    def install(self, monkeypatch) -> None:
        monkeypatch.setattr(parser_service, "chat_providers", self)

    def calls_for(self, section: str) -> list[int | None]:
        """The caps used by attempts for one section, in call order."""
        return [c for c, s in zip(self.caps, self.sections) if s == section]


@pytest.fixture(autouse=True)
def _no_verify(monkeypatch):
    """Skip the extra audit call so these tests exercise the chunk loop."""
    monkeypatch.setattr(settings, "parse_verify_completeness", False)


class TestRetryEscalation:
    async def test_the_retry_uses_a_strictly_larger_cap(self, monkeypatch):
        """The whole point: same cap twice returns the same cut-off response."""
        rec = _CapRecorder({"certifications": 1})
        rec.install(monkeypatch)

        await parser_service._parse_chunked(RESUME_TEXT)

        caps = rec.calls_for("certifications")
        assert caps[0] == settings.parse_chunk_num_predict
        assert caps[1] == settings.parse_chunk_truncated_num_predict
        assert caps[1] > caps[0], "a retry at the same cap cannot fix truncation"

    async def test_the_first_attempt_uses_the_configured_initial_cap(self, monkeypatch):
        rec = _CapRecorder()
        rec.install(monkeypatch)

        await parser_service._parse_chunked(RESUME_TEXT)

        assert all(cap == settings.parse_chunk_num_predict for cap in rec.caps)
        assert settings.parse_chunk_truncated_num_predict not in rec.caps, (
            "a healthy parse must never pay for an escalation it did not need"
        )

    async def test_the_successful_retry_returns_the_parsed_section(self, monkeypatch):
        """Escalation has to land the content, not merely change the number."""
        rec = _CapRecorder({"certifications": 1})
        rec.install(monkeypatch)

        resume = await parser_service._parse_chunked(RESUME_TEXT)

        assert resume is not None
        names = [c.name for c in resume.certifications]
        assert "PMP" in names, "the truncated chunk's certifications must be recovered"
        assert "PRINCE2 Practitioner" in names
        assert resume.summary, "the rest of the resume must survive untouched"

    async def test_truncation_is_not_retried_at_the_same_cap(self, monkeypatch):
        rec = _CapRecorder({"certifications": 1})
        rec.install(monkeypatch)

        await parser_service._parse_chunked(RESUME_TEXT)

        caps = rec.calls_for("certifications")
        assert caps == [settings.parse_chunk_num_predict, settings.parse_chunk_truncated_num_predict]
        assert caps.count(settings.parse_chunk_num_predict) == 1, (
            "the original cap must appear exactly once for the truncated section"
        )


class TestPersistentTruncation:
    async def test_both_attempts_truncating_fails_clearly(self, monkeypatch, caplog):
        """Not a silent `{}`: an error naming the section and both caps."""
        rec = _CapRecorder({"certifications": 2})
        rec.install(monkeypatch)

        with caplog.at_level("ERROR", logger="app.services.parser_service"):
            await parser_service._parse_chunked(RESUME_TEXT)

        errors = [r for r in caplog.records if r.levelname == "ERROR"]
        assert errors, "persistent truncation must be reported at error level"
        text = " ".join(r.getMessage() for r in errors)
        assert "truncated even at the larger cap" in text
        assert "certifications" in text, "the lost section must be named"
        assert str(settings.parse_chunk_truncated_num_predict) in text

    async def test_the_lost_chunk_is_counted_as_failed(self, monkeypatch, caplog):
        """The whole parse must report itself partial, not healthy."""
        rec = _CapRecorder({"certifications": 2})
        rec.install(monkeypatch)

        with caplog.at_level("WARNING", logger="app.services.parser_service"):
            await parser_service._parse_chunked(RESUME_TEXT)

        warnings = " ".join(r.getMessage() for r in caplog.records)
        assert "Partial parse" in warnings, (
            "a section lost to truncation must make the parse report itself incomplete"
        )

    async def test_it_does_not_fall_back_to_the_original_cap(self, monkeypatch):
        """After two truncations, no third call at the cap that failed."""
        rec = _CapRecorder({"certifications": 2})
        rec.install(monkeypatch)

        await parser_service._parse_chunked(RESUME_TEXT)

        caps = rec.calls_for("certifications")
        assert caps == [settings.parse_chunk_num_predict, settings.parse_chunk_truncated_num_predict]
        assert len(caps) == 2, "persistent truncation must not burn a third attempt"

    async def test_parse_chunk_still_raises_when_given_only_a_truncating_call(self):
        """The unit-level invariant does not depend on the pool being present."""

        async def always_truncates(system, user):
            raise ResponseTruncated("cut", tokens=2157, num_predict=3200)

        with pytest.raises(ResponseTruncated):
            await parse_chunk("certifications", "text", always_truncates)

    async def test_no_escalated_call_still_fails_loudly(self, monkeypatch, caplog):
        """A caller that supplies no escalation must still not be silent."""
        chunks = [{"section": "summary", "text": "PROFESSIONAL SUMMARY\nhello"}]

        async def call(system, user):
            raise ResponseTruncated("cut", tokens=100, num_predict=3200)

        with caplog.at_level("ERROR", logger="app.services.parser_service"):
            results = await parser_service._parse_chunks_concurrently(
                chunks,
                call,
                concurrency=1,
                budget=60.0,
                started=time.monotonic(),
            )

        assert results == [(0, {})]
        text = " ".join(r.getMessage() for r in caplog.records)
        assert "no larger cap is available" in text


class TestNoRegression:
    async def test_normal_json_still_parses_the_same_way(self, monkeypatch):
        rec = _CapRecorder()
        rec.install(monkeypatch)

        resume = await parser_service._parse_chunked(RESUME_TEXT)

        assert resume is not None
        assert [c.name for c in resume.certifications] == ["PMP", "PRINCE2 Practitioner"]

    async def test_invalid_non_truncated_json_still_returns_empty(self):
        """Unparseable-but-not-truncated output keeps its old behaviour."""

        async def bad_call(system, user):
            return "this is not json at all"

        assert await parse_chunk("summary", "text", bad_call) == {}

    async def test_a_provider_returning_none_still_returns_empty(self):
        async def none_call(system, user):
            return None

        assert await parse_chunk("summary", "text", none_call) == {}

    async def test_a_slow_or_broken_call_still_returns_empty(self):
        async def boom(system, user):
            raise RuntimeError("connection reset")

        assert await parse_chunk("summary", "text", boom) == {}

    async def test_other_failures_still_take_the_generic_retry(self, monkeypatch):
        """Non-truncation failures keep their existing one-retry treatment."""
        attempts: list[int | None] = []

        async def flaky(system, user, **kwargs):
            attempts.append(kwargs.get("num_predict"))
            if len(attempts) == 1:
                return None  # provider produced nothing
            return _payload_for(system)

        monkeypatch.setattr(settings, "parse_verify_completeness", False)
        monkeypatch.setattr(parser_service, "chat_providers", flaky)

        resume = await parser_service._parse_chunked(RESUME_TEXT)
        assert resume is not None
        assert settings.parse_chunk_truncated_num_predict not in attempts, (
            "a plain empty response is not truncation and must not escalate"
        )


class TestV41CapGuard:
    """The arithmetic, not the model's output: caps must stay ahead of need.

    Recording a measurement and asserting margin against it catches a future
    cap reduction or a prompt that outgrows the cap, without asserting that the
    model must keep producing an exact token count.
    """

    def test_the_initial_cap_clears_the_measured_worst_case_with_margin(self):
        margin = settings.parse_chunk_num_predict - _MEASURED_WORST_CASE_OUTPUT
        assert margin >= 400, (
            f"cap {settings.parse_chunk_num_predict} leaves only {margin} tokens over the "
            f"measured {_MEASURED_WORST_CASE_OUTPUT}-token requirement — too little to absorb "
            "the model choosing to enumerate more entries"
        )

    def test_the_escalation_exceeds_the_initial_cap(self):
        assert settings.parse_chunk_truncated_num_predict > settings.parse_chunk_num_predict

    def test_the_escalation_still_fits_the_context_window(self):
        """num_ctx is pinned at 4096; exceeding it just truncates again."""
        peak = _MEASURED_MAX_PROMPT_INPUT + settings.parse_chunk_truncated_num_predict
        assert peak <= ollama_service.OLLAMA_NUM_CTX
        assert peak <= 4096 - 64, "leave headroom in the context window itself"

    def test_the_initial_cap_still_fits_the_context_window(self):
        peak = _MEASURED_MAX_PROMPT_INPUT + settings.parse_chunk_num_predict
        assert peak <= ollama_service.OLLAMA_NUM_CTX

    def test_the_context_window_unchanged(self):
        """Pinned deliberately: a larger window reserves memory the box lacks."""
        assert ollama_service.OLLAMA_NUM_CTX == 4096
