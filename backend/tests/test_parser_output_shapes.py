"""A valid chunk must not be discarded for not matching the requested shape.

The concrete failure, caught on the real V4.1 resume: asked for
``{"experience": [...]}``, the model returned a bare ``[{...}]`` array with
complete, correct content. ``parse_chunk`` parsed it fine and then threw it
away for not being a dict, so the chunk was logged as a provider failure and an
entire job (NTT Data, 2003-2009) silently vanished from the resume — while the
parse reported "15/16 sections succeeded" and looked healthy.

These tests pin that a shape difference can never cost content again.
"""

from __future__ import annotations

import json

import pytest

from app.services import parser_service
from app.services.ai_core.json_parser import extract_json
from app.services.resume_chunk_parser import _as_section_dict, merge_chunks, parse_chunk

ROLE = {
    "company": "NTT Data",
    "title": "Project Manager",
    "location": "Bangalore",
    "start_date": "2003",
    "end_date": "2009",
    "description": ["Delivered clinical patient-care monitoring systems."],
}

RESUME_TEXT = """RAJASEKAR SHARMA
Senior Project Manager
sharma.rajasekar@gmail.com

PROFESSIONAL SUMMARY
Senior project manager with two decades of delivery experience.

PROFESSIONAL EXPERIENCE
Project Manager, NTT Data, Bangalore - 2003 to 2009
- Delivered clinical patient-care monitoring systems

EARLY CAREER HIGHLIGHTS
Programmer Analyst, Syntel India Ltd, Chennai - 2001 to 2003
- Built core financial loan-servicing modules on IBM AS400

CERTIFICATIONS
- PRINCE2 Practitioner
"""


async def _call_returning(raw: str):
    async def call(system, user):
        return raw

    return call


class TestOutputShapeNormalisation:
    def test_a_dict_passes_through_untouched(self):
        payload = {"experience": [ROLE]}
        assert _as_section_dict("experience", payload) is payload

    def test_a_bare_array_becomes_the_section_list(self):
        """The shape that actually cost a job."""
        assert _as_section_dict("experience", [ROLE]) == {"experience": [ROLE]}

    def test_early_career_is_keyed_as_experience(self):
        """early_career and experience feed the same list, so a bare array for
        an early-career chunk must land under "experience" or it merges to
        nothing even though it parsed."""
        shaped = _as_section_dict("early_career", [ROLE])
        assert "experience" in shaped
        assert shaped["experience"] == [ROLE]

    def test_certifications_array_is_keyed_correctly(self):
        shaped = _as_section_dict("certifications", [{"name": "PRINCE2 Practitioner"}])
        assert shaped == {"certifications": [{"name": "PRINCE2 Practitioner"}]}

    def test_a_double_encoded_payload_is_unwrapped(self):
        """The model sometimes wraps the JSON in a JSON string. The payload
        underneath is intact, so one more pass is worth it."""
        inner = json.dumps([ROLE])
        assert _as_section_dict("experience", json.dumps(inner)) == {"experience": [ROLE]}

    def test_an_array_for_a_scalar_section_is_rejected(self):
        """A list of items means nothing for a section that wants a string, so
        it is still discarded rather than written into the wrong field."""
        assert _as_section_dict("summary", ["a", "b"]) == {}
        assert _as_section_dict("header", [{"name": "x"}]) == {}

    def test_a_double_encoded_payload_that_is_not_json_is_rejected(self):
        assert _as_section_dict("experience", json.dumps("not json at all")) == {}

    @pytest.mark.parametrize("junk", [None, 42, 3.5, True, b"bytes"])
    def test_scalar_junk_is_rejected(self, junk):
        assert _as_section_dict("experience", junk) == {}


class TestParseChunkAcceptsRealShapes:
    async def test_a_bare_array_is_kept_not_discarded(self):
        call = await _call_returning("```json\n" + json.dumps([ROLE]) + "\n```")
        data = await parse_chunk("experience", "text", call)
        assert data["experience"][0]["company"] == "NTT Data"

    async def test_a_fenced_bare_array_is_kept(self):
        call = await _call_returning(f"```json\n{json.dumps([ROLE])}\n```")
        data = await parse_chunk("experience", "text", call)
        assert data["experience"][0]["title"] == "Project Manager"

    async def test_invalid_json_is_still_rejected(self):
        call = await _call_returning("I could not parse that, sorry.")
        assert await parse_chunk("experience", "text", call) == {}

    async def test_empty_output_is_still_rejected(self):
        call = await _call_returning("")
        assert await parse_chunk("experience", "text", call) == {}


