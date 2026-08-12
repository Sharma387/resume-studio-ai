"""Legacy preview invocation.

Everything behind this module is the retained legacy rendering stack
(Jinja ``HTMLRenderer`` + ``PreviewService`` orchestrated by
``ResumeRenderingService``). Canonical preview must never import these —
it is reached only through this adapter by the ``?template_id=``
compatibility path.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.resume import Resume


def generate_legacy_preview(
    resume: Resume,
    template_id: str,
    theme: str | None = None,
) -> str:
    """Generate a legacy Jinja HTML preview and return its file path."""
    from app.rendering.service import ResumeRenderingService

    return ResumeRenderingService().generate_preview(resume, template_id, theme=theme)
