"""Layout recommendation based on resume characteristics.

Recommendations operate on canonical layouts (``LayoutRegistry`` via the
reference layouts) and never initialize a legacy rendering stack.

Each recommendation exposes the canonical ``layout_id``. The legacy
``template_id`` compatibility field was removed together with the legacy
retirement.

This module must not import TemplateRegistry / Jinja / PreviewService /
ResumeRenderingService / ReportLab (verified by import-graph tests).
"""

from __future__ import annotations

from app.models.resume import Resume
from app.rendering.layout_preview import default_layout_registry

#: coarse category label per canonical layout (kept for response stability).
_LAYOUT_CATEGORY: dict[str, str] = {
    "executive": "executive",
    "modern": "modern",
    "sidebar": "professional",
    "timeline": "professional",
    "classic": "ats",
    "minimal": "professional",
}


def recommend(resume: Resume) -> list[dict]:
    """Recommend canonical layouts based on resume characteristics."""
    registry = default_layout_registry()
    layouts = registry.definitions()
    total_exp_years = _estimate_experience_years(resume)
    industry = _detect_industry(resume)
    is_executive = total_exp_years >= 10 or _has_executive_title(resume)
    is_technical = industry in ("technology", "engineering")
    ats_score = _estimate_ats_readability(resume)

    scored = []
    for layout in layouts:
        m = layout.metadata
        score = 50

        if is_executive and m.layout_id in ("executive", "sidebar"):
            score += 30
        if is_executive and m.layout_id in ("executive", "sidebar"):
            score += 10

        if is_technical and m.ats_score >= 90:
            score += 25

        if m.ats_score >= ats_score - 10:
            score += 10

        if is_technical and m.layout_id in ("classic", "minimal"):
            score += 15

        if not is_executive and m.layout_id in ("modern", "classic", "minimal"):
            score += 15

        if resume.summary and len(resume.summary) > 100 and m.layout_id == "executive":
            score += 5

        scored.append({
            "layout_id": m.layout_id,
            "name": m.display_name,
            "score": min(100, score),
            "category": _LAYOUT_CATEGORY.get(m.layout_id, "professional"),
            "ats_score": m.ats_score,
            "best_for": _best_for(m.layout_id, is_executive, is_technical),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def _estimate_experience_years(resume: Resume) -> int:
    years = 0
    for exp in resume.experience:
        if exp.start_date and exp.end_date:
            try:
                start = int(exp.start_date[:4])
                end = int(exp.end_date[:4])
                years += end - start
            except (ValueError, IndexError):
                years += 2
        elif exp.start_date and exp.current:
            try:
                years += max(0, 2026 - int(exp.start_date[:4]))
            except (ValueError, IndexError):
                years += 2
    return years


def _has_executive_title(resume: Resume) -> bool:
    executive_titles = {"ceo", "cfo", "cto", "coo", "chief", "vp", "vice president",
                        "director", "head of", "senior director", "managing director"}
    for exp in resume.experience:
        title_lower = exp.title.lower()
        for et in executive_titles:
            if et in title_lower:
                return True
    return False


def _detect_industry(resume: Resume) -> str:
    tech_keywords = {"software", "engineer", "developer", "data", "devops", "python",
                     "javascript", "react", "aws", "cloud", "it ", "system", "full stack"}
    for exp in resume.experience:
        combined = (exp.title + " " + exp.company + " " + " ".join(exp.description)).lower()
        for kw in tech_keywords:
            if kw in combined:
                return "technology"
    return "general"


def _estimate_ats_readability(resume: Resume) -> int:
    score = 70
    if resume.summary:
        score += 5
    if len(resume.experience) >= 2:
        score += 5
    if resume.skills:
        score += 5
    if resume.education:
        score += 5
    for exp in resume.experience:
        if exp.description:
            has_numbers = any(any(c.isdigit() for c in d) for d in exp.description)
            if has_numbers:
                score += 5
                break
    return min(100, score)


def _best_for(layout_id: str, is_executive: bool, is_technical: bool) -> str:
    if is_executive and layout_id in ("executive", "sidebar"):
        return "Executive & Leadership"
    if is_technical and layout_id in ("classic", "minimal"):
        return "ATS-Optimised"
    if layout_id == "modern":
        return "Modern & Creative"
    return "General Purpose"
