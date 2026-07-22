from pathlib import Path

import pytest

from app.services.document.detector import get_extractor_for_filename
from app.models.document import ExtractionResult


def _write_pdf(tmp_path: Path, pages: list[str]) -> Path:
    import fitz
    doc = fitz.open()
    for content in pages:
        page = doc.new_page()
        page.insert_text((50, 50), content, fontsize=11)
    path = tmp_path / "test.pdf"
    doc.save(str(path))
    doc.close()
    return path


def _write_docx(tmp_path: Path, paragraphs: list[str]) -> Path:
    from docx import Document
    doc = Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    path = tmp_path / "test.docx"
    doc.save(str(path))
    return path


def _write_txt(tmp_path: Path, text: str, encoding: str = "utf-8") -> Path:
    path = tmp_path / "test.txt"
    path.write_text(text, encoding=encoding)
    return path


class TestPDFExtractor:
    def test_extracts_text(self, tmp_path: Path):
        path = _write_pdf(tmp_path, ["Hello World"])
        ext = get_extractor_for_filename("test.pdf")
        result = ext.extract(path)
        assert isinstance(result, ExtractionResult)
        assert "Hello World" in result.content
        assert result.page_count == 1

    def test_multi_page(self, tmp_path: Path):
        path = _write_pdf(tmp_path, ["Page 1", "Page 2", "Page 3"])
        ext = get_extractor_for_filename("test.pdf")
        result = ext.extract(path)
        assert result.page_count == 3

    def test_empty_file(self, tmp_path: Path):
        path = tmp_path / "empty.pdf"
        path.write_text("")
        ext = get_extractor_for_filename("test.pdf")
        result = ext.extract(path)
        assert result.page_count == 0
        assert result.content == ""


class TestDOCXExtractor:
    def test_extracts_paragraphs(self, tmp_path: Path):
        path = _write_docx(tmp_path, ["Hello", "World"])
        ext = get_extractor_for_filename("test.docx")
        result = ext.extract(path)
        assert "Hello" in result.content
        assert "World" in result.content
        assert result.page_count >= 1

    def test_empty_file(self, tmp_path: Path):
        path = tmp_path / "empty.docx"
        path.write_text("")
        ext = get_extractor_for_filename("test.docx")
        result = ext.extract(path)
        assert result.page_count == 0
        assert result.content == ""


class TestTXTExtractor:
    def test_extracts_text(self, tmp_path: Path):
        path = _write_txt(tmp_path, "Hello World")
        ext = get_extractor_for_filename("test.txt")
        result = ext.extract(path)
        assert "Hello World" in result.content
        assert result.page_count >= 1

    def test_utf8_fallback(self, tmp_path: Path):
        path = _write_txt(tmp_path, "café", encoding="utf-8")
        ext = get_extractor_for_filename("test.txt")
        result = ext.extract(path)
        assert "café" in result.content

    def test_empty_file(self, tmp_path: Path):
        path = tmp_path / "empty.txt"
        path.write_text("")
        ext = get_extractor_for_filename("test.txt")
        result = ext.extract(path)
        assert result.page_count == 0
        assert result.content == ""


class TestExtractionResultDTO:
    def test_creation(self):
        result = ExtractionResult(content="hello", page_count=1)
        assert result.content == "hello"
        assert result.page_count == 1

    def test_default_page_count(self):
        result = ExtractionResult(content="text")
        assert result.page_count == 0
