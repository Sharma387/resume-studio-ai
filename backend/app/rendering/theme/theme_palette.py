"""Theme palette — immutable composition of theme metadata and tokens."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.rendering.theme.theme_metadata import ThemeMetadata
from app.rendering.theme.theme_tokens import ThemeTokens


class ThemePalette(BaseModel):
    """A complete theme: immutable metadata plus visual design tokens.

    Purely declarative — no rendering behaviour. Themes never influence layout
    structure (that responsibility belongs to the Layout Registry).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    metadata: ThemeMetadata
    tokens: ThemeTokens

    @property
    def theme_id(self) -> str:
        return self.metadata.theme_id

    @property
    def stable_id(self) -> str:
        return self.metadata.stable_id
