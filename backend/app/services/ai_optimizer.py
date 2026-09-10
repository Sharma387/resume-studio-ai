"""AI Resume Optimizer — grammar, ATS, keyword, and formatting analysis."""

from app.models.resume import Resume
from app.services.ats_scoring import analyze as ats_analyze


def optimize(resume: Resume) -> dict:
    """Run all optimisation analyses and return recommendations."""
    ats = ats_analyze(resume)
    return {
        "overall_score": ats["overall_score"],
        "quality": ats["quality"],
        "ats": ats,
        "suggestions": _generate_suggestions(resume, ats),
    }


def target_for_job(resume: Resume, job_description: str) -> dict:
    """Analyse a resume against a job description and suggest improvements."""
    jd_lower = job_description.lower()
    keywords = _extract_keywords(jd_lower)
    resume_text = str(resume.model_dump(mode="json")).lower()

    missing_keywords = [kw for kw in keywords if kw not in resume_text]
    matched_keywords = [kw for kw in keywords if kw in resume_text]

    return {
        "matched_keywords": matched_keywords[:20],
        "missing_keywords": missing_keywords[:20],
        "match_rate": round(len(matched_keywords) / max(len(keywords), 1) * 100, 1),
        "total_keywords": len(keywords),
    }


def _generate_suggestions(resume: Resume, ats: dict) -> list[dict]:
    suggestions = []
    for s in ats.get("suggestions", []):
        suggestions.append({"type": "improvement", "message": s})
    if resume.summary and len(resume.summary) > 150:
        suggestions.append({"type": "warning", "message": "Summary is verbose. Consider condensing to 2-3 sentences."})
    if resume.experience:
        for exp in resume.experience:
            for desc in exp.description:
                words = desc.split()
                if len(words) > 30:
                    suggestions.append(
                        {
                            "type": "style",
                            "message": f"A bullet point in '{exp.title}' is too long ({len(words)} words). Break into shorter statements.",
                        }
                    )
                    break
    return suggestions[:8]


def _extract_keywords(text: str) -> list[str]:
    common_skill_keywords = [
        "python",
        "javascript",
        "typescript",
        "react",
        "node.js",
        "aws",
        "docker",
        "kubernetes",
        "sql",
        "postgresql",
        "machine learning",
        "data science",
        "project management",
        "agile",
        "scrum",
        "leadership",
        "strategy",
        "communication",
        "team management",
        "stakeholder",
        "budget",
        "analytics",
        "marketing",
        "sales",
        "operations",
        "finance",
        "compliance",
        "risk management",
        "product management",
        "qa",
        "devops",
        "ci/cd",
        "terraform",
        "gcp",
        "azure",
        "api",
        "rest",
        "graphql",
        "mongodb",
        "redis",
        "kafka",
        "microservices",
    ]
    found = set()
    for kw in common_skill_keywords:
        if kw in text:
            found.add(kw)
    return sorted(found)
