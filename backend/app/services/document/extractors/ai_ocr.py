"""AI-based PDF text extraction using a local vision model.

The PDF text layer (PyMuPDF) is empty or near-empty for image-only resumes
(scanned pages, export-from-image pipelines). When that happens the resume
cannot be parsed at all, so the pages are rendered to images and a local
vision model transcribes them.

This is a *fallback*: callers keep the text layer whenever it carries real
content, and only reach for OCR when it does not. ``ocr_pdf`` returns
``None`` whenever OCR is unavailable or yields nothing, so extraction never
fails because of it.
"""

from __future__ import annotations

import base64

import fitz
import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.models.document import ExtractionResult

logger = get_logger(__name__)

OLLAMA_BASE = "http://localhost:11434"

OCR_PROMPT = (
    "Transcribe this resume page verbatim as plain text. Keep every line, "
    "bullet, heading, date, number, amount, and symbol exactly as shown, and "
    "keep the reading order. Do not summarize, reword, or add commentary."
)

# Vision-capable model families to look for, best first.
_VISION_PREFERENCES = ("qwen3-vl", "qwen2.5-vl", "qwen2-vl", "llava", "minicpm-v", "moondream", "gemma3")


def resolve_vision_model() -> str | None:
    """Return the configured vision model if it is installed, else a discovered one."""
    configured = settings.pdf_ai_ocr_model.strip()
    try:
        response = httpx.get(f"{OLLAMA_BASE}/api/tags", timeout=settings.pdf_ai_ocr_probe_timeout)
        if response.status_code != 200:
            return None
        installed = [m.get("name", "") for m in response.json().get("models", [])]
    except Exception as exc:  # noqa: BLE001 - Ollama may be down; caller falls back
        logger.debug("Ollama model discovery failed for AI OCR: %s", exc)
        return None

    if configured and any(name == configured or name.startswith(configured.split(":")[0]) for name in installed):
        return configured
    lowered = [(name, name.lower()) for name in installed]
    for family in _VISION_PREFERENCES:
        for name, low in lowered:
            if family in low:
                return name
    return None


def _transcribe_page(model: str, png_bytes: bytes) -> str:
    """Ask the vision model to transcribe one rendered page."""
    encoded = base64.b64encode(png_bytes).decode()
    body = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": OCR_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}},
                ],
            }
        ],
        "stream": False,
        "options": {"num_predict": settings.pdf_ai_ocr_num_predict, "temperature": 0.0},
    }
    response = httpx.post(
        f"{OLLAMA_BASE}/v1/chat/completions",
        json=body,
        timeout=settings.pdf_ai_ocr_timeout,
    )
    if response.status_code != 200:
        logger.warning("AI OCR request failed with HTTP %s", response.status_code)
        return ""
    message = response.json().get("choices", [{}])[0].get("message", {}) or {}
    # Vision models may answer under "thinking" if reasoning is enabled.
    return (message.get("content") or message.get("thinking") or "").strip()


def ocr_pdf(filepath, *, dpi: int | None = None) -> ExtractionResult | None:
    """Transcribe every page of a PDF with a local vision model.

    Returns ``None`` when no vision model is installed, OCR fails, or every
    page comes back empty, so the caller can keep whatever the text layer
    provided.
    """
    model = resolve_vision_model()
    if model is None:
        logger.info("AI OCR skipped: no vision model installed")
        return None

    render_dpi = dpi or settings.pdf_ai_ocr_dpi
    pages: list[str] = []
    page_total = 0
    try:
        document = fitz.open(str(filepath))
        page_total = document.page_count
        for number, page in enumerate(document, start=1):
            pixmap = page.get_pixmap(dpi=render_dpi)
            text = _transcribe_page(model, pixmap.tobytes("png"))
            if text:
                pages.append(text)
            else:
                logger.warning("AI OCR produced no text for page %s of %s", number, page_total)
        document.close()
    except Exception as exc:  # noqa: BLE001 - OCR is a fallback, never fatal
        logger.warning("AI OCR failed for %s: %s", filepath, exc)
        return None

    if not pages:
        return None
    content = "\n\n".join(pages).strip()
    if not content:
        return None
    logger.info(
        "AI OCR via %s transcribed %s/%s pages (%s chars)", model, len(pages), page_total, len(content)
    )
    return ExtractionResult(content=content, page_count=page_total or len(pages))
