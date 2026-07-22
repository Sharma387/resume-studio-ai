from pathlib import Path

from app.services.upload_service import UPLOAD_DIR
from app.services.document.detector import get_extractor_for_filename, detect_file_type
from app.services.document.normalizer import TextNormalizer
from app.services.document.metadata import MetadataExtractor


class ExtractResult:
    def __init__(self, pages: int, characters: int, text: str):
        self.pages = pages
        self.characters = characters
        self.text = text

    def to_dict(self) -> dict:
        return {
            "success": True,
            "data": {
                "pages": self.pages,
                "characters": self.characters,
                "text": self.text,
            },
        }


def extract_document(filename: str) -> ExtractResult:
    filepath = UPLOAD_DIR / filename

    if not filepath.exists():
        raise FileNotFoundError(f"File '{filename}' not found")

    extractor = get_extractor_for_filename(filename)
    raw = extractor.extract(filepath)

    normalizer = TextNormalizer()
    cleaned = normalizer.normalize(raw.content)

    char_count = MetadataExtractor.character_count(cleaned)

    return ExtractResult(
        pages=raw.page_count,
        characters=char_count,
        text=cleaned,
    )
