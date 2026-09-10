"""Thread-safe registry of declarative layout definitions."""

from __future__ import annotations

import threading
from collections.abc import Mapping
from types import MappingProxyType

from app.rendering.layout.layout_definition import LayoutDefinition
from app.rendering.layout.layout_metadata import LayoutMetadata, LayoutVersion


class LayoutRegistryError(Exception):
    """Base error for the layout registry."""


class LayoutRegistrationError(LayoutRegistryError, ValueError):
    """Raised when a layout cannot be registered."""


class LayoutLookupError(LayoutRegistryError, KeyError):
    """Raised when no layout is registered for an id."""


class LayoutRegistry:
    """Maps layout ids to declarative :class:`LayoutDefinition` objects.

    Registration order is preserved and is the deterministic ``list()`` order.
    All operations are guarded by a lock, making reads thread-safe. Returned
    collections are immutable.
    """

    def __init__(
        self,
        *,
        allow_replacement: bool = False,
        supported_engine_version: LayoutVersion | None = None,
    ) -> None:
        self._allow_replacement = allow_replacement
        self._supported_engine_version = supported_engine_version or LayoutVersion(major=1, minor=0, patch=0)
        self._by_layout_id: dict[str, LayoutDefinition] = {}
        self._by_stable_id: dict[str, LayoutDefinition] = {}
        self._lock = threading.RLock()

    # Registration lifecycle
    def register(
        self,
        definition: LayoutDefinition,
        allow_replacement: bool | None = None,
    ) -> None:
        if not isinstance(definition, LayoutDefinition):
            raise LayoutRegistrationError(f"definition must be a LayoutDefinition, got {type(definition).__name__}")
        if definition.metadata.engine_version > self._supported_engine_version:
            raise LayoutRegistrationError(
                f"layout '{definition.layout_id}' requires engine "
                f"{definition.metadata.engine_version} but supported is "
                f"{self._supported_engine_version}"
            )
        effective = self._allow_replacement if allow_replacement is None else allow_replacement
        with self._lock:
            if definition.layout_id in self._by_layout_id and not effective:
                raise LayoutRegistrationError(f"layout id '{definition.layout_id}' already registered")
            if definition.stable_id in self._by_stable_id and not effective:
                raise LayoutRegistrationError(f"stable id '{definition.stable_id}' already registered")
            self._by_layout_id[definition.layout_id] = definition
            self._by_stable_id[definition.stable_id] = definition

    def unregister(self, layout_id: str) -> LayoutDefinition | None:
        with self._lock:
            definition = self._by_layout_id.pop(layout_id, None)
        if definition is not None:
            with self._lock:
                self._by_stable_id.pop(definition.stable_id, None)
        return definition

    # Lookup
    def resolve(self, layout_id: str) -> LayoutDefinition:
        with self._lock:
            definition = self._by_layout_id.get(layout_id)
        if definition is None:
            raise LayoutLookupError(f"unknown layout '{layout_id}'")
        return definition

    def lookup(self, stable_id: str) -> LayoutDefinition | None:
        """Look up a layout by its permanent stable id."""
        with self._lock:
            return self._by_stable_id.get(stable_id)

    def get(self, layout_id: str) -> LayoutDefinition | None:
        with self._lock:
            return self._by_layout_id.get(layout_id)

    def contains(self, layout_id: str) -> bool:
        return self.get(layout_id) is not None

    # Validation
    def validate(self, definition: LayoutDefinition) -> None:
        """Check a definition is registerable (engine gate + uniqueness)."""
        self.register(definition)  # raises on failure; no mutation on success path issues

    # Listing / metadata
    def list(self) -> tuple[str, ...]:
        """Layout ids in registration order (immutable)."""
        with self._lock:
            return tuple(self._by_layout_id.keys())

    def definitions(self) -> tuple[LayoutDefinition, ...]:
        with self._lock:
            return tuple(self._by_layout_id.values())

    def ordered(self) -> tuple[LayoutDefinition, ...]:
        """Definitions ordered by (stable_id, version) — deterministic."""
        with self._lock:
            return tuple(
                sorted(
                    self._by_layout_id.values(),
                    key=lambda d: (d.stable_id, str(d.metadata.version)),
                )
            )

    def metadata(self) -> Mapping[str, LayoutMetadata]:
        """Immutable layout-id → metadata mapping."""
        with self._lock:
            return MappingProxyType(
                {layout_id: definition.metadata for layout_id, definition in self._by_layout_id.items()}
            )

    def __len__(self) -> int:
        with self._lock:
            return len(self._by_layout_id)

    def __iter__(self):
        with self._lock:
            return iter(tuple(self._by_layout_id.keys()))

    def __contains__(self, layout_id: object) -> bool:
        return isinstance(layout_id, str) and self.contains(layout_id)
