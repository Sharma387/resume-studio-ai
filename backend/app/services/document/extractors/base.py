from abc import ABC, abstractmethod
from pathlib import Path

from app.models.document import ExtractionResult


class BaseExtractor(ABC):
    """Abstract base for all document extractors."""

    @abstractmethod
    def extract(self, filepath: Path) -> ExtractionResult:
        """Extract text content from a document.

        Args:
            filepath: Path to the document file on disk.

        Returns:
            ExtractionResult containing extracted text and page count.
        """
        ...
