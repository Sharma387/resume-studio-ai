from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from app.models.resume import Resume

PDF_DIR = Path("storage") / "pdfs"
PDF_DIR.mkdir(parents=True, exist_ok=True)

DARK = HexColor("#1a1a2e")
ACCENT = HexColor("#0099cc")
GRAY = HexColor("#555555")
LIGHT_GRAY = HexColor("#aaaaaa")


def _build_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        "Name", fontSize=24, fontName="Helvetica-Bold", textColor=DARK,
        spaceAfter=12, alignment=TA_CENTER, leading=30,
    ))
    styles.add(ParagraphStyle(
        "ContactRow", fontSize=9, fontName="Helvetica", textColor=GRAY,
        spaceAfter=3, alignment=TA_CENTER, leading=16,
    ))
    styles.add(ParagraphStyle(
        "LinkRow", fontSize=8, fontName="Helvetica", textColor=ACCENT,
        spaceAfter=2, alignment=TA_CENTER, leading=14,
    ))
    styles.add(ParagraphStyle(
        "SectionTitle", fontSize=13, fontName="Helvetica-Bold", textColor=ACCENT,
        spaceBefore=18, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        "ItemTitle", fontSize=10.5, fontName="Helvetica-Bold", textColor=DARK,
        spaceAfter=1, spaceBefore=8,
    ))
    styles.add(ParagraphStyle(
        "ItemSubtitle", fontSize=9, fontName="Helvetica", textColor=GRAY,
        spaceAfter=3, leading=14,
    ))
    styles.add(ParagraphStyle(
        "BulletItem", fontSize=9, fontName="Helvetica", textColor=DARK,
        spaceAfter=2, leading=15, leftIndent=14,
    ))
    styles.add(ParagraphStyle(
        "Summary", fontSize=9.5, fontName="Helvetica", textColor=DARK,
        spaceAfter=4, leading=16,
    ))
    styles.add(ParagraphStyle(
        "SkillItem", fontSize=9, fontName="Helvetica", textColor=DARK,
        spaceAfter=2, leading=15,
    ))
    return styles


S = _build_styles()


def _add_section(content, title: str):
    content.append(Paragraph(f"<font color='{ACCENT.hexval()}'>──  {title}</font>", S["SectionTitle"]))


def _add_experience(content, exp):
    dates = f"{exp.start_date or ''} – {'Present' if exp.current else exp.end_date or ''}"
    content.append(Paragraph(exp.title, S["ItemTitle"]))
    content.append(Paragraph(f"{exp.company}{' · ' + exp.location if exp.location else ''}  ·  {dates}", S["ItemSubtitle"]))
    for desc in exp.description:
        content.append(Paragraph(f"• {desc}", S["BulletItem"]))


def _add_education(content, edu):
    line = f"{edu.degree}{' in ' + edu.field if edu.field else ''}"
    dates = f"{edu.start_date or ''} – {edu.end_date or ''}"
    gpa = f"  ·  GPA: {edu.gpa}" if edu.gpa else ""
    content.append(Paragraph(line, S["ItemTitle"]))
    content.append(Paragraph(f"{edu.institution}  ·  {dates}{gpa}", S["ItemSubtitle"]))
    for a in edu.achievements:
        content.append(Paragraph(f"• {a}", S["BulletItem"]))


def _add_skills(content, skills):
    for cat in skills:
        skill_line = ", ".join(cat.skills)
        content.append(Paragraph(f"<b>{cat.category}:</b>  {skill_line}", S["SkillItem"]))


def _add_projects(content, projects):
    for proj in projects:
        line = proj.name
        if proj.technologies:
            line += f"  —  {', '.join(proj.technologies)}"
        content.append(Paragraph(line, S["ItemTitle"]))
        if proj.description:
            content.append(Paragraph(proj.description, S["BulletItem"]))


def _add_certifications(content, certs):
    for cert in certs:
        line = cert.name
        if cert.issuer:
            line += f" — {cert.issuer}"
        if cert.date:
            line += f" ({cert.date})"
        content.append(Paragraph(f"• {line}", S["BulletItem"]))


def _contact_line(resume: Resume) -> str:
    parts = [p for p in [resume.email, resume.phone, resume.location] if p]
    return "  |  ".join(parts) if parts else ""


def _link_line(resume: Resume) -> str:
    parts = [str(l) for l in [resume.linkedin, resume.github, resume.website] if l]
    return "  |  ".join(parts) if parts else ""


def _page_number_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(LIGHT_GRAY)
    canvas.drawCentredString(A4[0] / 2, 15 * mm, f"Page {doc.page}")
    canvas.restoreState()


def generate_pdf(resume_id: str, resume: Resume) -> Path:
    path = PDF_DIR / f"{resume_id}.pdf"
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=25 * mm,
        rightMargin=25 * mm,
        topMargin=20 * mm,
        bottomMargin=25 * mm,
    )

    content = []

    content.append(Paragraph(resume.full_name, S["Name"]))

    contact = _contact_line(resume)
    if contact:
        content.append(Paragraph(contact, S["ContactRow"]))

    link_line = _link_line(resume)
    if link_line:
        content.append(Paragraph(link_line, S["LinkRow"]))

    content.append(Spacer(1, 16))

    if resume.summary:
        _add_section(content, "Professional Summary")
        content.append(Paragraph(resume.summary, S["Summary"]))

    if resume.experience:
        _add_section(content, "Experience")
        for exp in resume.experience:
            _add_experience(content, exp)

    if resume.education:
        _add_section(content, "Education")
        for edu in resume.education:
            _add_education(content, edu)

    if resume.skills:
        _add_section(content, "Skills")
        _add_skills(content, resume.skills)

    if resume.projects:
        _add_section(content, "Projects")
        _add_projects(content, resume.projects)

    if resume.certifications:
        _add_section(content, "Certifications")
        _add_certifications(content, resume.certifications)

    doc.build(content, onFirstPage=_page_number_footer, onLaterPages=_page_number_footer)
    return path
