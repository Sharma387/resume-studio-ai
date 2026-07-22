from pathlib import Path

from app.services.document.metadata import MetadataExtractor


class TestWordCount:
    def test_empty(self):
        assert MetadataExtractor.word_count("") == 0

    def test_single_word(self):
        assert MetadataExtractor.word_count("hello") == 1

    def test_multiple_words(self):
        assert MetadataExtractor.word_count("hello world foo") == 3

    def test_whitespace_only(self):
        assert MetadataExtractor.word_count("   ") == 0


class TestCharacterCount:
    def test_empty(self):
        assert MetadataExtractor.character_count("") == 0

    def test_simple(self):
        assert MetadataExtractor.character_count("hello") == 5

    def test_with_spaces(self):
        assert MetadataExtractor.character_count("hello world") == 11


class TestFileMetadata:
    def test_returns_size(self, tmp_path: Path):
        path = tmp_path / "test.txt"
        path.write_text("hello")
        meta = MetadataExtractor.file_metadata(path)
        assert meta["size_bytes"] == 5

    def test_has_timestamps(self, tmp_path: Path):
        path = tmp_path / "test.txt"
        path.write_text("hello")
        meta = MetadataExtractor.file_metadata(path)
        assert "created_at" in meta
        assert "modified_at" in meta
