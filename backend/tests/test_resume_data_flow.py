"""Resume → CVM data-flow tests (professional_title, awards, languages).

Proves the fields survive: domain model → parser-style payload → JSON
serialization → cvm_from_resume → RenderContext → TreeBuilder → HTML.
"""

import pytest
from pydantic import ValidationError

from app.models.resume import Award, Language, Resume
from app.rendering.content import cvm_from_resume
from app.rendering.layout.reference_layouts import classic_layout, executive_layout, modern_layout, sidebar_layout
from app.rendering.layout_html import render_layout_html
from app.rendering.theme.reference_themes import blue_theme


def _resume(**overrides) -> Resume:
    base = dict(
        user_id="u1",
        full_name="Sharma Rajasekar",
        email="sharma@test.com",
        professional_title="Senior Transformation & Infrastructure Leader",
        awards=[
            Award(name="Distinguished Engineering Award", issuer="Acme Corp", date="2023-06", description="For platform leadership"),
            Award(name="Best Platform Initiative", issuer="Industry Forum", date="2022-11"),
        ],
        languages=[
            Language(name="English", proficiency="Native"),
            Language(name="German", proficiency="Professional"),
        ],
    )
    base.update(overrides)
    return Resume(**base)


# ── Domain model ──────────────────────────────────────────────────────────────


class TestResumeModel:
    def test_new_fields_construct(self):
        resume = _resume()
        assert resume.professional_title == "Senior Transformation & Infrastructure Leader"
        assert len(resume.awards) == 2
        assert resume.awards[0].name == "Distinguished Engineering Award"
        assert resume.awards[0].issuer == "Acme Corp"
        assert resume.awards[0].date == "2023-06"
        assert resume.awards[0].description == "For platform leadership"
        assert resume.languages[0].name == "English"
        assert resume.languages[0].proficiency == "Native"

    def test_new_fields_default(self):
        resume = Resume(user_id="u1", full_name="A", email="a@test.com")
        assert resume.professional_title is None
        assert resume.awards == []
        assert resume.languages == []

    def test_award_requires_name(self):
        with pytest.raises(ValidationError):
            Award(name="")

    def test_invalid_awards_type_rejected(self):
        with pytest.raises(ValidationError):
            Resume(user_id="u1", full_name="A", email="a@test.com", awards="not-a-list")


# ── Parser-style payload (the parser schema IS Resume.model_json_schema) ──────


class TestParserPayload:
    def test_full_payload_populates_new_fields(self):
        resume = _resume()
        assert resume.professional_title == "Senior Transformation & Infrastructure Leader"
        assert [a.name for a in resume.awards] == ["Distinguished Engineering Award", "Best Platform Initiative"]
        assert [lang.proficiency for lang in resume.languages] == ["Native", "Professional"]

    def test_legacy_payload_without_new_fields(self):
        resume = Resume(user_id="u1", full_name="A", email="a@test.com", summary="S")
        assert resume.professional_title is None
        assert resume.awards == []
        assert resume.languages == []

    def test_empty_arrays_allowed(self):
        resume = Resume(user_id="u1", full_name="A", email="a@test.com", awards=[], languages=[])
        assert resume.awards == [] and resume.languages == []

    def test_language_without_proficiency(self):
        resume = _resume(languages=[Language(name="French")])
        assert resume.languages[0].proficiency is None


# ── JSON round trip (model_dump_json → Resume(**data)) ────────────────────────


class TestJsonRoundTrip:
    def test_new_fields_survive_serialization(self):
        resume = _resume()
        data = resume.model_dump_json()
        restored = Resume.model_validate_json(data)
        assert restored == resume
        assert restored.professional_title == resume.professional_title
        assert [a.name for a in restored.awards] == [a.name for a in resume.awards]
        assert [lang.name for lang in restored.languages] == [lang.name for lang in resume.languages]

    def test_old_record_without_new_fields_loads(self):
        # Simulate a JSON record written before the fields existed.
        old = {"user_id": "u1", "full_name": "Old User", "email": "old@test.com", "summary": "S"}
        resume = Resume(**old)
        assert resume.professional_title is None
        assert resume.awards == [] and resume.languages == []


# ── CVM mapping ───────────────────────────────────────────────────────────────


class TestCVMMapping:
    def test_professional_title_maps_to_profile(self):
        cvm = cvm_from_resume(_resume(), stable_id="r1")
        assert cvm.profile.professional_title == "Senior Transformation & Infrastructure Leader"

    def test_awards_map(self):
        cvm = cvm_from_resume(_resume())
        assert len(cvm.awards) == 2
        assert cvm.awards[0].title == "Distinguished Engineering Award"
        assert cvm.awards[0].issuer == "Acme Corp"
        assert cvm.awards[0].date == "2023-06"

    def test_languages_map(self):
        cvm = cvm_from_resume(_resume())
        assert len(cvm.languages) == 2
        assert cvm.languages[0].name == "English"
        assert cvm.languages[0].proficiency == "Native"
        assert cvm.languages[1].name == "German"

    def test_existing_fields_unchanged(self):
        cvm = cvm_from_resume(_resume())
        assert cvm.profile.full_name == "Sharma Rajasekar"
        assert cvm.profile.email == "sharma@test.com"
        assert cvm.summary is None


# ── End-to-end preview ────────────────────────────────────────────────────────


def _html_for(cvm, layout):
    return render_layout_html(cvm, layout, blue_theme())


class TestEndToEndPreview:
    def test_html_contains_new_field_values(self):
        cvm = cvm_from_resume(_resume(), stable_id="r1")
        for layout in (executive_layout(), sidebar_layout(), modern_layout(), classic_layout()):
            html = _html_for(cvm, layout)
            assert "Senior Transformation" in html and "Infrastructure Leader" in html  # professional title
            assert "Distinguished Engineering Award" in html                              # award name
            assert "Acme Corp" in html                                                    # award issuer
            assert "English — Native" in html                                             # language + proficiency
            assert "German — Professional" in html
            assert "Best Platform Initiative" in html

    def test_same_cvm_renders_all_layouts_without_modification(self):
        cvm = cvm_from_resume(_resume(), stable_id="r1")
        import re

        def body(html):
            stripped = re.sub(r"<style.*?</style>", "", html, flags=re.S)
            return " ".join(re.sub(r"<[^>]+>", " ", stripped).split())

        bodies = [body(_html_for(cvm, layout)) for layout in (executive_layout(), sidebar_layout(), modern_layout(), classic_layout())]
        from collections import Counter

        counters = [Counter(b.split()) for b in bodies]
        assert counters[0] == counters[1] == counters[2] == counters[3]
        assert "Senior Transformation" in bodies[0]
        # The CVM is not mutated by rendering.
        assert len(cvm.awards) == 2 and len(cvm.languages) == 2

    def test_backward_compat_resume_renders(self):
        legacy = Resume(user_id="u1", full_name="Old User", email="old@test.com", summary="S")
        cvm = cvm_from_resume(legacy, stable_id="legacy")
        html = _html_for(cvm, classic_layout())
        assert "Old User" in html
        assert "Distinguished Engineering Award" not in html  # genuinely absent
        assert "English — Native" not in html
