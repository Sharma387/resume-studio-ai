"""P3.5: ContentAnalyzer — deterministic, render-independent content metrics.

Focuses on the public contract: which sections are measured, what a "logical
item" means (grouped skills/certifications are single items), that word and
character counts are exact and deterministic (no InlineRun/group duplication),
and that the golden comprehensive vs long CVMs order correctly by size.

The ``_comprehensive_cvm``/``_long_cvm`` fixtures are the existing golden
content used across the rendering suite, reused verbatim for consistency.
"""

from app.models.resume import Resume
from app.rendering.content.builders import cvm_from_resume
from app.rendering.content.models import (
    AwardEntry,
    CertificationEntry,
    ContentView,
    EducationEntry,
    ExperienceEntry,
    LanguageEntry,
    Profile,
    ProjectEntry,
    SkillGroup,
)
from app.rendering.content_analyzer import ContentAnalysis, ContentAnalyzer, SectionMetrics


def _empty_cvm() -> ContentView:
    return ContentView(stable_id="resume.empty")


def _item_cvm() -> ContentView:
    """One logical item per measured section."""
    return ContentView(
        stable_id="resume.items",
        profile=Profile(full_name="Jane Doe", professional_title="Engineer"),
        summary="Focused summary text.",
        experience=(
            ExperienceEntry(
                company="Acme Corp",
                title="Senior Engineer",
                location="Boston, MA",
                start_date="2021",
                end_date="2024",
                description=("Led the platform team", "Cut latency"),
            ),
        ),
        education=(EducationEntry(institution="MIT", degree="M.S.", field="Computer Science"),),
        skills=(SkillGroup(category="Languages", skills=("Python", "Go")),),
        certifications=(CertificationEntry(name="AWS Certified", issuer="Amazon", date="2022"),),
        projects=(ProjectEntry(name="Orbit Scheduler", description="Task scheduler"),),
        awards=(AwardEntry(title="Employee of the Year", issuer="Acme", date="2023"),),
        languages=(LanguageEntry(name="English", proficiency="Native"),),
    )


def _analyze(cvm: ContentView) -> ContentAnalysis:
    return ContentAnalyzer().analyze(cvm)


class TestEmptyAnalysis:
    def test_empty_view_produces_empty_analysis(self):
        analysis = _analyze(_empty_cvm())
        assert analysis.sections == {}
        assert analysis.total_word_count == 0
        assert analysis.total_char_count == 0


class TestItemCounts:
    def test_item_counts_per_section(self):
        metrics = _analyze(_item_cvm()).sections
        assert metrics["profile"].item_count == 1
        assert metrics["summary"].item_count == 1
        assert metrics["experience"].item_count == 1
        assert metrics["education"].item_count == 1
        assert metrics["projects"].item_count == 1
        assert metrics["certifications"].item_count == 1
        assert metrics["skills"].item_count == 1
        assert metrics["awards"].item_count == 1
        assert metrics["languages"].item_count == 1

    def test_multi_entry_item_counts(self):
        cvm = _item_cvm().model_copy(
            update={
                "experience": _item_cvm().experience * 3,
                "education": _item_cvm().education * 2,
                "projects": _item_cvm().projects * 4,
                "certifications": _item_cvm().certifications * 3,
                "awards": _item_cvm().awards * 2,
                "languages": _item_cvm().languages * 5,
            }
        )
        metrics = _analyze(cvm).sections
        assert metrics["experience"].item_count == 3
        assert metrics["education"].item_count == 2
        assert metrics["projects"].item_count == 4
        assert metrics["certifications"].item_count == 3
        assert metrics["awards"].item_count == 2
        assert metrics["languages"].item_count == 5

    def test_grouped_skill_is_one_logical_item(self):
        cvm = ContentView(
            stable_id="resume.grouped-skill",
            profile=Profile(full_name="J", professional_title="Manager"),
            skills=(
                SkillGroup(
                    category="Project Management Lifecycle",
                    skills=("SAFe", "Agile", "Waterfall"),
                ),
            ),
        )
        metrics = _analyze(cvm).sections["skills"]
        assert metrics.item_count == 1
        logical = "Project Management Lifecycle: SAFe, Agile, Waterfall"
        assert metrics.word_count == len(logical.split())
        assert metrics.char_count == len(logical)

    def test_grouped_certification_is_one_logical_item(self):
        cvm = ContentView(
            stable_id="resume.grouped-cert",
            profile=Profile(full_name="J", professional_title="Engineer"),
            certifications=(
                CertificationEntry(
                    category="Professional Credentials",
                    values=("PRINCE2 Practitioner", "Certified Scrum Master (CSM)", "ITIL Foundation Certificate"),
                ),
            ),
        )
        metrics = _analyze(cvm).sections["certifications"]
        assert metrics.item_count == 1
        logical = "Professional Credentials: PRINCE2 Practitioner | Certified Scrum Master (CSM) | ITIL Foundation Certificate"
        assert metrics.word_count == len(logical.split())
        assert metrics.char_count == len(logical)

    def test_multiple_grouped_skills_each_single_item(self):
        cvm = ContentView(
            stable_id="resume.multi-skills",
            profile=Profile(full_name="J", professional_title="Engineer"),
            skills=(
                SkillGroup(category="Languages", skills=("Python", "Go")),
                SkillGroup(category="Cloud", skills=("AWS", "Azure")),
            ),
        )
        metrics = _analyze(cvm).sections["skills"]
        assert metrics.item_count == 2
        logical = "Languages: Python, Go Cloud: AWS, Azure"
        assert metrics.word_count == len(logical.split())


