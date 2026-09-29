"""End-to-end test of the chunked parse pipeline with a stubbed model.

The contract under test is the one the parser exists to satisfy: no fact in the
source resume may be lost on the way to the parsed :class:`Resume`. The stub
stands in for the LLM — it reads each chunk and fills in the schema that
chunk's prompt asks for — so anything dropped by chunking, dispatch, merging,
or coercion shows up as a missing fact in the final output.
"""

from __future__ import annotations

import json
import re

import pytest

from app.services.parser_service import parse_resume

RESUME_TEXT = """SHARMA RAJASEKAR
Agile Delivery Lead | IT Infrastructure Program Specialist
Auckland, New Zealand | +64 22 451 0637 | sharma.rajasekar@gmail.com
linkedin.com/in/sharma-rajasekar-46b4738

PROFESSIONAL SUMMARY
Seasoned delivery leader with 24 years of enterprise infrastructure, cloud and
cybersecurity experience across healthcare, airline and utility sectors.

CORE COMPETENCIES & SKILLS
Agile Delivery & Scrum
  Servant Leadership, Coaching, Release Planning
Project & Programme Management
  Vendor Management, Financial Management, Risk Governance

KEY ACHIEVEMENTS
Delivered 100% of Program Increment commitments with zero slippages.
Reduced infrastructure run costs by $1.2M per annum.

PROFESSIONAL EXPERIENCE

Agile Delivery Lead | EBOS Group Limited
Auckland, New Zealand   -   Jul 2026 - Present
- Delivered 100% of Program Increment (PI) commitments with zero slippages.
- Led end-to-end onboarding of Animalcare, HPS and TWC business units.

IT Infrastructure Project Specialist | EBOS Group Limited
Auckland, New Zealand   -   Sep 2021 - Jun 2026
- Migrated 42 servers to a hardened cloud landing zone with zero downtime.
- Owned a $5M annual infrastructure budget and vendor portfolio.

EARLY CAREER HIGHLIGHTS

Systems Administrator, Datacom, Auckland - Mar 2015 to Aug 2017
- Administered Linux and Windows estates across 14 sites.

EDUCATION
Master of Business Administration (Full-Time MBA Candidate)
Auckland University of Technology | Oct 2017 - Jun 2019
- Graduated with distinction.
- Led the capstone consulting project for a national healthcare client.

CERTIFICATIONS & PROFESSIONAL DEVELOPMENT
Professional Credentials: PMP | PRINCE2 Practitioner | Scrum Master
Cloud & Architecture: AWS Solutions Architect | Azure Fundamentals

PROFESSIONAL AWARDS & RECOGNITION
PEARL Team Award 2025 - EBOS Group Limited
Dream Team Award 2016 - healthAlliance
"""

_BULLET = re.compile(r"^\s*[-–—•*▪◦·]\s+")
_MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*"
_SPAN = re.compile(
    rf"({_MONTH}\s+(?:19|20)\d{{2}})\s*(?:-|–|—|to)\s*"
    rf"({_MONTH}\s+(?:19|20)\d{{2}}|Present|Current)"
)


def _bullets(text: str) -> list[str]:
    """The achievement bullets in a chunk, marker stripped, in order."""
    found = []
    for line in text.splitlines():
        if _BULLET.match(line):
            body = _BULLET.sub("", line).strip()
            if body:
                found.append(body)
    return found


