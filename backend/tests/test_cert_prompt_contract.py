"""The certifications prompt classifies each line, not the section it sits in.

Fix A gave the chunk a ``skills`` key and Option 1 reconciled the overlap away
in ``merge_chunks``, but both only act on what the model emits twice. The
residual failure is a *pure* misroute: a tool line emitted solely under
``certifications``, with the model's skill group carrying a different heading
("AI & Automation") so no overlap exists and reconciliation correctly stays
out of it. Observed once in eleven post-fix runs.

Option 2 is a prompt-only repair for that, and these tests pin its contract:

* a line-level rule, judged on the line's items rather than on position;
* credentials versus tools/technologies/competencies stated explicitly;
* different skill headings permitted, so a second heading is not read as a
  reason to move the line into certifications;
* one worked mixed example whose output can be parsed and asserted on;
* exactly-once emission;
* no dependency on the section heading, which ``chunk_resume`` strips before
  the model ever sees the chunk.

The prompt is also given a size ceiling. This section has the largest
prompt+input in the whole parse, so growing it without re-measuring
``_MEASURED_MAX_PROMPT_INPUT`` in ``test_response_truncation.py`` would push
prompt + escalated cap past ``num_ctx`` and the generation would truncate.

Nothing here decides classification itself — that stays with the model — and
no test may require the model to answer a particular way; the benchmark is
what checks behaviour. These assert only that the prompt states the rule.
"""

from __future__ import annotations

import json
import re

from app.services.resume_chunk_parser import CHUNK_PROMPTS, merge_chunks

PROMPT = CHUNK_PROMPTS["certifications"]


def _example_output() -> dict:
    """The worked example's ``out:`` line, parsed as the JSON it claims to be."""
    match = re.search(r"^  out: (\{.*\})$", PROMPT, re.M)
    assert match, "the worked mixed-input example is missing its expected output"
    return json.loads(match.group(1))


class TestLineLevelClassificationRule:
    def test_the_rule_is_stated_per_line(self):
        assert "Judge each line by its ITEMS" in PROMPT

    def test_position_in_the_chunk_is_not_the_signal(self):
        """The chunker strips the section heading, so position is all that is
        left of "where the line sits" — and it says nothing."""
        assert "not by where it sits" in PROMPT

    def test_credentials_and_tools_are_distinguished_by_name(self):
        assert (
            "credentials (certifications, licences, assessed training, "
            "qualifications) are certifications"
        ) in PROMPT
        assert (
            "tools, technologies, platforms and competencies are skills"
        ) in PROMPT

    def test_certifications_are_not_merely_technology_names(self):
        """The scope sentence must put tool names on the skills side."""
        assert (
            "credentials (certifications, licences, assessed training, "
            "qualifications) are certifications"
        ) in PROMPT
        assert "are skills" in PROMPT

    def test_skill_lines_may_carry_different_headings(self):
        """The exact shape of the residual failure: the model's own skill
        group was named differently from the line it should have absorbed."""
        assert "skill lines may carry different headings" in PROMPT


class TestWorkedMixedInputExample:
    def test_all_three_input_lines_are_present(self):
        for line in (
            "Professional Credentials: PRINCE2 | Scrum Master",
            "AI & Emerging Technologies: GitHub Copilot | Claude | RAG",
            "AI & Automation: Python | Power Automate",
        ):
            assert line in PROMPT, f"example input line missing: {line!r}"

    def test_the_expected_output_is_valid_json(self):
        """If it is going to show a JSON answer it must be one."""
        _example_output()

    def test_the_credential_line_is_the_only_certification(self):
        example = _example_output()
        assert [(c["name"], c["category"]) for c in example["certifications"]] == [
            ("PRINCE2", "Professional Credentials"),
            ("Scrum Master", "Professional Credentials"),
        ]

    def test_both_tool_lines_are_skills_under_their_own_headings(self):
        example = _example_output()
        assert [(g["category"], g["skills"]) for g in example["skills"]] == [
            ("AI & Emerging Technologies",
             ["GitHub Copilot", "Claude", "RAG"]),
            ("AI & Automation", ["Python", "Power Automate"]),
        ]

    def test_the_example_is_marked_as_not_to_be_emitted(self):
        """A small model will copy an example verbatim if nothing says not to."""
        assert "never emit these items" in PROMPT


