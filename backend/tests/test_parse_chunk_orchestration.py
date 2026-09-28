"""Orchestration guarantees for the chunked parse.

The failure these cover is expensive: when the local model is unhealthy, every
chunk call burns the full per-chunk timeout and retries, so a three-page resume
took hours and returned nothing. A parse must stay bounded in time and must
return whatever it managed to parse rather than all-or-nothing.
"""

from __future__ import annotations

import json

import pytest

from app.core.config import settings
from app.services import parser_service

RESUME_TEXT = """RAJASEKAR SHARMA
Senior Project Manager
sharma.rajasekar@gmail.com

PROFESSIONAL SUMMARY
Senior project manager with two decades of delivery experience.

CORE COMPETENCIES
- Programme Management
- Vendor Management

PROFESSIONAL EXPERIENCE
Senior Project Manager, Transdev Auckland, 2020 - Present
- Delivered a $4M programme across 12 sites
- Reduced incidents by 35 percent

Project Manager, Auckland Council, 2017 - 2020
- Led a multi-agency portfolio

EDUCATION
MBA, AUT University, 2017 - 2019
- Distinction

CERTIFICATIONS
- PMP
- PRINCE2

AWARDS
- PEARL Team Award 2025
"""


def _json_for(section: str) -> str:
    """Minimal well-formed output for a chunk of the given section."""
    payloads = {
        "header": {"full_name": "Rajasekar Sharma", "email": "sharma.rajasekar@gmail.com"},
        "summary": {"summary": "Senior project manager."},
        "skills": {"skills": [{"category": "Delivery", "skills": ["Programme Management"]}]},
        "experience": {
            "experience": [
                {
                    "title": "Senior Project Manager",
                    "company": "Transdev Auckland",
                    "start_date": "2020",
                    "end_date": "Present",
                    "description": ["Delivered a $4M programme", "Reduced incidents by 35 percent"],
                }
            ]
        },
        "education": {"education": [{"degree": "MBA", "institution": "AUT University"}]},
        "certifications": {"certifications": [{"name": "PMP"}]},
        "awards": {"awards": [{"name": "PEARL Team Award", "date": "2025"}]},
    }
    return json.dumps(payloads.get(section, {}))


@pytest.fixture(autouse=True)
def _no_verify(monkeypatch):
    """Skip the extra audit call so tests exercise the chunk loop only."""
    monkeypatch.setattr(settings, "parse_verify_completeness", False)


def _stub_provider(monkeypatch, handler):
    """Replace the provider call with ``handler(section) -> str | None``."""
    seen: list[str] = []

    async def fake_call(system, user, **kwargs):
        seen.append(system)
        return handler(len(seen))

    monkeypatch.setattr(parser_service, "chat_ollama", fake_call)
    return seen


def _section_of(system: str) -> str:
    # The prompt is "<prefix> <CHUNK_PROMPTS[section]>"; the section key is the
    # last quoted-ish token before the schema text, so find it by the prompts
    # table instead of string surgery.
    from app.services.resume_chunk_parser import CHUNK_PROMPTS

    for name, text in CHUNK_PROMPTS.items():
        if text and text in system:
            return name
    return "unknown"


class TestBoundedTime:
    async def test_stops_at_the_time_budget(self, monkeypatch):
        """The budget is checked between chunks, so a slow provider cannot
        extend the parse indefinitely."""
        monkeypatch.setattr(settings, "parse_time_budget", 0)
        calls: list[str] = []

        async def fake_call(system, user, **kwargs):
            calls.append(system)
            return json.dumps({"full_name": "Rajasekar Sharma", "email": "a@b.com"})

        monkeypatch.setattr(parser_service, "chat_ollama", fake_call)

        resume = await parser_service._parse_chunked(RESUME_TEXT)

        assert calls == [], "no chunk should be attempted once the budget is spent"
        # Nothing was parsed, so there is nothing usable to return.
        assert resume is None

    async def test_returns_partial_result_when_budget_runs_out(self, monkeypatch):
        """Sections parsed before the cutoff are still returned."""
        import app.services.parser_service as ps

        # Two chunks' worth of elapsed time, then the clock jumps past budget.
        ticks = iter([0.0, 0.0, 0.0, 999.0, 999.0, 999.0, 999.0, 999.0])

        monkeypatch.setattr(ps.time, "monotonic", lambda: next(ticks, 999.0))
        monkeypatch.setattr(settings, "parse_time_budget", 100)

        def handler(n: int) -> str:
            # Fail every chunk after the first two good ones.
            return _json_for("header") if n <= 2 else None

        _stub_provider(monkeypatch, handler)

        resume = await parser_service._parse_chunked(RESUME_TEXT)

        assert resume is not None
        assert resume.full_name == "Rajasekar Sharma"


