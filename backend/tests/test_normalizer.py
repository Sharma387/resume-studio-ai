from app.services.document.normalizer import TextNormalizer


class TestTextNormalizer:
    def test_removes_extra_blank_lines(self):
        result = TextNormalizer.normalize("Line 1\n\n\n\nLine 2")
        assert result == "Line 1\n\nLine 2"

    def test_strips_lines(self):
        result = TextNormalizer.normalize("  Hello  \n  World  ")
        assert result == "Hello\nWorld"

    def test_empty_string(self):
        result = TextNormalizer.normalize("")
        assert result == ""

    def test_only_whitespace(self):
        result = TextNormalizer.normalize("   \n  \n  ")
        assert result == ""

    def test_single_line(self):
        result = TextNormalizer.normalize("  Hello World  ")
        assert result == "Hello World"

    def test_normalize_spaces(self):
        result = TextNormalizer.normalize("Hello    World")
        assert result == "Hello World"

    def test_no_changes_needed(self):
        text = "Line 1\n\nLine 2"
        result = TextNormalizer.normalize(text)
        assert result == text