class TestExactlyOnceEmission:
    def test_the_prompt_requires_one_key_only(self):
        assert "exactly one key, never both" in PROMPT

    def test_the_example_itself_is_duplicate_free(self):
        example = _example_output()
        cert_items = [c["name"] for c in example["certifications"]]
        skill_items = [s for g in example["skills"] for s in g["skills"]]
        assert not set(cert_items) & set(skill_items)

    def test_the_example_agrees_with_the_reconciliation_policy(self):
        """Prompt and merge must not pull in opposite directions: the answer
        the prompt asks for has to survive the merge unchanged."""
        merged = merge_chunks([("certifications", _example_output())])

        assert [c["name"] for c in merged["certifications"]] == [
            "PRINCE2", "Scrum Master",
        ]
        assert [g["category"] for g in merged["skills"]] == [
            "AI & Emerging Technologies", "AI & Automation",
        ]
        cert_cats = {c["category"] for c in merged["certifications"]}
        skill_cats = {g["category"] for g in merged["skills"]}
        assert not cert_cats & skill_cats


class TestUnchangedContract:
    """What Option 1, the completeness fixture and the schema already rely on."""

    def test_both_top_level_keys_are_still_offered(self):
        assert '"certifications"' in PROMPT
        assert '"skills"' in PROMPT

    def test_the_certification_schema_is_unchanged(self):
        assert '{"certifications": [{"name", "issuer", "date", "url", "category", "values": []}]}' in PROMPT

    def test_metadata_is_not_required(self):
        """issuer/date/url stay optional: the source rarely states them, and
        requiring them would either invent them or drop the credential."""
        assert "Use null for issuer/date/url not stated." in PROMPT

    def test_the_heading_still_sets_the_category(self):
        """`test_parse_completeness` depends on the heading reaching category."""
        assert "set category to that heading on EVERY entry it covers" in PROMPT
        assert "never add an entry for the heading itself" in PROMPT

    def test_every_item_is_still_kept(self):
        assert "Never drop an item." in PROMPT

    def test_the_absent_skills_key_is_still_optional(self):
        assert "Omit the skills key if there are no skill lines." in PROMPT


class TestNoDependencyOnTheStrippedHeading:
    def test_the_stripped_section_heading_is_not_the_signal(self):
        """`chunk_resume` removes this text before the model sees the chunk, so
        a rule keyed to it can never fire — the defect Option 2 replaces."""
        assert "CERTIFICATIONS & PROFESSIONAL DEVELOPMENT" not in PROMPT

    def test_the_replaced_section_heading_rule_is_gone(self):
        """The old primary signal keyed the decision to a heading pattern the
        model never receives; only its replacement may remain."""
        assert "under headings such as" not in PROMPT
        assert "Those lines are NOT certifications" not in PROMPT


class TestPromptSizeStaysInsideTheContextWindow:
    def test_the_prompt_is_not_longer_than_the_recorded_guard_assumes(self):
        """Tripwire for `num_ctx`.

        510 tokens was measured against this fixture when the prompt was 1343
        characters; `_MEASURED_MAX_PROMPT_INPUT` in test_response_truncation
        converts that into the context-window assertion. A prompt that grows
        past here has almost certainly outgrown the measurement, so fail loudly
        and make the next author re-measure rather than trust a stale number.
        """
        assert len(PROMPT) <= 1400, (
            f"certifications prompt is {len(PROMPT)} chars; re-measure "
            "_MEASURED_MAX_PROMPT_INPUT against the real fixture and confirm "
            "prompt + parse_chunk_truncated_num_predict still fits num_ctx"
        )
