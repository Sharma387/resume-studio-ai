"""The completeness audit must not report facts that are actually present.

Two failure modes were measured live on the real resume:

1. The whole-resume audit overflowed the context window. The server silently
   dropped the oldest tokens, so the model reported seven roles that were in
   the output as "possibly missing".
2. Once that was fixed, asking the model to *diff* two documents still produced
   false reports — it listed all nine roles as missing, including bullets
   sitting in the very JSON beside it. A 3B model cannot hold two documents in
   mind well enough to compare them.

So the audit asks the model only to list the source's facts (a task it does
reliably) and matches them against the parsed output in Python, where the
comparison cannot hallucinate.
"""

from __future__ import annotations

import asyncio
import json

from app.services.resume_chunk_parser import (
    _AUDIT_SOURCE_CHARS,
    _facts_missing_from,
    _section_shape,
    verify_completeness,
    verify_sections,
)


class _Recorder:
    """Stands in for the provider call and keeps the prompts it was given."""

    def __init__(self, reply: str = '{"facts": []}'):
        self.reply = reply
        self.prompts: list[str] = []
        self.systems: list[str] = []

    async def __call__(self, system: str, user: str) -> str:
        self.systems.append(system)
        self.prompts.append(user)
        return self.reply


def _facts(*items: str) -> str:
    return json.dumps({"facts": list(items)})


class TestFactMatching:
    def test_a_fact_present_in_the_output_is_not_reported(self):
        payload = json.dumps(
            {"description": ["Led a $1M domain migration for the Animal Care business units"]}
        )
        assert _facts_missing_from(["Led a $1M domain migration for the Animal Care business units"], payload) == []

    def test_a_fact_absent_from_the_output_is_reported(self):
        payload = json.dumps({"description": ["Led a $1M domain migration"]})
        missing = _facts_missing_from(
            ["Directed nationwide delivery of strategic technology projects spanning wireless networking"], payload
        )
        assert len(missing) == 1

    def test_a_wrapped_bullet_is_matched_against_its_clean_form(self):
        """PDF extraction hard-wraps lines, so the source holds ragged
        fragments while the parsed output holds one clean sentence. Comparing
        raw strings would report every wrapped bullet as missing."""
        wrapped = "Managed Northern Region district and national IT software/infrastructure port\nfolios, delivering 25+ "
        clean = json.dumps({
            "description": [
                "Managed Northern Region district and national IT software/infrastructure portfolios, "
                "delivering 25+ major projects"
            ]
        })
        assert _facts_missing_from([wrapped], clean) == []

    def test_minor_rewordings_still_count_as_present(self):
        payload = json.dumps({"description": ["Modernised network access infrastructure with zero disruption"]})
        assert _facts_missing_from(["Modernized network access infrastructure with zero disruption."], payload) == []

    def test_filler_words_do_not_make_a_fact_look_present(self):
        """A dropped bullet must not be rescued by words common to every
        bullet."""
        payload = json.dumps({"description": ["Managed the budget and the team and the schedule"]})
        missing = _facts_missing_from(
            ["Delivered statewide stroke rehabilitation pathway redesign across six district hospitals"], payload
        )
        assert len(missing) == 1

    def test_an_empty_output_reports_everything_with_content(self):
        missing = _facts_missing_from(["Delivered a $4M programme", "Reduced incidents by 35 percent"], "")
        assert len(missing) == 2

    def test_pure_punctuation_facts_are_ignored(self):
        assert _facts_missing_from(["---", "..."], json.dumps({"x": "y"})) == []


class TestWholeDocumentGuard:
    def test_refuses_to_audit_an_oversized_resume(self):
        """Better to skip than to emit unreliable omission reports."""
        call = _Recorder(_facts("something"))
        resume = {"experience": [{"title": "PM", "description": ["x" * 200]}] * 400}

        assert asyncio.run(verify_completeness("Some resume text", resume, call)) == []
        assert call.prompts == [], "no call should be made with an input that cannot fit"

    def test_audits_when_both_sides_fit(self):
        call = _Recorder(_facts("PEARL Team Award 2025"))
        missing = asyncio.run(
            verify_completeness("Award: PEARL Team Award 2025", {"awards": []}, call)
        )
        assert len(missing) == 1
        assert "PEARL Team Award 2025" in missing[0]


