"""Legacy ReportLab PDF generation.

The retained ReportLab ``pdf_templates`` engine is only reachable through
this adapter. Canonical export uses ``RenderTreePDFRenderer`` instead and
must never import ReportLab.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.resume import Resume


def generate_legacy_pdf(
    resume_id: str,
    resume: Resume,
    template_name: str | None = None,
) -> Path:
    """Generate a legacy ReportLab PDF and return its file path."""
    from app.services.pdf_service import generate_pdf

    return generate_pdf(resume_id, resume, template_name)


def pdf_dir() -> Path:
    """The legacy PDF output directory."""
    from app.services.pdf_templates.engine import PDF_DIR

    return PDF_DIR


def list_legacy_template_names() -> list[str]:
    """List the legacy ReportLab template names."""
    from app.services.pdf_templates.registry import TemplateRegistry

    return TemplateRegistry.list_names()
