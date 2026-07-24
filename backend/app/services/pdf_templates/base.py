from abc import ABC, abstractmethod
from typing import Any

from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.colors import HexColor
from reportlab.platypus import Paragraph, Spacer

from app.models.resume import Resume


class BaseTemplate(ABC):
    """Abstract base for all resume PDF templates."""

    # ── Override in subclasses ──────────────────────────────────
    name: str = "base"
    accent_color: str = "#0099cc"
    dark_color: str = "#1a1a2e"
    gray_color: str = "#555555"
    light_color: str = "#aaaaaa"
    font_name: str = "Helvetica"
    font_bold: str = "Helvetica-Bold"
    section_divider: str = "──  {title}"
    show_section_lines: bool = True

    # ── Public API ──────────────────────────────────────────────

    def build_document(self, resume: Resume) -> list[Any]:
        """Return a list of ReportLab flowables for the resume."""
        styles = self._build_styles()
        content: list[Any] = []

        self._build_header(content, resume, styles)
        content.append(Spacer(1, 16))

        if resume.summary:
            self._add_section_header(content, "Professional Summary", styles)
            content.append(Paragraph(resume.summary, styles["Summary"]))

        if resume.experience:
            self._add_section_header(content, "Experience", styles)
            for exp in resume.experience:
                self._build_experience(content, exp, styles)

        if resume.education:
            self._add_section_header(content, "Education", styles)
            for edu in resume.education:
                self._build_education(content, edu, styles)

        if resume.skills:
            self._add_section_header(content, "Skills", styles)
            self._build_skills(content, resume.skills, styles)

        if resume.projects:
            self._add_section_header(content, "Projects", styles)
            for proj in resume.projects:
                self._build_project(content, proj, styles)

        if resume.certifications:
            self._add_section_header(content, "Certifications", styles)
            for cert in resume.certifications:
                self._build_certification(content, cert, styles)

        return content

    # ── Style building ──────────────────────────────────────────

    def _build_styles(self) -> dict:
        accent = HexColor(self.accent_color)
        dark = HexColor(self.dark_color)
        gray = HexColor(self.gray_color)

        styles = getSampleStyleSheet()
        pf = self.font_name
        pb = self.font_bold

        styles.add(ParagraphStyle("Name", fontSize=24, fontName=pb, textColor=dark, spaceAfter=12, alignment=TA_CENTER, leading=30))
        styles.add(ParagraphStyle("ContactRow", fontSize=9, fontName=pf, textColor=gray, spaceAfter=3, alignment=TA_CENTER, leading=16))
        styles.add(ParagraphStyle("LinkRow", fontSize=8, fontName=pf, textColor=accent, spaceAfter=2, alignment=TA_CENTER, leading=14))
        styles.add(ParagraphStyle("SectionTitle", fontSize=13, fontName=pb, textColor=accent, spaceBefore=18, spaceAfter=6))
        styles.add(ParagraphStyle("ItemTitle", fontSize=10.5, fontName=pb, textColor=dark, spaceAfter=1, spaceBefore=8))
        styles.add(ParagraphStyle("ItemSubtitle", fontSize=9, fontName=pf, textColor=gray, spaceAfter=3, leading=14))
        styles.add(ParagraphStyle("BulletItem", fontSize=9, fontName=pf, textColor=dark, spaceAfter=2, leading=15, leftIndent=14))
        styles.add(ParagraphStyle("Summary", fontSize=9.5, fontName=pf, textColor=dark, spaceAfter=4, leading=16))
        styles.add(ParagraphStyle("SkillItem", fontSize=9, fontName=pf, textColor=dark, spaceAfter=2, leading=15))

        self._customize_styles(styles)
        return styles

    def _customize_styles(self, styles: dict) -> None:
        """Override in subclasses to tweak paragraph styles."""

    # ── Section helpers ─────────────────────────────────────────

    def _add_section_header(self, content: list, title: str, styles: dict) -> None:
        if self.show_section_lines:
            content.append(Paragraph(
                f"<font color='{HexColor(self.accent_color).hexval()}'>"
                f"{self.section_divider.format(title=title)}</font>",
                styles["SectionTitle"],
            ))
        else:
            content.append(Paragraph(title, styles["SectionTitle"]))

    # ── Section renderers (override in subclasses) ──────────────

    def _build_header(self, content: list, resume: Resume, styles: dict) -> None:
        content.append(Paragraph(resume.full_name, styles["Name"]))
        contact = "  |  ".join(p for p in [resume.email, resume.phone, resume.location] if p)
        if contact:
            content.append(Paragraph(contact, styles["ContactRow"]))
        link_line = "  |  ".join(str(l) for l in [resume.linkedin, resume.github, resume.website] if l)
        if link_line:
            content.append(Paragraph(link_line, styles["LinkRow"]))

    def _build_experience(self, content: list, exp, styles: dict) -> None:
        dates = f"{exp.start_date or ''} – {'Present' if exp.current else exp.end_date or ''}"
        content.append(Paragraph(exp.title, styles["ItemTitle"]))
        content.append(Paragraph(f"{exp.company}{' · ' + exp.location if exp.location else ''}  ·  {dates}", styles["ItemSubtitle"]))
        for desc in exp.description:
            content.append(Paragraph(f"• {desc}", styles["BulletItem"]))

    def _build_education(self, content: list, edu, styles: dict) -> None:
        line = f"{edu.degree}{' in ' + edu.field if edu.field else ''}"
        dates = f"{edu.start_date or ''} – {edu.end_date or ''}"
        gpa = f"  ·  GPA: {edu.gpa}" if edu.gpa else ""
        content.append(Paragraph(line, styles["ItemTitle"]))
        content.append(Paragraph(f"{edu.institution}  ·  {dates}{gpa}", styles["ItemSubtitle"]))
        for a in edu.achievements:
            content.append(Paragraph(f"• {a}", styles["BulletItem"]))

    def _build_skills(self, content: list, skills, styles: dict) -> None:
        for cat in skills:
            skill_line = ", ".join(cat.skills)
            content.append(Paragraph(f"<b>{cat.category}:</b>  {skill_line}", styles["SkillItem"]))

    def _build_project(self, content: list, proj, styles: dict) -> None:
        line = proj.name
        if proj.technologies:
            line += f"  —  {', '.join(proj.technologies)}"
        content.append(Paragraph(line, styles["ItemTitle"]))
        if proj.url:
            content.append(Paragraph(str(proj.url), styles["ItemSubtitle"]))
        if proj.description:
            content.append(Paragraph(proj.description, styles["BulletItem"]))

    def _build_certification(self, content: list, cert, styles: dict) -> None:
        line = cert.name
        if cert.issuer:
            line += f" — {cert.issuer}"
        if cert.date:
            line += f" ({cert.date})"
        content.append(Paragraph(f"• {line}", styles["BulletItem"]))