class TestSystemicFailure:
    async def test_gives_up_after_consecutive_failures(self, monkeypatch):
        """A run of failures means the provider is down; retrying every
        remaining chunk would multiply the wait for no gain."""
        monkeypatch.setattr(settings, "parse_max_consecutive_failures", 3)
        attempts: list[str] = []

        async def fake_call(system, user, **kwargs):
            attempts.append(system)
            return None

        monkeypatch.setattr(parser_service, "chat_ollama", fake_call)

        assert await parser_service._parse_chunked(RESUME_TEXT) is None
        # 3 failed chunks, each retried once, then it stops.
        assert len(attempts) == 6, "should stop early rather than try every chunk"

    async def test_an_isolated_failure_is_still_retried(self, monkeypatch):
        """A single bad chunk is worth one more attempt."""
        monkeypatch.setattr(settings, "parse_max_consecutive_failures", 3)
        calls: list[str] = []

        def handler(n: int) -> str | None:
            calls.append(str(n))
            if n == 2:
                return None  # first attempt at chunk 2 fails
            if n == 3:
                return _json_for("header")  # its retry succeeds
            return _json_for("header")

        _stub_provider(monkeypatch, handler)
        resume = await parser_service._parse_chunked(RESUME_TEXT)

        assert resume is not None
        assert resume.full_name == "Rajasekar Sharma"

    async def test_failure_streak_resets_after_a_success(self, monkeypatch):
        """Two failures, a success, then more chunks: the streak resets so
        later chunks are not abandoned."""
        monkeypatch.setattr(settings, "parse_max_consecutive_failures", 3)
        outcomes = [None, _json_for("header"), None, None, None, None, _json_for("header")]

        def handler(n: int) -> str | None:
            return outcomes[n - 1] if n - 1 < len(outcomes) else _json_for("header")

        _stub_provider(monkeypatch, handler)
        resume = await parser_service._parse_chunked(RESUME_TEXT)

        assert resume is not None
        assert resume.full_name == "Rajasekar Sharma"


class TestPartialResultsArePreferred:
    async def test_partial_chunked_result_beats_another_long_call(self, monkeypatch):
        """A partial chunked parse is returned as-is rather than discarded
        for a single-shot retry, which would take even longer.

        The header chunk is the identity and survives; a content chunk drops.
        """
        single_shot_calls: list[str] = []

        async def fake_single_shot(text):
            single_shot_calls.append(text)
            return None

        monkeypatch.setattr(parser_service, "_parse_single_shot", fake_single_shot)

        # Chunk 1 (header) succeeds; everything after it fails.
        def handler(n: int) -> str | None:
            return _json_for("header") if n == 1 else None

        _stub_provider(monkeypatch, handler)

        resume = await parser_service._parse_chunked(RESUME_TEXT)

        assert resume is not None
        assert resume.full_name == "Rajasekar Sharma"
        assert resume.email == "sharma.rajasekar@gmail.com"
        assert single_shot_calls == [], "a partial result must not trigger the slow retry"

    async def test_the_audit_is_skipped_once_the_budget_is_spent(self, monkeypatch):
        """Enabling the fidelity check costs one model call per section, so it
        must not be able to push a parse past its budget."""
        monkeypatch.setattr(settings, "parse_verify_completeness", True)
        monkeypatch.setattr(settings, "parse_time_budget", 10)
        calls: list[int] = []

        async def fake_verify_sections(pairs, call, *, max_calls=None):
            calls.append(max_calls)
            return []

        monkeypatch.setattr(parser_service, "verify_sections", fake_verify_sections)
        _stub_provider(monkeypatch, lambda n: _json_for("header"))

        # Elapsed time is already past the budget when the audit would start.
        ticks = iter([0.0, 0.0, 0.0, 999.0])
        monkeypatch.setattr(parser_service.time, "monotonic", lambda: next(ticks, 999.0))

        resume = await parser_service._parse_chunked(RESUME_TEXT)

        assert resume is not None
        assert calls == [], "no audit call may be made on a spent budget"

    async def test_the_audit_covers_only_what_fits_in_the_remaining_budget(self, monkeypatch):
        """With part of the budget left, only that many sections are checked —
        never the whole resume, however many sections it has."""
        monkeypatch.setattr(settings, "parse_verify_completeness", True)
        monkeypatch.setattr(settings, "parse_time_budget", 130)
        calls: list[int] = []

        async def fake_verify_sections(pairs, call, *, max_calls=None):
            calls.append(max_calls)
            assert len(pairs) > max_calls, "the cap should bite on a 7-section resume"
            return []

        monkeypatch.setattr(parser_service, "verify_sections", fake_verify_sections)
        _stub_provider(monkeypatch, lambda n: _json_for("header"))

        # 70s elapsed, leaving 60s of a 130s budget: two 30s audit calls.
        ticks = iter([0.0] + [70.0] * 40)
        monkeypatch.setattr(parser_service.time, "monotonic", lambda: next(ticks, 70.0))

        resume = await parser_service._parse_chunked(RESUME_TEXT)

        assert resume is not None
        assert calls == [2]

    async def test_no_identity_at_all_still_falls_through(self, monkeypatch):
        """Without identity the model cannot build a valid Resume, so the
        caller is expected to try the single-shot path."""
        def handler(n: int) -> str | None:
            return None if n <= 2 else _json_for("summary")

        _stub_provider(monkeypatch, handler)

        assert await parser_service._parse_chunked(RESUME_TEXT) is None
