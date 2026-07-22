from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT, TA_RIGHT

from app.models.cover_letter import CoverLetter
from app.models.resume import Resume

PDF_DIR = Path("storage") / "cover_letter_pdfs"
PDF_DIR.mkdir(parents=True, exist_ok=True)

GRAY = HexColor("#555555")


def generate_cover_letter_pdf(resume_id: str, letter_id: str, letter: CoverLetter, resume: Resume) -> Path:
    path = PDF_DIR / f"{letter_id}.pdf"
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=25 * mm,
        rightMargin=25 * mm,
        topMargin=25 * mm,
        bottomMargin=25 * mm,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("SenderName", fontSize=16, fontName="Helvetica-Bold", spaceAfter=2, leading=20))
    styles.add(ParagraphStyle("SenderInfo", fontSize=9, fontName="Helvetica", textColor=GRAY, spaceAfter=2, leading=13))
    styles.add(ParagraphStyle("DateLine", fontSize=10, fontName="Helvetica", spaceBefore=12, spaceAfter=12))
    styles.add(ParagraphStyle("Recipient", fontSize=10, fontName="Helvetica", spaceAfter=2, leading=14))
    styles.add(ParagraphStyle("Subject", fontSize=10, fontName="Helvetica-Bold", spaceBefore=12, spaceAfter=12))
    styles.add(ParagraphStyle("Body", fontSize=10, fontName="Helvetica", spaceAfter=6, leading=16))
    styles.add(ParagraphStyle("Signature", fontSize=10, fontName="Helvetica-Bold", spaceBefore=20))

    content = []

    content.append(Paragraph(resume.full_name, styles["SenderName"]))
    contact = "  |  ".join(p for p in [resume.email, resume.phone, resume.location] if p)
    if contact:
        content.append(Paragraph(contact, styles["SenderInfo"]))

    from datetime import datetime
    content.append(Paragraph(datetime.now().strftime("%B %d, %Y"), styles["DateLine"]))

    recipient_lines = []
    if letter.company_name:
        recipient_lines.append(letter.company_name)
    recipient_lines.append(f"Attn: {letter.hiring_manager}" if letter.hiring_manager else "Attn: Hiring Manager")
    if letter.role_title:
        recipient_lines.append(f"Re: {letter.role_title}")
    for line in recipient_lines:
        content.append(Paragraph(line, styles["Recipient"]))

    if letter.subject:
        content.append(Paragraph(f"Subject: {letter.subject}", styles["Subject"]))

    for para in letter.content.split("\n\n"):
        para = para.strip()
        if para:
            content.append(Paragraph(para, styles["Body"]))

    content.append(Spacer(1, 12))
    content.append(Paragraph(resume.full_name, styles["Signature"]))

    doc.build(content)
    return path
