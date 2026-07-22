from pathlib import Path

from app.models.resume import Resume
from app.services.pdf_templates.engine import render_pdf, PDF_DIR


def generate_pdf(resume_id: str, resume: Resume, template_name: str | None = None) -> Path:
    return render_pdf(resume_id, resume, template_name)
