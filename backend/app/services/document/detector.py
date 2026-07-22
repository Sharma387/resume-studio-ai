from pathlib import Path

from app.services.document.extractors.base import BaseExtractor
from app.services.document.extractors.pdf import PDFExtractor
from app.services.document.extractors.docx import DOCXExtractor
from app.services.document.extractors.txt import TXTExtractor

# Maps file extension → (mime_type, extractor_class, file_type)
EXTRACTOR_REGISTRY: dict[str, tuple[str, type[BaseExtractor], str]] = {
    ".pdf": ("application/pdf", PDFExtractor, "pdf"),
    ".docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        DOCXExtractor,
        "docx",
    ),
    ".txt": ("text/plain", TXTExtractor, "txt"),
}

# MIME type → file_type lookup
MIME_TO_TYPE: dict[str, tuple[str, type[BaseExtractor]]] = {
    v[0]: (v[2], v[1]) for v in EXTRACTOR_REGISTRY.values()
}


def detect_file_type(filename: str) -> str | None:
    """Return the normalized file type for a given filename."""
    ext = Path(filename).suffix.lower()
    entry = EXTRACTOR_REGISTRY.get(ext)
    return entry[2] if entry else None


def detect_mime_type(filename: str) -> str:
    """Return the MIME type for a given filename."""
    ext = Path(filename).suffix.lower()
    entry = EXTRACTOR_REGISTRY.get(ext)
    return entry[0] if entry else "application/octet-stream"


def get_extractor(file_type: str) -> BaseExtractor:
    """Return an extractor instance for the given file type."""
    for entry in EXTRACTOR_REGISTRY.values():
        if entry[2] == file_type:
            return entry[1]()
    raise ValueError(f"No extractor registered for file type '{file_type}'")


def get_extractor_for_filename(filename: str) -> BaseExtractor:
    """Detect file type from filename and return the matching extractor."""
    ext = Path(filename).suffix.lower()
    entry = EXTRACTOR_REGISTRY.get(ext)
    if entry is None:
        raise ValueError(f"Unsupported file extension '{ext}'")
    return entry[1]()
