import pytest
from pydantic import ValidationError

from app.models.match import (
    SkillMatch,
    Recommendation,
    MatchResult,
    JobDescription,
)


class TestSkillMatch:
    def test_valid(self):
        s = SkillMatch(skill="Python", required=True, matched=True)
        assert s.skill == "Python"
        assert s.required is True
        assert s.matched is True

    def test_empty_skill(self):
        with pytest.raises(ValidationError):
            SkillMatch(skill="", required=True, matched=False)

    def test_defaults(self):
        s = SkillMatch(skill="Docker")
        assert s.required is True
        assert s.matched is False


class TestRecommendation:
    def test_valid(self):
        r = Recommendation(
            section="Skills",
            priority="high",
            message="Add Kubernetes to your skills.",
        )
        assert r.section == "Skills"
        assert r.priority == "high"

    def test_invalid_priority(self):
        with pytest.raises(ValidationError):
            Recommendation(
                section="Skills",
                priority="urgent",
                message="Test message here for validation.",
            )

    def test_short_message(self):
        with pytest.raises(ValidationError):
            Recommendation(
                section="Skills",
                priority="medium",
                message="Short",
            )

    def test_empty_section(self):
        with pytest.raises(ValidationError):
            Recommendation(
                section="",
                priority="medium",
                message="This is a sufficiently long message.",
            )


class TestJobDescription:
    def test_valid(self):
        j = JobDescription(
            resume_id="abc123",
            description="We are looking for a senior engineer with 5+ years of Python experience.",
        )
        assert j.resume_id == "abc123"
        assert j.job_title is None

    def test_missing_resume_id(self):
        with pytest.raises(ValidationError):
            JobDescription(description="A job description here.")

    def test_short_description(self):
        with pytest.raises(ValidationError):
            JobDescription(resume_id="abc", description="Too short")

    def test_with_job_title(self):
        j = JobDescription(
            resume_id="abc",
            job_title="Senior Engineer",
            description="A sufficiently long job description text for validation.",
        )
        assert j.job_title == "Senior Engineer"


class TestMatchResult:
    def test_valid(self):
        m = MatchResult(user_id="test", 
            id="match1",
            resume_id="resume1",
            overall_score=85.0,
        )
        assert m.overall_score == 85.0
        assert m.matched_skills == []

    def test_score_below_zero(self):
        with pytest.raises(ValidationError):
            MatchResult(user_id="test", id="m1", resume_id="r1", overall_score=-5.0)

    def test_score_above_hundred(self):
        with pytest.raises(ValidationError):
            MatchResult(user_id="test", id="m1", resume_id="r1", overall_score=150.0)

    def test_score_boundary(self):
        m = MatchResult(user_id="test", id="m1", resume_id="r1", overall_score=100.0)
        assert m.overall_score == 100.0

    def test_with_nested_models(self):
        m = MatchResult(user_id="test", 
            id="m1",
            resume_id="r1",
            overall_score=72.0,
            skill_matches=[SkillMatch(skill="Python", matched=True)],
            matched_skills=["Python"],
            missing_skills=["Go"],
            recommendations=[
                Recommendation(
                    section="Skills",
                    priority="high",
                    message="Add Go to your skill set for better alignment.",
                )
            ],
        )
        assert len(m.skill_matches) == 1
        assert len(m.recommendations) == 1
        assert m.matched_skills == ["Python"]
        assert m.missing_skills == ["Go"]
