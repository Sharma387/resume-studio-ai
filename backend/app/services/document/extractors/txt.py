from pathlib import Path

from app.services.document.extractors.base import BaseExtractor
from app.models.document import ExtractionResult


class TXTExtractor(BaseExtractor):
    """Extract text from plain text files."""

    def extract(self, filepath: Path) -> ExtractionResult:
        if filepath.stat().st_size == 0:
            return ExtractionResult(content="", page_count=0)

        raw = filepath.read_bytes()
        # Try UTF-8 first, fall back to latin-1
        for encoding in ("utf-8", "latin-1"):
            try:
                text = raw.decode(encoding)
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        else:
            text = raw.decode("utf-8", errors="replace")

        # Estimate page count: ~3000 chars per page
        page_count = max(1, len(text) // 3000) if text.strip() else 0

        return ExtractionResult(content=text, page_count=page_count)