def _role(text: str) -> dict:
    """Build one role from a chunk the way a competent model would."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    header = lines[0]

    # Two header styles: "Title | Company, City" and "Title, Company, City".
    if "|" in header:
        title, _, rest = header.partition("|")
        parts = [p.strip() for p in rest.split(",")]
        company = parts[0] if parts else ""
        place = parts[1] if len(parts) > 1 else ""
    else:
        parts = [p.strip() for p in header.split(",")]
        title = parts[0] if parts else ""
        company = parts[1] if len(parts) > 1 else ""
        place = parts[2] if len(parts) > 2 else ""
    place = _SPAN.sub("", place).strip(" -–—,")

    span = _SPAN.search(" ".join(lines[1:]))
    start, end = (span.group(1), span.group(2)) if span else (None, None)

    role = {"company": company, "title": title.strip(), "description": _bullets(text)}
    if place:
        role["location"] = place
    if start:
        role["start_date"] = start
    if end:
        role["end_date"] = end
        role["current"] = end.lower() in ("present", "current")
    return role


def _fake_model(system: str, user: str) -> str:
    """Stand in for the LLM, filling in the schema the chunk's prompt asks for."""
    lines = [line.strip() for line in user.splitlines() if line.strip()]

    if "contact header" in system:
        return json.dumps(
            {
                "full_name": lines[0],
                "professional_title": lines[1],
                "location": "Auckland, New Zealand",
                "phone": "+64 22 451 0637",
                "email": "sharma.rajasekar@gmail.com",
                "linkedin": "https://linkedin.com/in/sharma-rajasekar-46b4738",
            }
        )
    if "summary/profile text" in system:
        return json.dumps({"summary": " ".join(lines)})
    if "skills section" in system:
        return json.dumps({"skills": [{"category": "Competencies", "skills": lines}]})
    if "this ONE job role" in system:
        return json.dumps(_role(user))
    if "EVERY earlier job role" in system:
        # Every role in the chunk, not just the first.
        blocks = re.split(r"(?m)^(?=[^•\n-]*[A-Z][^•\n]*,)", user)
        return json.dumps({"experience": [_role(b) for b in blocks if _bullets(b)]})
    if "every qualification" in system:
        return json.dumps(
            {
                "education": [
                    {
                        "institution": lines[1].split("|")[0].strip() if len(lines) > 1 else "",
                        "degree": lines[0],
                        "achievements": _bullets(user),
                    }
                ]
            }
        )
    if "EVERY certification" in system:
        certs = []
        for line in lines:
            group, _, items = line.partition(":")
            for item in items.split("|"):
                if item.strip():
                    certs.append({"name": item.strip(), "category": group.strip()})
        return json.dumps({"certifications": certs})
    if "EVERY award" in system:
        return json.dumps(
            {"awards": [{"name": ln.split(" - ")[0], "issuer": ln.split(" - ")[-1]} for ln in lines]}
        )
    if "every project" in system:
        return json.dumps({"projects": []})
    if "every language" in system:
        return json.dumps({"languages": []})
    return json.dumps({})


def source_bullets(text: str) -> list[str]:
    return _bullets(text)


class TestParseCompleteness:
    @pytest.fixture(autouse=True)
    def _stub_model(self, monkeypatch):
        async def fake_chat(system, user, **kwargs):
            return _fake_model(system, user)

        monkeypatch.setattr("app.services.parser_service.chat_providers", fake_chat)
        # The audit pass is a reporting tool, covered by its own test.
        monkeypatch.setattr(
            "app.services.parser_service.settings.parse_verify_completeness", False
        )

    async def test_every_bullet_survives_verbatim(self):
        """The core guarantee: no achievement bullet may be lost or shortened."""
        resume = await parse_resume(RESUME_TEXT)
        bullets = [b for role in resume.experience for b in (role.description or [])]
        bullets += [a for e in resume.education for a in (e.achievements or [])]

        expected = source_bullets(RESUME_TEXT)
        assert expected, "fixture must contain bullets"
        for bullet in expected:
            assert bullet in bullets, f"bullet lost: {bullet!r}"

    async def test_every_role_survives_with_its_dates(self):
        resume = await parse_resume(RESUME_TEXT)
        employers = {r.company for r in resume.experience}

        assert {"EBOS Group Limited", "Datacom"} <= employers
        ebos_lead = next(r for r in resume.experience if r.title.startswith("Agile Delivery Lead"))
        assert ebos_lead.start_date and ebos_lead.end_date
        assert ebos_lead.current is True

    async def test_identity_and_contact_details_survive(self):
        resume = await parse_resume(RESUME_TEXT)
        assert resume.full_name == "SHARMA RAJASEKAR"
        assert resume.email == "sharma.rajasekar@gmail.com"
        assert resume.phone == "+64 22 451 0637"
        assert "Auckland" in (resume.location or "")
        assert "linkedin.com/in/sharma-rajasekar" in str(resume.linkedin or "")

    async def test_summary_and_skills_survive(self):
        resume = await parse_resume(RESUME_TEXT)
        assert "24 years" in (resume.summary or "")
        assert resume.skills
        skills = {s for group in resume.skills for s in group.skills}
        assert any("Scrum" in s for s in skills)

    async def test_every_certification_and_award_survives(self):
        resume = await parse_resume(RESUME_TEXT)
        certs = " ".join(c.name or "" for c in resume.certifications)
        for cert in ("PMP", "PRINCE2 Practitioner", "Scrum Master",
                     "AWS Solutions Architect", "Azure Fundamentals"):
            assert cert in certs, f"certification lost: {cert}"

        awards = " ".join(a.name or "" for a in resume.awards)
        assert "PEARL Team Award 2025" in awards
        assert "Dream Team Award 2016" in awards

    async def test_education_achievements_survive(self):
        resume = await parse_resume(RESUME_TEXT)
        assert len(resume.education) >= 1
        education = resume.education[0]
        assert "MBA" in (education.degree or "")
        assert "Auckland University of Technology" in (education.institution or "")
        assert len(education.achievements or []) == 2
