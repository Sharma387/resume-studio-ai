from pathlib import Path

import fitz

from app.core.config import settings
from app.core.logging import get_logger
from app.models.document import ExtractionResult
from app.services.document.extractors.ai_ocr import ocr_pdf
from app.services.document.extractors.base import BaseExtractor

logger = get_logger(__name__)


class PDFExtractor(BaseExtractor):
    """Extract text from PDF files using PyMuPDF, with AI OCR as fallback.

    The PDF text layer is authoritative when it carries real content. It is
    empty or near-empty for image-only resumes (scanned pages), which then
    cannot be parsed at all, so those pages are rendered and transcribed by a
    local vision model instead.
    """

    def extract(self, filepath: Path) -> ExtractionResult:
        if filepath.stat().st_size == 0:
            return ExtractionResult(content="", page_count=0)

        doc = fitz.open(str(filepath))
        raw_pages: list[str] = [page.get_text("text") for page in doc]
        doc.close()

        full_text = "\n".join(raw_pages)
        if self._needs_ocr(full_text, len(raw_pages)) and settings.pdf_ai_ocr_fallback:
            ocr = ocr_pdf(filepath)
            if ocr is not None and ocr.content.strip():
                logger.info(
                    "PDF text layer thin (%s chars); AI OCR supplied %s chars",
                    len(full_text.strip()),
                    len(ocr.content),
                )
                return ocr
            logger.info("PDF text layer thin and AI OCR unavailable; using text layer")

        return ExtractionResult(content=full_text, page_count=len(raw_pages))

    @staticmethod
    def _needs_ocr(text: str, page_count: int) -> bool:
        """True when the text layer is too sparse per page to be real text.

        Density is judged per page rather than per document: a 3-page scan
        yields ~0 chars on every page, while a short but genuine one-page
        resume still clears the bar and is never needlessly OCR'd.
        """
        stripped = text.strip()
        if not stripped:
            return page_count > 0
        return len(stripped) / max(page_count, 1) < settings.pdf_text_layer_min_chars
