"""Builders converting source resume data into the Content View Model.

The CVM models themselves stay pure (no coupling to the source schema); this
adapter is the "Resume/Candidate Data → CVM" seam. It preserves source content
faithfully while producing a layout-independent view.
"""

from __future__ import annotations

from app.models.resume import Resume
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


def _url(value: object | None) -> str | None:
    return str(value) if value is not None else None


def cvm_from_resume(resume: Resume, *, stable_id: str | None = None) -> ContentView:
    """Build a :class:`ContentView` from a parsed :class:`Resume`.

    ``stable_id`` defaults to the resume id when present, else ``resume.unknown``;
    callers should pass the canonical content id (e.g. the stored resume id).
    """
    sid = stable_id or getattr(resume, "id", None) or "unknown"

    profile = Profile(
        full_name=resume.full_name,
        professional_title=resume.professional_title,
        email=resume.email,
        phone=resume.phone,
        location=resume.location,
        linkedin=_url(resume.linkedin),
        github=_url(resume.github),
        website=_url(resume.website),
    )

    experience = tuple(
        ExperienceEntry(
            company=entry.company,
            title=entry.title,
            location=entry.location,
            start_date=entry.start_date,
            end_date=entry.end_date,
            current=entry.current,
            description=tuple(entry.description),
        )
        for entry in resume.experience
    )

    education = tuple(
        EducationEntry(
            institution=entry.institution,
            degree=entry.degree,
            field=entry.field,
            start_date=entry.start_date,
            end_date=entry.end_date,
            gpa=entry.gpa,
            achievements=tuple(entry.achievements),
        )
        for entry in resume.education
    )

    skills = tuple(
        SkillGroup(category=group.category, skills=tuple(group.skills))
        for group in resume.skills
    )

    certifications = tuple(
        CertificationEntry(
            name=cert.name,
            issuer=cert.issuer,
            date=cert.date,
            url=_url(cert.url),
            category=cert.category,
            values=tuple(cert.values),
        )
        for cert in resume.certifications
    )

    projects = tuple(
        ProjectEntry(
            name=project.name,
            description=project.description,
            url=_url(project.url),
            technologies=tuple(project.technologies),
        )
        for project in resume.projects
    )

    awards = tuple(
        AwardEntry(
            title=award.name,
            issuer=award.issuer,
            date=award.date,
        )
        for award in resume.awards
    )

    languages = tuple(
        LanguageEntry(name=language.name, proficiency=language.proficiency)
        for language in resume.languages
    )

    return ContentView(
        stable_id=f"resume.{sid}",
        profile=profile,
        summary=resume.summary,
        experience=experience,
        education=education,
        skills=skills,
        certifications=certifications,
        projects=projects,
        awards=awards,
        languages=languages,
    )
