"""Tests for AI-based PDF OCR extraction (model calls are mocked)."""

from pathlib import Path

import pytest

from app.core.config import settings
from app.models.document import ExtractionResult
from app.services.document import extractors
from app.services.document.extractors.ai_ocr import ocr_pdf, resolve_vision_model
from app.services.document.extractors.pdf import PDFExtractor


def _write_text_pdf(tmp_path: Path, content: str) -> Path:
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), content, fontsize=11)
    path = tmp_path / "text.pdf"
    doc.save(str(path))
    doc.close()
    return path


# Long enough to clear the "thin text layer" threshold, i.e. a real text-layer
# PDF that must never be routed through the slow OCR path.
_RICH_TEXT = (
    "Jane Doe  Senior Project Manager  Auckland New Zealand  jane@example.com\n"
    "PROFESSIONAL SUMMARY\n"
    "Seasoned delivery leader with 24 years of enterprise infrastructure, cloud, "
    "cybersecurity and agile delivery experience across healthcare, airline and "
    "utility sectors, focused on measurable outcomes and durable governance.\n"
    "CORE COMPETENCIES\n"
    "Project and programme management, vendor management, financial management, "
    "risk and change governance, business intelligence and data visualisation."
)


def _write_blank_pdf(tmp_path: Path) -> Path:
    """A PDF with a valid but empty text layer, i.e. a scanned-style page."""
    import fitz

    doc = fitz.open()
    doc.new_page()
    path = tmp_path / "scan.pdf"
    doc.save(str(path))
    doc.close()
    return path


class TestPDFExtractorOcrFallback:
    @pytest.fixture(autouse=True)
    def _enable_ocr(self):
        """The global test fixture disables OCR; these tests exercise it."""
        settings.pdf_ai_ocr_fallback = True

    def test_uses_text_layer_when_it_has_content(self, tmp_path, monkeypatch):
        called = {"count": 0}

        def _fail(*args, **kwargs):
            called["count"] += 1
            return None

        monkeypatch.setattr(extractors.pdf, "ocr_pdf", _fail)
        path = _write_text_pdf(tmp_path, _RICH_TEXT)

        result = PDFExtractor().extract(path)

        assert "Jane Doe" in result.content
        assert called["count"] == 0, "OCR must not run when the text layer is real"

    def test_falls_back_to_ocr_for_thin_text_layer(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            extractors.pdf,
            "ocr_pdf",
            lambda *a, **k: ExtractionResult(content="Scanned Jane Doe", page_count=1),
        )
        path = _write_blank_pdf(tmp_path)

        result = PDFExtractor().extract(path)

        assert result.content == "Scanned Jane Doe"
        assert result.page_count == 1

    def test_keeps_text_layer_when_ocr_fails(self, tmp_path, monkeypatch):
        monkeypatch.setattr(extractors.pdf, "ocr_pdf", lambda *a, **k: None)
        path = _write_blank_pdf(tmp_path)

        result = PDFExtractor().extract(path)

        assert result.content == ""
        assert result.page_count == 1

    def test_ocr_fallback_can_be_disabled(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "pdf_ai_ocr_fallback", False)
        monkeypatch.setattr(
            extractors.pdf,
            "ocr_pdf",
            lambda *a, **k: pytest_fail("OCR should not run when disabled"),
        )
        path = _write_blank_pdf(tmp_path)

        assert PDFExtractor().extract(path).content == ""


def pytest_fail(msg):  # noqa: D103 - tiny helper used as a sentinel
    raise AssertionError(msg)


class TestResolveVisionModel:
    def test_prefers_configured_model(self, monkeypatch):
        monkeypatch.setattr(settings, "pdf_ai_ocr_model", "qwen3-vl:8b")
        monkeypatch.setattr(
            extractors.ai_ocr.httpx,
            "get",
            lambda *a, **k: _tags_response(["qwen3-vl:8b", "deepseek-coder-v2:16b"]),
        )
        assert resolve_vision_model() == "qwen3-vl:8b"

    def test_discovers_vision_model_when_configured_missing(self, monkeypatch):
        monkeypatch.setattr(settings, "pdf_ai_ocr_model", "some-vl:70b")
        monkeypatch.setattr(
            extractors.ai_ocr.httpx,
            "get",
            lambda *a, **k: _tags_response(["deepseek-coder-v2:16b", "qwen2-vl:7b"]),
        )
        assert resolve_vision_model() == "qwen2-vl:7b"

    def test_returns_none_without_any_vision_model(self, monkeypatch):
        monkeypatch.setattr(settings, "pdf_ai_ocr_model", "qwen3-vl:8b")
        monkeypatch.setattr(
            extractors.ai_ocr.httpx,
            "get",
            lambda *a, **k: _tags_response(["deepseek-coder-v2:16b", "qwen2.5-coder:14b"]),
        )
        assert resolve_vision_model() is None

    def test_returns_none_when_ollama_unreachable(self, monkeypatch):
        def _raise(*a, **k):
            raise RuntimeError("connection refused")

        monkeypatch.setattr(extractors.ai_ocr.httpx, "get", _raise)
        assert resolve_vision_model() is None


class TestOcrPdf:
    def test_returns_none_without_vision_model(self, tmp_path, monkeypatch):
        monkeypatch.setattr(extractors.ai_ocr, "resolve_vision_model", lambda: None)
        path = _write_text_pdf(tmp_path, "content")
        assert ocr_pdf(path) is None

    def test_transcribes_every_page(self, tmp_path, monkeypatch):
        import fitz

        doc = fitz.open()
        for _ in range(2):
            doc.new_page()
        path = tmp_path / "two.pdf"
        doc.save(str(path))
        doc.close()

        monkeypatch.setattr(extractors.ai_ocr, "resolve_vision_model", lambda: "qwen3-vl:8b")
        monkeypatch.setattr(extractors.ai_ocr, "_transcribe_page", lambda model, png: f"page text {model}")

        result = ocr_pdf(path)

        assert result is not None
        assert result.page_count == 2
        assert result.content.count("qwen3-vl:8b") == 2

    def test_returns_none_when_all_pages_empty(self, tmp_path, monkeypatch):
        import fitz

        doc = fitz.open()
        doc.new_page()
        path = tmp_path / "empty.pdf"
        doc.save(str(path))
        doc.close()

        monkeypatch.setattr(extractors.ai_ocr, "resolve_vision_model", lambda: "qwen3-vl:8b")
        monkeypatch.setattr(extractors.ai_ocr, "_transcribe_page", lambda model, png: "   ")

        assert ocr_pdf(path) is None

    def test_returns_none_on_transport_error(self, tmp_path, monkeypatch):
        import fitz

        doc = fitz.open()
        doc.new_page()
        path = tmp_path / "err.pdf"
        doc.save(str(path))
        doc.close()

        monkeypatch.setattr(extractors.ai_ocr, "resolve_vision_model", lambda: "qwen3-vl:8b")

        def _raise(model, png):
            raise RuntimeError("ollama died")

        monkeypatch.setattr(extractors.ai_ocr, "_transcribe_page", _raise)
        assert ocr_pdf(path) is None


def _tags_response(names: list[str]):
    class _Response:
        status_code = 200

        @staticmethod
        def json():
            return {"models": [{"name": n} for n in names]}

    return _Response()