class TestExtractJsonKeepsArrays:
    """The slice itself was the defect: a bare array was rewritten into a single
    object, so behaviour depended on whether the model used a code fence."""

    def test_a_fenced_array_survives(self):
        raw = "```json\n" + json.dumps([ROLE, ROLE]) + "\n```"
        assert json.loads(extract_json(raw)) == [ROLE, ROLE]

    def test_an_unfenced_multi_item_array_survives(self):
        """Previously sliced to "{...}, {...}" — invalid JSON, whole section lost."""
        raw = json.dumps([ROLE, dict(ROLE, company="Syntel India Ltd")])
        parsed = json.loads(extract_json(raw))
        assert isinstance(parsed, list)
        assert [r["company"] for r in parsed] == ["NTT Data", "Syntel India Ltd"]

    def test_an_unfenced_single_item_array_survives_as_an_array(self):
        """Previously collapsed into one object, which happened to work for a
        single role but would drop the other four."""
        parsed = json.loads(extract_json(json.dumps([ROLE])))
        assert isinstance(parsed, list)
        assert parsed[0]["company"] == "NTT Data"

    def test_a_plain_object_is_unaffected(self):
        raw = json.dumps({"full_name": "Rajasekar Sharma", "email": "a@b.com"})
        assert json.loads(extract_json(raw))["full_name"] == "Rajasekar Sharma"

    def test_an_object_with_a_code_fence_is_unaffected(self):
        raw = "```json\n" + json.dumps({"summary": "Senior PM."}) + "\n```"
        assert json.loads(extract_json(raw))["summary"] == "Senior PM."

    def test_prose_around_a_fenced_array_is_ignored(self):
        raw = "Here you go:\n```json\n" + json.dumps([ROLE]) + "\n```\nHope that helps."
        assert json.loads(extract_json(raw))[0]["title"] == "Project Manager"

    def test_text_with_no_json_at_all_is_returned_unchanged(self):
        assert extract_json("I could not parse that, sorry.") == "I could not parse that, sorry."

    def test_a_lone_open_bracket_does_not_crash(self):
        assert extract_json("[ unterminated") == "[ unterminated"


class TestMergedResumeKeepsTheRole:
    def test_a_bare_array_chunk_merges_into_the_role_list(self):
        merged = merge_chunks([("early_career", {"experience": [ROLE]})])
        assert [r["company"] for r in merged["experience"]] == ["NTT Data"]

    async def test_a_role_returned_as_an_array_survives_the_whole_parse(self, monkeypatch):
        """End-to-end guard on the exact regression, reproduced from the real
        failure: the NTT Data chunk came back as a *fenced* bare array with
        complete content, and the whole job disappeared.

        Fenced matters. An unfenced single-item array used to be mangled into a
        single object by ``extract_json`` and then survive by accident, which is
        what made an earlier version of this test pass against unfixed code.
        """
        early_role = {
            "company": "Syntel India Ltd",
            "title": "Programmer Analyst",
            "description": ["Built core financial loan-servicing modules on IBM AS400."],
        }

        def fenced(roles: list[dict]) -> str:
            return "```json\n" + json.dumps(roles) + "\n```"

        async def fake_call(system, user, **kwargs):
            from tests.test_parse_chunk_orchestration import _section_of

            section = _section_of(system)
            if section == "experience":
                return fenced([ROLE])
            if section == "early_career":
                return fenced([early_role])
            if section == "header":
                return fenced(
                    {"full_name": "Rajasekar Sharma", "email": "sharma.rajasekar@gmail.com"}
                )
            if section == "summary":
                return fenced({"summary": "Senior project manager."})
            return fenced({"certifications": [{"name": "PRINCE2 Practitioner"}]})

        monkeypatch.setattr(parser_service, "chat_providers", fake_call)

        resume = await parser_service._parse_chunked(RESUME_TEXT)

        assert resume is not None
        companies = [e.company for e in resume.experience]
        assert "NTT Data" in companies, f"the bare-array role was dropped: {companies}"
        assert "Syntel India Ltd" in companies, f"the early-career role was dropped: {companies}"
        assert any("AS400" in b for e in resume.experience for b in (e.description or []))
