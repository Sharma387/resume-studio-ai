"""Certifications and skills are two sections, and neither may swallow the other.

Two defects were found while diagnosing why certification and skill counts
swung between runs of the real V4.1 resume (certifications 31<->37, skills
2<->9). Both were deterministic, and neither was about recall — every source
line was captured in every run. The instability came from *where* the content
landed.

**A. Skills emitted from a certifications chunk were discarded.** A resume
heading reading "CERTIFICATIONS & PROFESSIONAL DEVELOPMENT" routinely lists
tools underneath it. The prompt gave the model no way to say so, and when a
model did add a ``skills`` key anyway, ``merge_chunks`` routed by section
label alone and never looked at it — so a correct judgement became data loss.

**C. A qualified awards heading was not a heading at all.** The pattern was
anchored as ``^\\s*(professional\\s+)?(awards?|...)``, so "KEY ACHIEVEMENTS"
matched nothing. Its bullets were absorbed into the preceding skills section,
and the model then invented skill groups to hold them ("Project Delivery &
Achievement") — the source of the skills-count swing.

These tests pin both. The deliberate omission: nothing here decides *whether* a
line is a credential or a skill. That judgement still belongs to the model, and
this file only asserts that whatever it decides survives the merge.
"""

from __future__ import annotations

import pytest

from app.services.resume_chunk_parser import CHUNK_PROMPTS, merge_chunks, parse_chunk
from app.services.resume_chunker import _is_heading, chunk_resume

# The real resume's shape: one credentials line, then six tool-category lines
# that share the certifications heading, plus a separate competencies section.
SAMPLE = """SHARMA RAJASEKAR
Senior Project Manager
Auckland, New Zealand

PROFESSIONAL SUMMARY
Senior project manager with 24+ years of delivery experience.

CORE COMPETENCIES & SKILLS
• Project & Programme Management (SAFe, Agile, Waterfall)
• Cross-functional Team Leadership (60+ resources)

KEY ACHIEVEMENTS
• Delivered 100% of Program Increment commitments with zero slippages.
• Reduced infrastructure run costs by $1.2M per annum.

PROFESSIONAL EXPERIENCE
Agile Delivery Lead  |  EBOS Group Limited
Auckland, New Zealand   •   Jul 2026 – Present
• Delivered 100% of PI commitments.

EDUCATION
Master of Business Administration (MBA)

CERTIFICATIONS & PROFESSIONAL DEVELOPMENT
• Professional Credentials: PRINCE2 Practitioner  |  Certified Scrum Master (CSM)  |  ITIL Foundation Certificate
• AI & Emerging Technologies: GitHub Copilot, Claude, Prompt Engineering, RAG
• Cloud, IT Infrastructure & Security: ClearPass, Cloud Infrastructure

PROFESSIONAL AWARDS & RECOGNITION
• PEARL Team Award (2025) — EBOS Group Limited: flawless transition.
"""


class TestSkillsFromCertificationsChunkSurvive:
    """Fix A: the merge must believe the model about which section a line is in."""

    def test_both_keys_in_one_chunk_both_land(self):
        chunk = {
            "certifications": [
                {"name": "PRINCE2 Practitioner", "category": "Professional Credentials"},
                {"name": "ITIL Foundation Certificate", "category": "Professional Credentials"},
            ],
            "skills": [{"category": "AI & Emerging Technologies", "skills": ["Claude", "RAG"]}],
        }
        merged = merge_chunks([("certifications", chunk)])

        assert [c["name"] for c in merged["certifications"]] == [
            "PRINCE2 Practitioner",
            "ITIL Foundation Certificate",
        ]
        assert merged["skills"] == [
            {"category": "AI & Emerging Technologies", "skills": ["Claude", "RAG"]}
        ]

    def test_skills_key_is_not_silently_dropped(self):
        """The exact loss: a model spots the tools are skills, output vanishes."""
        chunk = {
            "certifications": [{"name": "PMP", "category": "Professional Credentials"}],
            "skills": [{"category": "Cloud & Security", "skills": ["ClearPass"]}],
        }
        merged = merge_chunks([("certifications", chunk)])

        assert merged["certifications"], "certification itself must still be kept"
        assert merged["skills"], "the skills key was discarded"
        assert merged["skills"][0]["skills"] == ["ClearPass"]

    def test_every_source_line_lands_in_exactly_one_section(self):
        """No line may be double-counted or lost, whichever key it was put in."""
        chunk = {
            "certifications": [{"name": "PMP", "category": "Professional Credentials"}],
            "skills": [
                {"category": "AI & Emerging Technologies", "skills": ["Claude", "RAG"]},
                {"category": "Cloud & Security", "skills": ["ClearPass"]},
            ],
        }
        merged = merge_chunks([("certifications", chunk)])

        certs = {c.get("name") for c in merged["certifications"]}
        skills = {s for g in merged["skills"] for s in g["skills"]}
        assert certs == {"PMP"}
        assert skills == {"Claude", "RAG", "ClearPass"}
        assert not certs & skills, "a line was placed in both sections"

    def test_absent_skills_key_still_merges_certifications(self):
        """The common case must be untouched: no skills key, no error, no junk."""
        merged = merge_chunks(
            [("certifications", {"certifications": [{"name": "PMP", "category": "Credentials"}]})]
        )
        assert [c["name"] for c in merged["certifications"]] == ["PMP"]
        assert merged["skills"] == []

    def test_malformed_groups_rejected_by_the_same_rules_as_skills_section(self):
        """Validation is shared, so a bad group is refused from either section."""
        bad = {"skills": [{"nope": 1}, {"skills": ["orphan"]}, "not-a-dict", None]}
        assert merge_chunks([("skills", dict(bad))])["skills"] == []
        assert merge_chunks([("certifications", dict(bad))])["skills"] == []

    def test_skills_from_certifications_accumulate_with_the_skills_section(self):
        """Both sections can contribute; neither overwrites the other."""
        merged = merge_chunks([
            ("skills", {"skills": [{"category": "Core", "skills": ["SAFe"]}]}),
            ("certifications", {"skills": [{"category": "AI & Data", "skills": ["Claude"]}]}),
        ])
        assert [g["category"] for g in merged["skills"]] == ["Core", "AI & Data"]

    async def test_prompt_offers_the_skills_key(self):
        """The prompt must ask for it, or the model is guessing at the schema."""
        prompt = CHUNK_PROMPTS["certifications"]
        assert '"skills"' in prompt
        assert '"certifications"' in prompt

    async def test_parse_chunk_keeps_both_keys_end_to_end(self):
        """Full path: model text in, both sections out. No AI call is made."""
        raw = (
            '{"certifications": [{"name": "PMP", "category": "Professional Credentials"}], '
            '"skills": [{"category": "AI & Emerging Technologies", "skills": ["Claude"]}]}'
        )

        async def call(system, text):
            return raw

        merged = merge_chunks([("certifications", await parse_chunk("certifications", SAMPLE, call))])
        assert [c["name"] for c in merged["certifications"]] == ["PMP"]
        assert merged["skills"] == [{"category": "AI & Emerging Technologies", "skills": ["Claude"]}]


