"""Thread-safe registry of section components.

The :class:`ComponentRegistry` maps section types to
:class:`~app.rendering.components.base.SectionComponent` implementations. It is
the extension point the TreeBuilder uses and the seam through which future
plugins register new resume sections.

Registration order is preserved and is the deterministic iteration order. All
operations are guarded by a lock, making reads thread-safe.
"""

from __future__ import annotations

import threading
from collections.abc import Mapping
from types import MappingProxyType

from app.rendering.components.base import ComponentMetadata, SectionComponent


class ComponentRegistryError(Exception):
    """Base error for the component registry."""


class ComponentRegistrationError(ComponentRegistryError, ValueError):
    """Raised when a component cannot be registered."""


class ComponentLookupError(ComponentRegistryError, KeyError):
    """Raised when no component is registered for a section type."""


class ComponentRegistry:
    """Maps section types to section components."""

    def __init__(self, *, allow_replacement: bool = False) -> None:
        self._allow_replacement = allow_replacement
        self._components: dict[str, SectionComponent] = {}
        self._lock = threading.RLock()

    # ── Registration lifecycle ─────────────────────────────────────────────────

    def register(
        self,
        component: SectionComponent,
        *,
        allow_replacement: bool | None = None,
    ) -> None:
        """Register ``component`` under its section type.

        Rejects non-component objects, components without usable metadata, and
        duplicate section types unless replacement is allowed (registry default
        or per-call override).
        """
        if not isinstance(component, SectionComponent):
            raise ComponentRegistrationError(f"component must be a SectionComponent, got {type(component).__name__}")

        try:
            section_type = component.section_type()
            metadata = component.metadata()
        except Exception as exc:  # noqa: BLE001 - surface any broken component
            raise ComponentRegistrationError(f"invalid component: {exc}") from exc

        if not section_type:
            raise ComponentRegistrationError("component must declare a non-empty section type")
        if metadata.section_type != section_type:
            raise ComponentRegistrationError(
                f"component section_type '{section_type}' does not match "
                f"metadata.section_type '{metadata.section_type}'"
            )

        effective = self._allow_replacement if allow_replacement is None else allow_replacement
        with self._lock:
            if section_type in self._components and not effective:
                raise ComponentRegistrationError(f"section type '{section_type}' is already registered")
            self._components[section_type] = component

    def unregister(self, section_type: str) -> SectionComponent | None:
        """Remove and return the component for ``section_type``, or ``None``."""
        with self._lock:
            return self._components.pop(section_type, None)

    # ── Lookup ─────────────────────────────────────────────────────────────────

    def resolve(self, section_type: str) -> SectionComponent:
        """Return the component for ``section_type``; raise on miss."""
        with self._lock:
            component = self._components.get(section_type)
        if component is None:
            raise ComponentLookupError(f"no component registered for section type '{section_type}'")
        return component

    def get(self, section_type: str) -> SectionComponent | None:
        """Return the component for ``section_type`` or ``None``."""
        with self._lock:
            return self._components.get(section_type)

    def has(self, section_type: str) -> bool:
        """Return True when ``section_type`` is registered."""
        with self._lock:
            return section_type in self._components

    # ── Listing & metadata ─────────────────────────────────────────────────────

    def list(self) -> tuple[str, ...]:
        """Return registered section types in registration order."""
        with self._lock:
            return tuple(self._components.keys())

    def components(self) -> tuple[SectionComponent, ...]:
        """Return registered components in registration order (immutable)."""
        with self._lock:
            return tuple(self._components.values())

    def metadata_map(self) -> Mapping[str, ComponentMetadata]:
        """Return an immutable section-type → metadata mapping."""
        with self._lock:
            return MappingProxyType({key: component.metadata() for key, component in self._components.items()})

    def __len__(self) -> int:
        with self._lock:
            return len(self._components)

    def __iter__(self):
        with self._lock:
            return iter(tuple(self._components.keys()))

    def __contains__(self, section_type: object) -> bool:
        return isinstance(section_type, str) and self.has(section_type)