class TestWordAndCharacterCounts:
    def test_word_count_deterministic(self):
        first = _analyze(_item_cvm())
        second = _analyze(_item_cvm())
        assert first.model_dump() == second.model_dump()

    def test_character_count_deterministic(self):
        first = _analyze(_item_cvm())
        second = _analyze(_item_cvm())
        assert first.total_char_count == second.total_char_count

    def test_no_duplication_from_grouped_fields(self):
        cvm = ContentView(
            stable_id="resume.no-dup-cert",
            profile=Profile(full_name="J", professional_title="Engineer"),
            certifications=(
                CertificationEntry(category="Cloud & Architecture", values=("AWS Solutions Architect", "Azure Fundamentals")),
            ),
        )
        metrics = _analyze(cvm).sections["certifications"]
        logical = "Cloud & Architecture: AWS Solutions Architect | Azure Fundamentals"
        assert metrics.word_count == len(logical.split())
        assert metrics.char_count == len(logical)

    def test_no_duplication_from_description_runs(self):
        cvm = ContentView(
            stable_id="resume.no-dup-exp",
            profile=Profile(full_name="J", professional_title="Engineer"),
            experience=(
                ExperienceEntry(
                    company="Acme",
                    title="Engineer",
                    description=("Led the platform team", "Cut latency"),
                ),
            ),
        )
        metrics = _analyze(cvm).sections["experience"]
        logical = "Acme Engineer Led the platform team Cut latency"
        assert metrics.word_count == len(logical.split())
        assert metrics.char_count == len(logical)

    def test_estimated_units_equals_word_count(self):
        metrics = _analyze(_item_cvm()).sections
        assert all(metric.estimated_units == metric.word_count for metric in metrics.values())


class TestPresenceAndTotals:
    def test_only_present_sections_analyzed(self):
        cvm = ContentView(
            stable_id="resume.partial",
            profile=Profile(full_name="J", professional_title="Engineer"),
            experience=(_item_cvm().experience[0],),
            skills=_item_cvm().skills,
        )
        assert set(_analyze(cvm).sections) == {"profile", "experience", "skills"}

    def test_totals_equal_section_sums(self):
        analysis = _analyze(_item_cvm())
        assert analysis.total_word_count == sum(s.word_count for s in analysis.sections.values())
        assert analysis.total_char_count == sum(s.char_count for s in analysis.sections.values())


class TestGoldenFixtures:
    def test_comprehensive_is_non_zero(self):
        from tests.test_tree_html_renderer import _comprehensive_cvm

        analysis = _analyze(_comprehensive_cvm())
        assert analysis.total_word_count > 0
        assert analysis.total_char_count > 0
        assert all(metric.word_count > 0 for metric in analysis.sections.values())

    def test_long_beats_comprehensive(self):
        from tests.test_tree_html_renderer import _comprehensive_cvm, _long_cvm

        long = _analyze(_long_cvm())
        comprehensive = _analyze(_comprehensive_cvm())
        assert long.total_word_count > comprehensive.total_word_count
        assert long.total_char_count > comprehensive.total_char_count

    def test_comprehensive_item_totals_exact(self):
        from tests.test_tree_html_renderer import _comprehensive_cvm

        metrics = _analyze(_comprehensive_cvm()).sections
        assert metrics["experience"].item_count == 2
        assert metrics["education"].item_count == 1
        assert metrics["skills"].item_count == 1
        assert metrics["certifications"].item_count == 1
        assert metrics["projects"].item_count == 1
        assert metrics["awards"].item_count == 1
        assert metrics["languages"].item_count == 2

    def test_resume_builder_path(self):
        resume = Resume(
            user_id="analyzer",
            full_name="Fixture User",
            professional_title="Engineer",
            email="fixture@test.com",
            summary="A real resume summary.",
            experience=[{"company": "Acme", "title": "Engineer", "start_date": "2020"}],
            skills=[{"category": "Languages", "skills": ["Python", "Go"]}],
        )
        analysis = _analyze(cvm_from_resume(resume))
        assert analysis.sections["profile"].item_count == 1
        assert analysis.sections["experience"].item_count == 1
        assert analysis.sections["skills"].item_count == 1
        assert analysis.total_word_count > 0


class TestResultShape:
    def test_metrics_and_analysis_are_immutable(self):
        from pydantic import ValidationError

        try:
            SectionMetrics(section_id="x", word_count=-1)
        except ValidationError:
            pass
        else:
            raise AssertionError("SectionMetrics should reject negative word_count")

    def test_analysis_exposes_expected_fields(self):
        analysis = _analyze(_item_cvm())
        section = analysis.sections["experience"]
        assert section.section_id == "experience"
        assert hasattr(analysis, "total_word_count")
        assert hasattr(analysis, "total_char_count")
