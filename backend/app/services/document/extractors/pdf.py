from pathlib import Path

import fitz

from app.services.document.extractors.base import BaseExtractor
from app.models.document import ExtractionResult


class PDFExtractor(BaseExtractor):
    """Extract text from PDF files using PyMuPDF."""

    def extract(self, filepath: Path) -> ExtractionResult:
        if filepath.stat().st_size == 0:
            return ExtractionResult(content="", page_count=0)

        doc = fitz.open(str(filepath))
        raw_pages: list[str] = []

        for page in doc:
            text = page.get_text("text")
            raw_pages.append(text)

        doc.close()

        full_text = "\n".join(raw_pages)
        return ExtractionResult(content=full_text, page_count=len(raw_pages))