class TestSectionAudit:
    def test_each_section_is_audited_against_its_own_text(self):
        call = _Recorder(_facts())
        pairs = [
            ("experience", "Senior PM at Transdev, 2020-Present", {"experience": [{"title": "PM"}]}),
            ("certifications", "PRINCE2 Practitioner", {"certifications": [{"name": "PRINCE2"}]}),
        ]
        assert asyncio.run(verify_sections(pairs, call)) == []
        assert len(call.prompts) == 2
        assert "experience" in call.prompts[0]
        assert "PRINCE2" in call.prompts[1]

    def test_findings_are_labelled_with_their_section(self):
        call = _Recorder(_facts("the Azure cert"))
        pairs = [("certifications", "Azure cert text", {"certifications": []})]
        findings = asyncio.run(verify_sections(pairs, call))
        assert findings == ["certifications: the Azure cert"]

    def test_skips_sections_that_parsed_to_nothing(self):
        call = _Recorder(_facts())
        pairs = [("summary", "some text", {}), ("awards", "more text", {"awards": []})]
        asyncio.run(verify_sections(pairs, call))
        assert len(call.prompts) == 1, "an unparsed section has nothing to audit against"

    def test_an_oversized_section_is_not_audited_at_all(self):
        call = _Recorder(_facts("a fact"))
        big_source = "Role description line. " * 2000
        pairs = [("experience", big_source, {"experience": [{"title": "PM"}]})]

        assert asyncio.run(verify_sections(pairs, call)) == []
        assert call.prompts == [], "an oversized section must not be audited at all"

    def test_max_calls_caps_the_extra_model_calls(self):
        call = _Recorder(_facts())
        pairs = [(f"section{i}", "text", {"x": i}) for i in range(10)]
        asyncio.run(verify_sections(pairs, call, max_calls=3))
        assert len(call.prompts) == 3

    def test_a_failing_audit_call_does_not_break_the_parse(self):
        async def _boom(system, user):
            raise RuntimeError("provider down")

        pairs = [("summary", "text", {"summary": "x"})]
        assert asyncio.run(verify_sections(pairs, _boom)) == []

    def test_chatty_model_output_is_tolerated(self):
        call = _Recorder("I reviewed it and everything looks complete.")
        pairs = [("summary", "text", {"summary": "x"})]
        assert asyncio.run(verify_sections(pairs, call)) == []

    def test_a_small_section_is_audited_whole(self):
        """The cap must not mangle a section that already fits."""
        call = _Recorder(_facts())
        source = "Senior Project Manager, Transdev Auckland, 2020 - Present"
        data = {"experience": [{"title": "Senior Project Manager"}]}
        asyncio.run(verify_sections([("experience", source, data)], call))
        assert source in call.prompts[0]
        assert len(call.prompts[0]) < _AUDIT_SOURCE_CHARS * 2

    def test_the_model_is_only_asked_to_list_the_source_facts(self):
        """The structured output is compared in Python, never by the model —
        that is what makes a false report impossible."""
        call = _Recorder(_facts())
        asyncio.run(verify_sections([("summary", "some text", {"summary": "x"})], call))
        prompt = call.prompts[0]
        assert "RESUME TEXT" in prompt
        assert "STRUCTURED RESUME" not in prompt
        assert "MISSING" not in prompt


class TestRoleShape:
    """The chunk's parsed output is reshaped before matching, so a fact the
    model did capture is not reported as lost."""

    SINGLE_ROLE = {
        "company": "EBOS Group Limited",
        "title": "IT Infrastructure Project Specialist",
        "start_date": "Nov 2024",
        "end_date": "Jun 2026",
        "description": ["Led a $1M domain migration for the Animal Care business units"],
    }

    def test_a_single_role_chunk_is_matched_in_the_shape_the_merge_produces(self):
        """The failure this guards: a single-role chunk returns the role at the
        top level, so matching it as-is reported the role as missing from its
        own section — nine of them, all false."""
        facts = ["IT Infrastructure Project Specialist at EBOS Group Limited"]
        assert _facts_missing_from(facts, json.dumps(_section_shape("experience", self.SINGLE_ROLE))) == []

    def test_a_multi_role_chunk_is_matched_as_a_list(self):
        chunk_data = {"experience": [{"company": "EBOS Group", "title": "Project Specialist"}]}
        assert _facts_missing_from(["Project Specialist at EBOS Group"], json.dumps(_section_shape("experience", chunk_data))) == []

    def test_the_organisation_description_line_is_matched_as_a_bullet(self):
        """Resumes open a role with a prose line about the organisation. The
        merge keeps it as the first bullet, so the audit must see it there."""
        chunk_data = dict(self.SINGLE_ROLE)
        chunk_data["summary"] = "Largest Australasian marketer, wholesaler, and distributor of healthcare products"
        shaped = json.dumps(_section_shape("experience", chunk_data))
        assert _facts_missing_from(
            ["Largest Australasian marketer, wholesaler, and distributor of healthcare products"], shaped
        ) == []

    def test_a_genuinely_dropped_bullet_is_still_caught(self):
        """Reshaping must not blunt the audit: a role's real bullet that never
        made it into the output has to be reported."""
        shaped = json.dumps(_section_shape("experience", self.SINGLE_ROLE))
        missing = _facts_missing_from(
            ["Deployed GlobalProtect VPN group-wide, consolidating disparate Cisco and F5 infrastructure"], shaped
        )
        assert len(missing) == 1

    def test_a_non_experience_section_is_untouched(self):
        assert _section_shape("summary", {"summary": "x"}) == {"summary": "x"}
