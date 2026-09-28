"""Identity fields are transcribed, not reasoned about — so the source wins.

A small local model reliably garbled the contact header on the real resume: it
rendered ``sharma.rajasekar@gmail.com`` as ``sharma.rajasekhar@gmail.com`` and
invented the location "Bangalore" for a candidate based in Auckland. The
extracted text is authoritative for these fields, so a model value that cannot
be found verbatim in the source is replaced by one that can. Nothing is
invented, and a correct model output is left untouched.
"""

from __future__ import annotations

from app.services.parser_service import _correct_identity_from_source

HEADER = """SHARMA RAJASEKAR
Senior Project Manager  |  Agile Delivery Lead  |  IT Infrastructure Specialist
Auckland, New Zealand   \u2022   +64 22 451 0637   \u2022   sharma.rajasekar@gmail.com   \u2022   linkedin.com/in/sharma-rajasekar-46b4738
"""


class TestEmail:
    def test_misspelled_email_is_corrected_from_the_source(self):
        data = {"email": "sharma.rajasekhar@gmail.com"}
        out = _correct_identity_from_source(data, HEADER)
        assert out["email"] == "sharma.rajasekar@gmail.com"

    def test_correct_email_is_left_alone(self):
        data = {"email": "sharma.rajasekar@gmail.com"}
        assert _correct_identity_from_source(data, HEADER)["email"] == "sharma.rajasekar@gmail.com"

    def test_case_difference_is_not_treated_as_an_error(self):
        data = {"email": "Sharma.Rajasekar@Gmail.com"}
        assert _correct_identity_from_source(data, HEADER)["email"] == "Sharma.Rajasekar@Gmail.com"

    def test_missing_email_is_filled_in(self):
        data = {"email": None}
        assert _correct_identity_from_source(data, HEADER)["email"] == "sharma.rajasekar@gmail.com"

    def test_no_email_in_source_leaves_the_value_untouched(self):
        data = {"email": "someone@else.com"}
        assert _correct_identity_from_source(data, "No contact details here.")["email"] == "someone@else.com"


class TestPhone:
    def test_invented_phone_is_replaced(self):
        data = {"phone": "+1 555 123 4567"}
        assert _correct_identity_from_source(data, HEADER)["phone"] == "+64 22 451 0637"

    def test_correct_phone_with_different_punctuation_is_kept(self):
        data = {"phone": "+64-22-451-0637"}
        assert _correct_identity_from_source(data, HEADER)["phone"] == "+64-22-451-0637"

    def test_correct_phone_is_kept(self):
        data = {"phone": "+64 22 451 0637"}
        assert _correct_identity_from_source(data, HEADER)["phone"] == "+64 22 451 0637"

    def test_empty_phone_is_not_invented(self):
        data = {"phone": ""}
        assert _correct_identity_from_source(data, HEADER)["phone"] == ""


class TestLocation:
    def test_hallucinated_location_is_replaced(self):
        """The exact failure seen live: "Bangalore" for an Auckland-based
        candidate."""
        data = {"location": "Bangalore"}
        assert _correct_identity_from_source(data, HEADER)["location"] == "Auckland, New Zealand"

    def test_correct_location_is_left_alone(self):
        data = {"location": "Auckland, New Zealand"}
        assert _correct_identity_from_source(data, HEADER)["location"] == "Auckland, New Zealand"

    def test_lowercase_variant_is_left_alone(self):
        data = {"location": "auckland, new zealand"}
        assert _correct_identity_from_source(data, HEADER)["location"] == "auckland, new zealand"

    def test_an_earlier_jobs_location_is_not_mistaken_for_the_contacts(self):
        """The contact header must beat a location that appears only in the
        body. On the real resume the model returned "Bangalore", which is the
        location of the 2012 Amadeus role, not where the candidate lives."""
        text = (
            HEADER
            + "\nPROFESSIONAL EXPERIENCE\n"
            "Senior Project Manager (Agile/Waterfall), Amadeus Software Labs, Bangalore \u2014 2012 to 2017\n"
            "Project Manager, NTT Data, Bangalore \u2014 2003 to 2009\n"
        )
        data = {"full_name": "SHARMA RAJASEKAR", "location": "Bangalore"}
        assert _correct_identity_from_source(data, text)["location"] == "Auckland, New Zealand"

    def test_a_correct_location_from_the_body_is_kept(self):
        """If the model's value really is the contact line's, it stays."""
        text = HEADER + "\nEXPERIENCE\nManager, Somewhere, Auckland, New Zealand \u2014 2020\n"
        data = {"full_name": "SHARMA RAJASEKAR", "location": "Auckland, New Zealand"}
        assert _correct_identity_from_source(data, text)["location"] == "Auckland, New Zealand"

    def test_empty_location_is_not_invented(self):
        data = {"location": ""}
        assert _correct_identity_from_source(data, HEADER)["location"] == ""


class TestLinkedin:
    def test_invented_linkedin_url_is_dropped(self):
        data = {"linkedin": "https://linkedin.com/in/someone-else"}
        assert _correct_identity_from_source(data, "Resume with no social links.")["linkedin"] is None

    def test_linkedin_from_the_source_is_kept(self):
        url = "https://linkedin.com/in/sharma-rajasekar-46b4738"
        data = {"linkedin": url}
        assert _correct_identity_from_source(data, HEADER)["linkedin"] == url


class TestNonInterference:
    def test_other_fields_are_untouched(self):
        data = {
            "full_name": "SHARMA RAJASEKAR",
            "professional_title": "Senior Project Manager",
            "summary": "A long summary.",
            "experience": [{"company": "EBOS", "title": "PM"}],
        }
        out = _correct_identity_from_source(data, HEADER)
        assert out["full_name"] == "SHARMA RAJASEKAR"
        assert out["professional_title"] == "Senior Project Manager"
        assert out["summary"] == "A long summary."
        assert out["experience"] == [{"company": "EBOS", "title": "PM"}]

    def test_does_not_mutate_the_caller_dicts_identity_when_absent(self):
        data = {}
        out = _correct_identity_from_source(data, HEADER)
        assert out is not None
        # A resume with no contact fields keeps them unset rather than gaining
        # invented ones.
        assert "linkedin" not in out or out["linkedin"] is None