class TestQualifiedAwardsHeadings:
    """Fix C: a qualifier in front of the noun must not hide a section."""

    @pytest.mark.parametrize(
        "heading",
        [
            "KEY ACHIEVEMENTS",
            "SELECTED ACHIEVEMENTS",
            "CAREER ACHIEVEMENTS",
            "SELECTED AWARDS",
            "MAJOR RECOGNITIONS",
            "KEY AWARDS AND RECOGNITION",
        ],
    )
    def test_qualified_heading_is_recognised(self, heading):
        assert _is_heading(heading) == "awards"

    @pytest.mark.parametrize(
        "heading",
        ["ACHIEVEMENTS", "AWARDS", "HONOURS", "RECOGNITION", "PROFESSIONAL AWARDS & RECOGNITION"],
    )
    def test_existing_unqualified_forms_still_work(self, heading):
        assert _is_heading(heading) == "awards"

    @pytest.mark.parametrize(
        "prose",
        [
            "Delivered 25 awards and recognition across the programme",
            "Selected awards for innovation in 2025",
            "Career achievements were recognised by the council",
            "Key achievements were noted by the board",
            "• Key achievements delivered in FY25",
        ],
    )
    def test_prose_is_not_mistaken_for_a_heading(self, prose):
        """A free-form qualifier is only honoured on a standalone heading line."""
        assert _is_heading(prose) is None

    def test_achievement_bullets_leave_the_skills_chunk(self):
        skills = next(c for c in chunk_resume(SAMPLE) if c["section"] == "skills")

        assert "Program Increment" not in skills["text"]
        assert "run costs" not in skills["text"]
        assert "Project & Programme Management" in skills["text"]

    def test_achievements_get_their_own_chunk(self):
        chunks = chunk_resume(SAMPLE)
        achievements = [c for c in chunks if c["section"] == "awards"]

        # KEY ACHIEVEMENTS and PROFESSIONAL AWARDS are two separate sections.
        assert len(achievements) == 2
        key_chunk = next(c for c in achievements if "Program Increment" in c["text"])
        assert "run costs" in key_chunk["text"]
        # And neither is the real awards list.
        assert "PEARL Team Award" not in key_chunk["text"]

    def test_no_text_is_lost_by_the_new_split(self):
        """A new boundary must not drop or duplicate a line."""
        for line in ("Project & Programme Management", "Delivered 100% of PI commitments",
                     "Reduced infrastructure run costs", "PRINCE2 Practitioner",
                     "PEARL Team Award"):
            hits = sum(1 for c in chunk_resume(SAMPLE) if line in c["text"])
            assert hits == 1, f"{line!r} appears in {hits} chunks"

    def test_other_sections_are_unaffected(self):
        sections = {c["section"] for c in chunk_resume(SAMPLE)}
        assert {
            "header", "summary", "skills", "experience",
            "education", "certifications", "awards",
        } <= sections


class TestCertificationsChunkContent:
    """The certifications chunk keeps both credentials and tool lines intact."""

    def test_chunk_carries_every_line_of_the_section(self):
        chunk = next(c for c in chunk_resume(SAMPLE) if c["section"] == "certifications")

        for line in ("Professional Credentials", "AI & Emerging Technologies",
                     "Cloud, IT Infrastructure & Security"):
            assert line in chunk["text"], f"{line!r} dropped from the chunk"

    def test_the_three_genuine_credentials_are_present(self):
        """Completeness check, stated as presence rather than as a count.

        Counts are not a completeness signal: a model that splits a category
        line into more or fewer entries changes the count without losing text.
        """
        chunk = next(c for c in chunk_resume(SAMPLE) if c["section"] == "certifications")

        for credential in ("PRINCE2 Practitioner", "Certified Scrum Master (CSM)",
                           "ITIL Foundation Certificate"):
            assert credential in chunk["text"]
