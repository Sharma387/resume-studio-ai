from pathlib import Path

import fitz

from app.services.upload_service import UPLOAD_DIR


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


def _clean_text(text: str) -> str:
    lines = text.split("\n")
    cleaned = []
    prev_blank = False
    for line in lines:
        stripped = line.strip()
        if stripped == "":
            if not prev_blank:
                cleaned.append("")
                prev_blank = True
        else:
            cleaned.append(stripped)
            prev_blank = False
    result = "\n".join(cleaned)
    result = " ".join(result.split())
    return result


def extract_pdf(filename: str) -> ExtractResult:
    filepath = UPLOAD_DIR / filename

    if not filepath.exists():
        raise FileNotFoundError(f"File '{filename}' not found")

    if filepath.stat().st_size == 0:
        return ExtractResult(pages=0, characters=0, text="")

    doc = fitz.open(str(filepath))
    raw_pages = []

    for page in doc:
        text = page.get_text("text")
        raw_pages.append(text)

    doc.close()

    full_text = "\n".join(raw_pages)
    cleaned = _clean_text(full_text)

    return ExtractResult(
        pages=len(raw_pages),
        characters=len(cleaned),
        text=cleaned,
    )
