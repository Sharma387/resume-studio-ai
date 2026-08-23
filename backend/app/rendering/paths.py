"""Filesystem paths shared by the rendering pipeline.

Kept separate from the rendering modules so the canonical pipeline never
imports the (now retired) legacy template/Jinja stack just to resolve the
preview cache directory.
"""

from pathlib import Path

from app.core.config import settings

PREVIEW_DIR = Path(settings.storage_base) / "previews"
