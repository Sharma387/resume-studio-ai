"""Tests for Designer services: version history, ATS scoring, recommendations."""

from app.models.resume import Resume
from app.services.ats_scoring import analyze as analyze_ats
from app.services.recommendation_service import recommend
from app.services.version_history import autosave, get_autosave, list_versions, save_version


def _make_resume(**overrides) -> Resume:
    data = dict(
        user_id="test",
        full_name="Test User",
        email="test@test.com",
        summary="Experienced software engineer with 5+ years.",
        phone="+1 555-0000",
        location="NYC",
        linkedin="https://linkedin.com/in/test",
        experience=[
            {
                "company": "Acme",
                "title": "Engineer",
                "start_date": "2020-01",
                "end_date": "2023-12",
                "current": False,
                "description": ["Built microservices", "Reduced latency by 40%"],
            }
        ],
        education=[{"institution": "MIT", "degree": "BS", "field": "CS", "gpa": 3.8, "achievements": []}],
        skills=[{"category": "Languages", "skills": ["Python", "Go"]}, {"category": "Frontend", "skills": ["React"]}],
        projects=[{"name": "Project X", "description": "A project", "technologies": ["Go"]}],
        certifications=[{"name": "AWS Certified"}],
    )
    data.update(overrides)
    return Resume(**data)


class TestVersionHistory:
    def test_save_and_list_versions(self):
        v = save_version("variant-1", {"name": "test"}, "Initial")
        assert v["label"] == "Initial"
        versions = list_versions("variant-1")
        assert len(versions) == 1
        assert versions[0]["label"] == "Initial"

    def test_autosave_and_retrieve(self):
        autosave("variant-2", {"name": "autosaved"})
        data = get_autosave("variant-2")
        assert data is not None
        assert data["resume_data"]["name"] == "autosaved"


class TestATSScoring:
    def test_analyze_returns_score(self):
        resume = _make_resume()
        result = analyze_ats(resume)
        assert "overall_score" in result
        assert "suggestions" in result
        assert 0 <= result["overall_score"] <= 100

    def test_minimal_resume_scores_lower(self):
        resume = _make_resume(summary="", experience=[], education=[], skills=[], projects=[], certifications=[])
        result = analyze_ats(resume)
        assert result["overall_score"] < 70

    def test_full_resume_scores_higher(self):
        resume = _make_resume()
        result = analyze_ats(resume)
        assert result["overall_score"] >= 70


class TestRecommendationService:
    def test_recommend_returns_scored_list(self):
        resume = _make_resume()
        results = recommend(resume)
        assert len(results) > 0
        for r in results:
            assert "layout_id" in r
            assert "score" in r
            assert 0 <= r["score"] <= 100
        # Results should be sorted by score descending
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)
