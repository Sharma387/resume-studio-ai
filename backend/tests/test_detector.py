from app.services.document.detector import (
    detect_file_type,
    detect_mime_type,
    get_extractor_for_filename,
    get_extractor,
)
from app.services.document.extractors.pdf import PDFExtractor
from app.services.document.extractors.docx import DOCXExtractor
from app.services.document.extractors.txt import TXTExtractor


class TestDetectFileType:
    def test_pdf(self):
        assert detect_file_type("resume.pdf") == "pdf"

    def test_docx(self):
        assert detect_file_type("resume.docx") == "docx"

    def test_txt(self):
        assert detect_file_type("resume.txt") == "txt"

    def test_unknown(self):
        assert detect_file_type("resume.doc") is None

    def test_case_insensitive(self):
        assert detect_file_type("RESUME.PDF") == "pdf"


class TestDetectMimeType:
    def test_pdf(self):
        assert detect_mime_type("resume.pdf") == "application/pdf"

    def test_docx(self):
        assert detect_mime_type("resume.docx") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    def test_txt(self):
        assert detect_mime_type("resume.txt") == "text/plain"

    def test_unknown(self):
        assert detect_mime_type("resume.doc") == "application/octet-stream"


class TestGetExtractor:
    def test_pdf_extractor(self):
        assert isinstance(get_extractor("pdf"), PDFExtractor)

    def test_docx_extractor(self):
        assert isinstance(get_extractor("docx"), DOCXExtractor)

    def test_txt_extractor(self):
        assert isinstance(get_extractor("txt"), TXTExtractor)

    def test_unknown_type(self):
        import pytest
        with pytest.raises(ValueError):
            get_extractor("doc")


class TestGetExtractorForFilename:
    def test_pdf(self):
        assert isinstance(get_extractor_for_filename("r.pdf"), PDFExtractor)

    def test_docx(self):
        assert isinstance(get_extractor_for_filename("r.docx"), DOCXExtractor)

    def test_txt(self):
        assert isinstance(get_extractor_for_filename("r.txt"), TXTExtractor)

    def test_unknown(self):
        import pytest
        with pytest.raises(ValueError):
            get_extractor_for_filename("r.doc")
