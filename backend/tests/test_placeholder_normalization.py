"""Tests for placeholder values a model returns in place of a null.

Models answer "unknown" fields with prose ("Not specified", "N/A") instead of
null. Those are not URLs, and prefixing them produced ``https://Not specified``,
which failed ``HttpUrl`` and silently dropped entire records — a resume whose
certifications all carried a placeholder URL parsed to zero certifications.
"""

import pytest

from app.models.resume import Resume

PLACEHOLDERS = [
    "Not specified",
    "not specified",
    "NOT SPECIFIED",
    "N/A",
    "n/a",
    "none",
    "None",
    "null",
    "Not available",
    "Not applicable",
    "unknown",
    "  ",
    "",
    "-",
]

REAL = {
    "name": "PRINCE2 Practitioner",
    "issuer": "PeopleCert",
    "date": "2019",
    "url": "https://peoplecert.org",
    "category": "Professional Credentials",
    "values": [],
}


def _resume(cert: dict) -> Resume:
    return Resume.model_validate(
        {"user_id": "u", "email": "a@b.com", "full_name": "X", "certifications": [cert]}
    )


class TestCertificationPlaceholders:
    @pytest.mark.parametrize("placeholder", PLACEHOLDERS)
    def test_placeholder_url_does_not_drop_the_record(self, placeholder):
        resume = _resume({**REAL, "url": placeholder})
        assert len(resume.certifications) == 1
        assert resume.certifications[0].url is None

    @pytest.mark.parametrize("placeholder", PLACEHOLDERS)
    def test_placeholder_issuer_and_date_become_null(self, placeholder):
        resume = _resume({**REAL, "issuer": placeholder, "date": placeholder})
        cert = resume.certifications[0]
        assert cert.issuer is None
        assert cert.date is None

    def test_real_values_are_preserved(self):
        cert = _resume(REAL).certifications[0]
        assert cert.issuer == "PeopleCert"
        assert cert.date == "2019"
        assert str(cert.url) == "https://peoplecert.org/"

    def test_placeholder_credential_groups_under_its_category(self):
        """A placeholder must not make a list item look like a standalone card."""
        from app.rendering.cert_grouping import group_certs

        resume = Resume.model_validate(
            {
                "user_id": "u",
                "email": "a@b.com",
                "full_name": "X",
                "certifications": [
                    {"name": "PRINCE2 Practitioner", "issuer": "Not specified", "date": "Not specified", "url": "Not specified", "category": "Professional Credentials", "values": []},
                    {"name": "ITIL Foundation", "issuer": "N/A", "date": "", "url": None, "category": "Professional Credentials", "values": []},
                    {"name": "PMP", "issuer": "PMI", "date": "2025", "url": None, "category": "Professional Credentials", "values": []},
                ],
            }
        )
        slots = group_certs(resume.certifications)
        assert len(slots) == 2
        assert not slots[0].is_card
        assert slots[0].values == ["PRINCE2 Practitioner", "ITIL Foundation"]
        assert "Not specified" not in slots[0].logical_text()
        assert slots[1].is_card

    def test_full_section_of_placeholders_survives(self):
        """The reported failure: every credential carried a placeholder URL."""
        resume = Resume.model_validate(
            {
                "user_id": "u",
                "email": "a@b.com",
                "full_name": "X",
                "certifications": [
                    {"name": f"Cert {i}", "issuer": "Not specified", "date": "Not specified", "url": "Not specified", "category": "AI", "values": []}
                    for i in range(31)
                ],
            }
        )
        assert len(resume.certifications) == 31


class TestOtherUrlFields:
    @pytest.mark.parametrize("placeholder", ["Not specified", "N/A", "", "  "])
    def test_project_url_placeholder_becomes_null(self, placeholder):
        resume = Resume.model_validate(
            {
                "user_id": "u",
                "email": "a@b.com",
                "full_name": "X",
                "projects": [{"name": "P", "url": placeholder}],
            }
        )
        assert resume.projects[0].url is None

    @pytest.mark.parametrize("placeholder", ["Not specified", "N/A", ""])
    def test_linkedin_placeholder_becomes_null(self, placeholder):
        resume = Resume.model_validate(
            {"user_id": "u", "email": "a@b.com", "full_name": "X", "linkedin": placeholder}
        )
        assert resume.linkedin is None

    def test_schemeless_url_still_gets_a_scheme(self):
        resume = Resume.model_validate(
            {"user_id": "u", "email": "a@b.com", "full_name": "X", "linkedin": "linkedin.com/in/jane"}
        )
        assert str(resume.linkedin).startswith("https://")
