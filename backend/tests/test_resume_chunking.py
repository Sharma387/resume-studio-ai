"""Tests for section chunking and chunk-merge (no AI calls involved)."""

import pytest

from app.services.resume_chunk_parser import merge_chunks, parse_chunk
from app.services.resume_chunker import chunk_resume

SAMPLE = """SHARMA RAJASEKAR
Senior Project Manager
Auckland, New Zealand  •  +64 22 451 0637  •  jane@example.com  •  linkedin.com/in/jane

PROFESSIONAL SUMMARY
Seasoned delivery leader with 24+ years of experience.

CORE COMPETENCIES & SKILLS
• Project Management (Agile, SAFe)
• Vendor Management (RFP, SLA)

KEY ACHIEVEMENTS
• Delivered 25+ initiatives per year.

PROFESSIONAL EXPERIENCE
Senior Project Manager  |  EBOS Group Limited
Auckland, New Zealand   •   Jul 2026 – Present
• Delivered 100% of PI commitments.
• Led onboarding of three business units.

Project Manager  |  Infosys Ltd
Auckland, New Zealand   •   May 2022 – Apr 2023
• Ran a competitive RFP for Auckland Council.

EARLY CAREER HIGHLIGHTS
Project Manager, NTT Data, Bangalore — 2003 to 2009
• Delivered clinical patient-care monitoring systems.

EDUCATION
Master of Business Administration (MBA)
Auckland University of Technology (AUT), Auckland   •   Oct 2017 – Jun 2019
• Graduated with an A- cumulative average.

CERTIFICATIONS & PROFESSIONAL DEVELOPMENT
• Professional Credentials: PRINCE2 Practitioner  |  Certified Scrum Master

PROFESSIONAL AWARDS & RECOGNITION
• PEARL Team Award (2025) — EBOS Group Limited: flawless transition.
"""


class TestChunkResume:
    def test_finds_all_sections(self):
        sections = {c["section"] for c in chunk_resume(SAMPLE)}
        assert {
            "header", "summary", "skills", "experience",
            "early_career", "education", "certifications", "awards",
        } <= sections

    def test_experience_split_per_role(self):
        roles = [c for c in chunk_resume(SAMPLE) if c["section"] == "experience"]
        # Two job roles, each with its own chunk (bullets stay with the role).
        assert len(roles) == 2
        assert all("|" in c["text"] for c in roles)
        ebos = next(c for c in roles if "EBOS" in c["text"])
        # The role header must not be split away from its bullets.
        assert "Delivered 100%" in ebos["text"]
        assert "Infosys" not in ebos["text"]

    def test_header_holds_contact_details(self):
        header = next(c for c in chunk_resume(SAMPLE) if c["section"] == "header")
        assert "jane@example.com" in header["text"]
        assert "linkedin.com/in/jane" in header["text"]

    def test_header_keeps_the_candidate_name(self):
        """An ALL-CAPS name must not be trimmed as if it were a section heading.

        The heading-trim used a plain "looks like a heading" test, which matched
        the name, so the parsed resume came back with no name at all.
        """
        header = next(c for c in chunk_resume(SAMPLE) if c["section"] == "header")
        assert header["text"].splitlines()[0].strip() == "SHARMA RAJASEKAR"

    def test_no_content_is_lost(self):
        chunks = chunk_resume(SAMPLE)
        body = " ".join(c["text"] for c in chunks)
        for fact in (
            "EBOS Group Limited", "Infosys Ltd", "NTT Data", "PRINCE2 Practitioner",
            "PEARL Team Award (2025)", "Auckland University of Technology",
            "100% of PI commitments", "A- cumulative average",
        ):
            assert fact in body, fact

    def test_oversized_section_is_split(self):
        big = "CERTIFICATIONS\n" + "\n".join(f"• Cert number {i} detail" for i in range(400))
        chunks = [c for c in chunk_resume(big) if c["section"] == "certifications"]
        assert len(chunks) > 1
        assert all(len(c["text"]) <= 2600 + 200 for c in chunks)

    def test_empty_text(self):
        assert chunk_resume("") == []
        assert chunk_resume("   \n  ") == []

    def test_dash_bullets_never_start_a_new_role(self):
        """A dash-bullet containing a comma looks like a "Title, Employer" header.

        When one was treated as a role header the bullet was orphaned into its
        own chunk, and the merge dropped it for having no company — losing a
        real achievement from the parsed resume.
        """
        text = (
            "PROFESSIONAL EXPERIENCE\n"
            "Agile Delivery Lead  |  EBOS Group Limited\n"
            "Auckland, New Zealand   •   Jul 2026 – Present\n"
            "- Delivered 100% of PI commitments with zero slippages.\n"
            "- Led end-to-end onboarding of Animalcare, HPS and TWC business units.\n"
        )
        roles = [c for c in chunk_resume(text) if c["section"] == "experience"]

        assert len(roles) == 1, "the bullet must not be split off as its own role"
        assert "Animalcare, HPS and TWC" in roles[0]["text"]

    def test_role_header_with_trailing_date_range_splits_per_role(self):
        """'Project Manager, NTT Data, Bangalore — 2003 to 2009' is a role header.

        The trailing year blocked the title/employer match, so several such
        roles landed in one oversized chunk instead of one chunk per role.
        """
        text = (
            "EARLY CAREER HIGHLIGHTS\n"
            "Project Manager, Amadeus Software Labs, Bangalore — 2012 to 2017\n"
            "• Led the mainframe migration programme.\n"
            "Project Manager, Ness Technologies, Bangalore — 2009 to 2012\n"
            "• Migrated legacy reporting to a cloud service.\n"
        )
        roles = [c for c in chunk_resume(text) if c["section"] == "early_career"]

        assert len(roles) == 2
        assert "Amadeus" in roles[0]["text"] and "Ness" not in roles[0]["text"]
        assert "Ness" in roles[1]["text"] and "Amadeus" not in roles[1]["text"]

    def test_lowercase_employer_still_splits_per_role(self):
        """'Project Manager  |  healthAlliance' is a role header.

        The employer group required a leading capital, so a lowercase company
        name was not recognised as a role start. Its lines were then absorbed
        into the *previous* role's chunk, and the model was handed two jobs at
        once — on the real resume it returned only the second, and Datacom
        Systems Ltd vanished with no error logged anywhere.
        """
        text = (
            "PROFESSIONAL EXPERIENCE\n"
            "Project Manager  |  Datacom Systems Ltd \n"
            "Auckland, New Zealand   •   Sep 2021 – Apr 2022 \n"
            "• Delivered a $500K Xero/MYOB API invoice integration.\n"
            "Project Manager  |  healthAlliance \n"
            "Auckland, New Zealand   •   Sep 2019 – Sep 2021 \n"
            "• Managed Northern Region DHB and Ministry of Health initiatives.\n"
        )
        roles = [c for c in chunk_resume(text) if c["section"] == "experience"]

        assert len(roles) == 2, "the two roles must not share a chunk"
        assert "Datacom" in roles[0]["text"] and "healthAlliance" not in roles[0]["text"]
        assert "healthAlliance" in roles[1]["text"] and "Datacom" not in roles[1]["text"]

    @pytest.mark.parametrize(
        "line",
        [
            "Auckland, New Zealand   •   Nov 2024 – Jun 2026 ",
            "Leading Australasian IT services provider spanning cloud, data centre, consulting.",
            "launch; enhanced POS environments for Staples USA.",
            "disruption. ",
        ],
    )
    def test_lowercase_support_does_not_swallow_non_headers(self, line):
        """Allowing a lowercase employer must not turn a location line or a
        wrapped bullet tail into a role boundary, which would orphan content
        into a chunk of its own."""
        text = (
            "PROFESSIONAL EXPERIENCE\n"
            f"Project Manager  |  Datacom Systems Ltd \n{line}\n"
            "Project Manager  |  healthAlliance \n"
            "• Managed Northern Region DHB initiatives.\n"
        )
        roles = [c for c in chunk_resume(text) if c["section"] == "experience"]

        assert len(roles) == 2
        assert "Datacom" in roles[0]["text"] and "healthAlliance" not in roles[0]["text"]


