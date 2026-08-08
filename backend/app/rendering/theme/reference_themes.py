"""Reference themes — lightweight data-only palettes validating the registry.

These exist purely to exercise the Theme Registry. Real palettes ship in a
later phase. Themes never influence layout structure.
"""

from __future__ import annotations

from app.rendering.theme.theme_metadata import ThemeMetadata, ThemeVersion
from app.rendering.theme.theme_palette import ThemePalette
from app.rendering.theme.theme_tokens import ColorTokens, ThemeTokens


def _build(name: str, *, display_name: str, description: str, colors: dict[str, str]) -> ThemePalette:
    metadata = ThemeMetadata(
        theme_id=name,
        stable_id=f"theme.{name}.v1",
        display_name=display_name,
        description=description,
        version=ThemeVersion(major=1, minor=0, patch=0),
        api_version=ThemeVersion(major=1, minor=0, patch=0),
        engine_version=ThemeVersion(major=1, minor=0, patch=0),
    )
    return ThemePalette(
        metadata=metadata,
        tokens=ThemeTokens(colors=ColorTokens(**colors)),
    )


REFERENCE_COLORS: dict[str, dict[str, str]] = {
    "blue": {
        "primary": "#2563eb",
        "on_primary": "#ffffff",
        "accent": "#1e40af",
        "background": "#ffffff",
        "on_background": "#1e293b",
        "text": "#1e293b",
        "muted": "#64748b",
        "border": "#e2e8f0",
        "success": "#2e7d32",
    },
    "slate": {
        "primary": "#475569",
        "on_primary": "#ffffff",
        "accent": "#334155",
        "background": "#ffffff",
        "on_background": "#0f172a",
        "text": "#0f172a",
        "muted": "#94a3b8",
        "border": "#cbd5e1",
        "success": "#15803d",
    },
    "forest": {
        "primary": "#2f855a",
        "on_primary": "#ffffff",
        "accent": "#276749",
        "background": "#fafafa",
        "on_background": "#1c2a21",
        "text": "#1c2a21",
        "muted": "#6b7280",
        "border": "#d1d5db",
        "success": "#166534",
    },
    "gold": {
        "primary": "#b98a2f",
        "on_primary": "#ffffff",
        "accent": "#8a641f",
        "background": "#ffffff",
        "on_background": "#1a1a1a",
        "text": "#1a1a1a",
        "muted": "#6b6b6b",
        "border": "#e5e5e5",
        "success": "#2e7d32",
    },
    "minimal": {
        "primary": "#111827",
        "on_primary": "#ffffff",
        "accent": "#374151",
        "background": "#ffffff",
        "on_background": "#111827",
        "text": "#111827",
        "muted": "#6b7280",
        "border": "#e5e7eb",
        "success": "#15803d",
    },
}


def blue_theme() -> ThemePalette:
    return _build("blue", display_name="Blue", description="Trusted corporate blue.", colors=REFERENCE_COLORS["blue"])


def slate_theme() -> ThemePalette:
    return _build("slate", display_name="Slate", description="Neutral analytical slate.", colors=REFERENCE_COLORS["slate"])


def forest_theme() -> ThemePalette:
    return _build("forest", display_name="Forest", description="Grounded green palette.", colors=REFERENCE_COLORS["forest"])


def gold_theme() -> ThemePalette:
    return _build("gold", display_name="Gold", description="Premium executive gold.", colors=REFERENCE_COLORS["gold"])


def minimal_theme() -> ThemePalette:
    return _build("minimal", display_name="Minimal", description="Monochrome minimal palette.", colors=REFERENCE_COLORS["minimal"])


REFERENCE_THEMES: tuple[ThemePalette, ...] = (
    blue_theme(),
    slate_theme(),
    forest_theme(),
    gold_theme(),
    minimal_theme(),
)
