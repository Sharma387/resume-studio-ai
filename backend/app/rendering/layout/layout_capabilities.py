"""Layout capabilities — strongly typed, declarative metadata (Layout Engine).

Capabilities describe what a layout can express. They are pure metadata the
TreeBuilder and renderers will consume later; they never contain rendering
logic.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class LayoutCapability(str, Enum):
    """Capability identifiers a layout may support."""

    SIDEBAR = "sidebar"
    TIMELINE = "timeline"
    PHOTO = "photo"
    BADGES = "badges"
    METRICS = "metrics"
    TABLES = "tables"
    MULTI_COLUMN = "multi_column"
    MULTI_PAGE = "multi_page"
    QR_CODE = "qr_code"
    PORTFOLIO = "portfolio"
    ICONS = "icons"


class LayoutCapabilities(BaseModel):
    """Immutable capability flags for a layout."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sidebar: bool = False
    timeline: bool = False
    photo: bool = False
    badges: bool = False
    metrics: bool = False
    tables: bool = False
    multi_column: bool = False
    multi_page: bool = True
    qr_code: bool = False
    portfolio: bool = False
    icons: bool = False

    def has(self, capability: LayoutCapability) -> bool:
        """Return True when the layout supports ``capability``."""
        return bool(getattr(self, capability.value))