class TestMergeChunks:
    def test_merges_and_sorts_roles(self):
        results = [
            ("header", {"full_name": "Jane Doe", "email": "jane@example.com",
                        "phone": "+64 22 451 0637", "location": "Auckland"}),
            ("experience", {"company": "Old Co", "title": "PM",
                            "start_date": "2003", "end_date": "2009",
                            "description": ["did a thing"]}),
            ("experience", {"company": "New Co", "title": "Lead",
                            "start_date": "2026", "end_date": None, "current": True,
                            "description": ["did another thing", "and a third"]}),
            ("certifications", {"certifications": [
                {"name": "PRINCE2 Practitioner", "issuer": "APMP"},
            ]}),
            ("awards", {"awards": [{"name": "PEARL Team Award", "date": "2025"}]}),
        ]
        merged = merge_chunks(results)
        assert merged["full_name"] == "Jane Doe"
        # Current role sorts first, then most recent.
        assert [e["company"] for e in merged["experience"]] == ["New Co", "Old Co"]
        assert len(merged["experience"][0]["description"]) == 2
        assert merged["certifications"][0]["name"] == "PRINCE2 Practitioner"
        assert merged["awards"][0]["name"] == "PEARL Team Award"

    def test_drops_items_missing_required_fields(self):
        results = [("experience", {"experience": [
            {"title": "No Company"},          # no company -> dropped
            {"company": "Acme", "title": "PM"},
        ]})]
        merged = merge_chunks(results)
        assert len(merged["experience"]) == 1
        assert merged["experience"][0]["company"] == "Acme"

    def test_later_summary_does_not_clobber_earlier(self):
        results = [
            ("summary", {"summary": "The real summary."}),
            ("header", {"full_name": "Jane", "summary": "short"}),
        ]
        assert merge_chunks(results)["summary"] == "The real summary."


class TestParseChunk:
    async def test_parses_valid_json(self):
        async def call(system, user):
            return '{"company": "Acme", "title": "PM", "description": ["a"]}'

        out = await parse_chunk("experience", "text", call)
        assert out["company"] == "Acme"

    async def test_tolerates_prose_around_json(self):
        async def call(system, user):
            return 'Sure!\n```json\n{"company": "Acme", "title": "PM"}\n```'

        assert (await parse_chunk("experience", "t", call))["title"] == "PM"

    async def test_returns_empty_on_invalid_json(self):
        async def call(system, user):
            return "I could not parse this resume."

        assert await parse_chunk("experience", "t", call) == {}

    async def test_returns_empty_when_provider_fails(self):
        async def call(system, user):
            raise RuntimeError("provider down")

        assert await parse_chunk("experience", "t", call) == {}
