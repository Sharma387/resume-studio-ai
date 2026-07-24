import pytest
from pydantic import ValidationError

from app.models.resume import Resume, Education, Experience, Project, Skill, Certification


class TestEducation:
    def test_valid(self):
        e = Education(institution="MIT", degree="BS")
        assert e.institution == "MIT"
        assert e.degree == "BS"

    def test_missing_required(self):
        with pytest.raises(ValidationError):
            Education()

    def test_empty_institution(self):
        with pytest.raises(ValidationError):
            Education(institution="", degree="BS")

    def test_empty_degree(self):
        with pytest.raises(ValidationError):
            Education(institution="MIT", degree="")

    def test_gpa_range(self):
        with pytest.raises(ValidationError):
            Education(institution="MIT", degree="BS", gpa=4.5)

    def test_negative_gpa(self):
        with pytest.raises(ValidationError):
            Education(institution="MIT", degree="BS", gpa=-1.0)

    def test_valid_gpa(self):
        e = Education(institution="MIT", degree="BS", gpa=3.5)
        assert e.gpa == 3.5


class TestExperience:
    def test_valid(self):
        e = Experience(company="Google", title="Engineer")
        assert e.company == "Google"
        assert e.title == "Engineer"

    def test_missing_required(self):
        with pytest.raises(ValidationError):
            Experience()

    def test_default_current(self):
        e = Experience(company="Google", title="Engineer")
        assert e.current is False


class TestProject:
    def test_valid(self):
        p = Project(name="My App")
        assert p.name == "My App"

    def test_missing_name(self):
        with pytest.raises(ValidationError):
            Project()

    def test_empty_name(self):
        with pytest.raises(ValidationError):
            Project(name="")


class TestSkill:
    def test_valid(self):
        s = Skill(category="Frontend", skills=["React"])
        assert s.category == "Frontend"
        assert s.skills == ["React"]

    def test_missing_category(self):
        with pytest.raises(ValidationError):
            Skill()

    def test_empty_category(self):
        with pytest.raises(ValidationError):
            Skill(category="")


class TestCertification:
    def test_valid(self):
        c = Certification(name="AWS Certified")
        assert c.name == "AWS Certified"

    def test_missing_name(self):
        with pytest.raises(ValidationError):
            Certification()

    def test_empty_name(self):
        with pytest.raises(ValidationError):
            Certification(name="")


class TestResume:
    def test_valid_minimal(self):
        r = Resume(user_id="test", full_name="John Doe", email="john@example.com")
        assert r.full_name == "John Doe"
        assert r.email == "john@example.com"

    def test_missing_full_name(self):
        with pytest.raises(ValidationError):
            Resume(user_id="test", email="john@example.com")

    def test_empty_full_name(self):
        with pytest.raises(ValidationError):
            Resume(user_id="test", full_name="", email="john@example.com")

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            Resume(user_id="test", full_name="John Doe", email="not-an-email")

    def test_invalid_url(self):
        with pytest.raises(ValidationError):
            Resume(user_id="test", full_name="John Doe", email="john@example.com", website="not-a-url")

    def test_valid_full(self):
        r = Resume(
            user_id="test",
            full_name="Jane Smith",
            email="jane@example.com",
            phone="+1 555-0000",
            location="NYC",
            linkedin="https://linkedin.com/in/jane",
            github="https://github.com/jane",
            website="https://jane.dev",
            summary="A summary.",
            education=[Education(institution="MIT", degree="BS")],
            experience=[Experience(company="Acme", title="Dev")],
            projects=[Project(name="Project X")],
            skills=[Skill(category="Lang", skills=["Python"])],
            certifications=[Certification(name="Cert")],
        )
        assert r.full_name == "Jane Smith"
        assert len(r.education) == 1
        assert len(r.experience) == 1
        assert len(r.projects) == 1
        assert len(r.skills) == 1
        assert len(r.certifications) == 1
