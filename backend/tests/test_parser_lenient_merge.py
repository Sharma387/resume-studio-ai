"""A single malformed value must not discard a whole parsed resume.

The GPA field is the concrete case seen on the real resume: a model returned
``"gpa": "A-"`` (a letter grade) into a ``float`` field, pydantic rejected the
whole document, and the parse fell through to the slow single-shot retry —
throwing away a resume that had parsed correctly. These tests pin the
behaviour: repair what can be repaired, shed only what cannot.
"""

from __future__ import annotations

import pytest

from app.services.parser_service import _build_resume_lenient, _gpa_as_float

BASE = {
    "full_name": "Rajasekar Sharma",
    "email": "sharma.rajasekar@gmail.com",
    "phone": "+64 22 451 0637",
    "location": "Auckland, New Zealand",
    "summary": "Senior project manager.",
}


class TestGpaCoercion:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            (3.8, 3.8),
            (4.0, 4.0),
            (0, 0.0),
            ("3.8", 3.8),
            ("GPA: 3.8 / 4.0", 3.8),
            ("3.75", 3.75),
            (None, None),
            ("", None),
        ],
    )
    def test_accepted_forms(self, raw, expected):
        assert _gpa_as_float(raw) == expected

    @pytest.mark.parametrize("raw", ["A-", "Distinction", "85%", "4.0/5.0", "Pass", True, False])
    def test_unrepresentable_forms_become_none(self, raw):
        """A letter grade or a 5-point scale has no 0-4 float equivalent, so it
        is dropped rather than allowed to fail the document."""
        assert _gpa_as_float(raw) is None


class TestLenientMerge:
    def test_letter_grade_gpa_keeps_the_whole_resume(self):
        payload = {
            **BASE,
            "education": [
                {
                    "institution": "AUT University",
                    "degree": "MBA",
                    "gpa": "A-",
                    "achievements": ["Distinction"],
                }
            ],
            "experience": [
                {
                    "company": "Transdev Auckland",
                    "title": "Senior Project Manager",
                    "description": ["Delivered a $4M programme"],
                }
            ],
        }
        resume = _build_resume_lenient(payload)

        assert resume is not None, "one bad GPA must not discard the parse"
        assert resume.full_name == "Rajasekar Sharma"
        assert len(resume.experience) == 1
        assert len(resume.education) == 1
        assert resume.education[0].gpa is None
        # The rest of the education entry survives.
        assert resume.education[0].achievements == ["Distinction"]

    def test_numeric_gpa_is_preserved(self):
        payload = {**BASE, "education": [{"institution": "AUT", "degree": "MBA", "gpa": "3.9"}]}
        resume = _build_resume_lenient(payload)
        assert resume is not None
        assert resume.education[0].gpa == pytest.approx(3.9)

    def test_one_broken_role_is_dropped_and_others_survive(self):
        """This is the requirement that matters most: nine good roles must not
        be lost because the tenth is missing its title."""
        roles = [
            {"company": f"Company {i}", "title": f"Role {i}", "description": [f"bullet {i}"]}
            for i in range(9)
        ]
        roles.insert(4, {"company": "Mystery Corp"})  # no title
        resume = _build_resume_lenient({**BASE, "experience": roles})

        assert resume is not None
        assert len(resume.experience) == 9, "only the untitled role should be dropped"
        assert all(r.title for r in resume.experience)
        assert {r.company for r in resume.experience} == {f"Company {i}" for i in range(9)}

    def test_multiple_broken_roles_are_all_dropped(self):
        roles = [
            {"company": "Good Co", "title": "PM", "description": ["a"]},
            {"company": "Bad Co"},
            {"company": "Also Bad"},
            {"company": "Fine Co", "title": "Lead", "description": ["b"]},
        ]
        resume = _build_resume_lenient({**BASE, "experience": roles})
        assert resume is not None
        assert [r.company for r in resume.experience] == ["Good Co", "Fine Co"]

    def test_repeated_broken_roles_across_rounds(self):
        """Indices shift as items are removed, so repair has to re-check."""
        roles = [{"company": f"C{i}"} for i in range(5)]
        roles.append({"company": "Keeper", "title": "PM", "description": ["ok"]})
        resume = _build_resume_lenient({**BASE, "experience": roles})
        assert resume is not None
        assert [r.company for r in resume.experience] == ["Keeper"]

    def test_gpa_and_broken_role_together(self):
        payload = {
            **BASE,
            "education": [{"institution": "AUT", "degree": "MBA", "gpa": "A-"}],
            "experience": [
                {"company": "Good", "title": "PM", "description": ["x"]},
                {"company": "Broken"},
            ],
        }
        resume = _build_resume_lenient(payload)
        assert resume is not None
        assert len(resume.experience) == 1
        assert len(resume.education) == 1

    def test_missing_identity_is_not_salvageable(self):
        """With no name or email there is no resume to build; the caller needs
        to know so it can try another strategy."""
        assert _build_resume_lenient({"summary": "something"}) is None

    def test_input_dict_is_not_mutated(self):
        payload = {**BASE, "education": [{"institution": "AUT", "degree": "MBA", "gpa": "A-"}]}
        _build_resume_lenient(payload)
        assert payload["education"][0]["gpa"] == "A-", "caller's data must be left alone"

    def test_empty_education_list_is_fine(self):
        resume = _build_resume_lenient({**BASE, "education": [], "experience": []})
        assert resume is not None
        assert resume.education == []
