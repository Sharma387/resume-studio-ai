"""Live ATS scoring and resume quality analysis."""

from app.models.resume import Resume


def analyze(resume: Resume) -> dict:
    """Analyse a resume and return ATS score with improvement suggestions."""
    score = 50
    suggestions: list[str] = []
    details: dict = {}

    # Contact info
    if resume.email:
        score += 5
    if resume.phone:
        score += 5
    if resume.linkedin:
        score += 5

    # Summary
    if resume.summary:
        score += 5
        if len(resume.summary) > 100:
            score += 3
        if len(resume.summary) < 50:
            suggestions.append("Professional summary is too short. Expand to 2-3 sentences.")
    else:
        suggestions.append("Add a professional summary to improve keyword density.")

    # Experience
    details["experience_count"] = len(resume.experience)
    if len(resume.experience) >= 2:
        score += 8
    elif len(resume.experience) == 1:
        score += 3
    else:
        suggestions.append("Add work experience to improve credibility.")

    has_numbers = False
    total_bullets = 0
    for exp in resume.experience:
        total_bullets += len(exp.description)
        for desc in exp.description:
            if any(c.isdigit() for c in desc):
                has_numbers = True
                break

    if has_numbers:
        score += 8
    else:
        suggestions.append("Add quantifiable achievements (numbers, percentages) to experience.")

    if total_bullets >= 6:
        score += 5
    elif total_bullets < 3 and resume.experience:
        suggestions.append("Each role should have 3-5 bullet points describing achievements.")

    # Skills
    details["skill_categories"] = len(resume.skills)
    total_skills = sum(len(s.skills) for s in resume.skills)
    if total_skills >= 10:
        score += 8
    elif total_skills >= 5:
        score += 4
    else:
        suggestions.append("List at least 10 relevant skills for better ATS matching.")

    # Education
    if resume.education:
        score += 5
        for edu in resume.education:
            if edu.gpa and edu.gpa >= 3.5:
                score += 3
                break

    # Projects
    if resume.projects:
        score += 5

    # Certifications
    if resume.certifications:
        score += 3

    # Length check
    total_chars = len(str(resume.model_dump()))
    details["estimated_pages"] = max(1, round(total_chars / 3000))
    if details["estimated_pages"] > 2:
        suggestions.append("Resume is longer than 2 pages. Consider condensing.")
    elif details["estimated_pages"] < 1:
        suggestions.append("Resume seems sparse. Add more content.")

    # Overall score
    score = min(100, score)
    quality = "excellent" if score >= 85 else "good" if score >= 70 else "fair" if score >= 55 else "needs_work"

    return {
        "overall_score": score,
        "quality": quality,
        "suggestions": suggestions[:5],
        "details": details,
        "breakdown": {
            "contact": min(15, score),
            "summary": min(8, max(0, score - 50)) if resume.summary else 0,
            "experience": min(26, score - 50 - (8 if resume.summary else 0)),
            "skills": min(8, (total_skills >= 10) * 8),
            "education": min(8, score),
        },
    }
