"""Theme tokens — immutable visual design tokens (Layout Engine).

Tokens are declarative data only: colors, typography, spacing, shape, and
effects. They never influence layout structure. Theme tokenization lives at L3
(config); the ThemeRegistry is its independent registry (L4).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

_HEX_COLOR = r"^#[0-9a-fA-F]{6}$"


class ColorTokens(BaseModel):
    """Core color tokens."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    primary: str = Field(pattern=_HEX_COLOR)
    on_primary: str = Field(pattern=_HEX_COLOR)
    accent: str = Field(pattern=_HEX_COLOR)
    background: str = Field(pattern=_HEX_COLOR)
    on_background: str = Field(pattern=_HEX_COLOR)
    text: str = Field(pattern=_HEX_COLOR)
    muted: str = Field(pattern=_HEX_COLOR)
    border: str = Field(pattern=_HEX_COLOR)
    success: str = Field(pattern=_HEX_COLOR)


class TypographyTokens(BaseModel):
    """Typography tokens."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    family: str = "'Inter', sans-serif"
    heading_family: str = "'Inter', sans-serif"
    size_scale: tuple[float, ...] = (9.0, 10.0, 12.0, 16.0, 20.0)
    line_height: float = Field(default=1.5, gt=0)
    weight_normal: int = Field(default=400, ge=100, le=900)
    weight_strong: int = Field(default=700, ge=100, le=900)
    weight_heading: int = Field(default=700, ge=100, le=900)


class SpacingTokens(BaseModel):
    """Spacing tokens (millimetres) and density."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    unit_mm: float = Field(default=4.0, ge=0)
    section_mm: float = Field(default=8.0, ge=0)
    block_mm: float = Field(default=4.0, ge=0)
    inline_mm: float = Field(default=6.0, ge=0)
    density: Literal["compact", "normal", "spacious"] = "normal"


class ShapeTokens(BaseModel):
    """Shape tokens (radii, borders, shadows)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    radius_mm: float = Field(default=0.0, ge=0)
    border_width_mm: float = Field(default=0.5, ge=0)
    shadow: Literal["none", "soft", "strong"] = "none"


class EffectTokens(BaseModel):
    """Effect tokens (accent and icon styling)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    accent_style: Literal["flat", "gradient", "outline"] = "flat"
    icon_style: Literal["filled", "outline", "line"] = "outline"


class ThemeTokens(BaseModel):
    """The complete set of visual design tokens for a theme."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    colors: ColorTokens
    typography: TypographyTokens = Field(default_factory=TypographyTokens)
    spacing: SpacingTokens = Field(default_factory=SpacingTokens)
    shape: ShapeTokens = Field(default_factory=ShapeTokens)
    effects: EffectTokens = Field(default_factory=EffectTokens)
