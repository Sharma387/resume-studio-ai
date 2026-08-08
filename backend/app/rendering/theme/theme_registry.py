"""Thread-safe registry of declarative theme palettes."""

from __future__ import annotations

import threading
from collections.abc import Mapping
from types import MappingProxyType

from app.rendering.theme.theme_metadata import ThemeMetadata, ThemeVersion
from app.rendering.theme.theme_palette import ThemePalette


class ThemeRegistryError(Exception):
    """Base error for the theme registry."""


class ThemeRegistrationError(ThemeRegistryError, ValueError):
    """Raised when a theme cannot be registered."""


class ThemeLookupError(ThemeRegistryError, KeyError):
    """Raised when no theme is registered for an id."""


class ThemeRegistry:
    """Maps theme ids to immutable :class:`ThemePalette` objects.

    Registration order is preserved and is the deterministic ``list()`` order.
    All operations are guarded by a lock, making reads thread-safe. Returned
    collections are immutable.
    """

    def __init__(
        self,
        *,
        allow_replacement: bool = False,
        supported_engine_version: ThemeVersion | None = None,
    ) -> None:
        self._allow_replacement = allow_replacement
        self._supported_engine_version = supported_engine_version or ThemeVersion(major=1, minor=0, patch=0)
        self._by_theme_id: dict[str, ThemePalette] = {}
        self._by_stable_id: dict[str, ThemePalette] = {}
        self._lock = threading.RLock()

    # Registration lifecycle
    def register(
        self,
        palette: ThemePalette,
        allow_replacement: bool | None = None,
    ) -> None:
        if not isinstance(palette, ThemePalette):
            raise ThemeRegistrationError(
                f"palette must be a ThemePalette, got {type(palette).__name__}"
            )
        if palette.metadata.engine_version > self._supported_engine_version:
            raise ThemeRegistrationError(
                f"theme '{palette.theme_id}' requires engine "
                f"{palette.metadata.engine_version} but supported is "
                f"{self._supported_engine_version}"
            )
        effective = self._allow_replacement if allow_replacement is None else allow_replacement
        with self._lock:
            if palette.theme_id in self._by_theme_id and not effective:
                raise ThemeRegistrationError(
                    f"theme id '{palette.theme_id}' already registered"
                )
            if palette.stable_id in self._by_stable_id and not effective:
                raise ThemeRegistrationError(
                    f"stable id '{palette.stable_id}' already registered"
                )
            self._by_theme_id[palette.theme_id] = palette
            self._by_stable_id[palette.stable_id] = palette

    def unregister(self, theme_id: str) -> ThemePalette | None:
        with self._lock:
            palette = self._by_theme_id.pop(theme_id, None)
        if palette is not None:
            with self._lock:
                self._by_stable_id.pop(palette.stable_id, None)
        return palette

    # Lookup
    def resolve(self, theme_id: str) -> ThemePalette:
        with self._lock:
            palette = self._by_theme_id.get(theme_id)
        if palette is None:
            raise ThemeLookupError(f"unknown theme '{theme_id}'")
        return palette

    def lookup(self, stable_id: str) -> ThemePalette | None:
        """Look up a theme by its permanent stable id."""
        with self._lock:
            return self._by_stable_id.get(stable_id)

    def get(self, theme_id: str) -> ThemePalette | None:
        with self._lock:
            return self._by_theme_id.get(theme_id)

    def contains(self, theme_id: str) -> bool:
        return self.get(theme_id) is not None

    # Validation
    def validate(self, palette: ThemePalette) -> None:
        """Check a palette is registerable (engine gate + uniqueness)."""
        self.register(palette)

    # Listing / metadata
    def list(self) -> tuple[str, ...]:
        """Theme ids in registration order (immutable)."""
        with self._lock:
            return tuple(self._by_theme_id.keys())

    def palettes(self) -> tuple[ThemePalette, ...]:
        with self._lock:
            return tuple(self._by_theme_id.values())

    def ordered(self) -> tuple[ThemePalette, ...]:
        """Palettes ordered by (stable_id, version) — deterministic."""
        with self._lock:
            return tuple(
                sorted(
                    self._by_theme_id.values(),
                    key=lambda p: (p.stable_id, str(p.metadata.version)),
                )
            )

    def metadata(self) -> Mapping[str, ThemeMetadata]:
        """Immutable theme-id → metadata mapping."""
        with self._lock:
            return MappingProxyType(
                {theme_id: palette.metadata for theme_id, palette in self._by_theme_id.items()}
            )

    def __len__(self) -> int:
        with self._lock:
            return len(self._by_theme_id)

    def __iter__(self):
        with self._lock:
            return iter(tuple(self._by_theme_id.keys()))

    def __contains__(self, theme_id: object) -> bool:
        return isinstance(theme_id, str) and self.contains(theme_id)
