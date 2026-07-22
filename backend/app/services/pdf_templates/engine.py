from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate

from app.models.resume import Resume
from app.services.pdf_templates.registry import TemplateRegistry

PDF_DIR = Path("storage") / "pdfs"
PDF_DIR.mkdir(parents=True, exist_ok=True)


def render_pdf(resume_id: str, resume: Resume, template_name: str | None = None) -> Path:
    template = TemplateRegistry.get(template_name) if template_name else TemplateRegistry.get_default()

    path = PDF_DIR / f"{resume_id}.pdf"

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=25 * mm,
        rightMargin=25 * mm,
        topMargin=20 * mm,
        bottomMargin=25 * mm,
    )

    content = template.build_document(resume)

    doc.build(content, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return path


def _page_footer(canvas, doc):
    from reportlab.lib.colors import HexColor
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(HexColor("#aaaaaa"))
    canvas.drawCentredString(A4[0] / 2, 15 * mm, f"Page {doc.page}")
    canvas.restoreState()
