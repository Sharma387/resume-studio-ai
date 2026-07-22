import os
from datetime import datetime
from pathlib import Path


class MetadataExtractor:
    """Extract metadata from a document file and its content."""

    @staticmethod
    def word_count(text: str) -> int:
        return len(text.split()) if text.strip() else 0

    @staticmethod
    def character_count(text: str) -> int:
        return len(text)

    @staticmethod
    def file_metadata(filepath: Path) -> dict:
        stat = filepath.stat()
        meta: dict = {}

        created = stat.st_birthtime if hasattr(stat, "st_birthtime") else stat.st_ctime
        meta["created_at"] = datetime.fromtimestamp(created).isoformat() if created else None
        meta["modified_at"] = datetime.fromtimestamp(stat.st_mtime).isoformat() if stat.st_mtime else None
        meta["size_bytes"] = stat.st_size

        return meta
