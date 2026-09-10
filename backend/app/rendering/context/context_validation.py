"""RenderContext compatibility validation.

Validates only invariants that belong to the resolved context: that the
supplied combination of layout, theme, content reference, and target engine
version is acceptable. The declarative models remain responsible for their own
validation (LayoutDefinition, ThemePalette, ContentReference, RenderState).

This module deliberately avoids importing ``RenderContext`` to keep the
dependency direction acyclic: ``render_context`` calls into here.
"""

from __future__ import annotations

from typing import Any

from app.rendering.layout.layout_definition import LayoutDefinition
from app.rendering.theme.theme_palette import ThemePalette

#: A semantic version expressed as (major, minor, patch) — the established
#: registry convention, reused here without a new version system.
SemanticVersion = tuple[int, int, int]


class ContextValidationError(ValueError):
    """Raised when a resolved render context is not acceptable."""


def _as_tuple(version: Any) -> tuple[int, int, int]:
    return (version.major, version.minor, version.patch)


def validate_resolved_context(
    *,
    layout: LayoutDefinition,
    theme: ThemePalette,
    content_ref: Any,
    engine_version: SemanticVersion | None,
) -> None:
    """Validate a resolved context; raise :class:`ContextValidationError`.

    Engine/API compatibility is enforced by the registries at registration;
    this only re-checks the *combination* supplied to the context.
    """
    if layout is None or theme is None:
        raise ContextValidationError("layout and theme are required")

    if engine_version is not None:
        if (
            not isinstance(engine_version, tuple)
            or len(engine_version) != 3
            or not all(isinstance(part, int) and part >= 0 for part in engine_version)
        ):
            raise ContextValidationError(
                f"engine_version must be a (major, minor, patch) tuple, got {engine_version!r}"
            )
        layout_required = _as_tuple(layout.metadata.engine_version)
        theme_required = _as_tuple(theme.metadata.engine_version)
        if layout_required > engine_version:
            raise ContextValidationError(
                f"layout '{layout.stable_id}' requires engine {layout_required} "
                f"but the context targets {engine_version}"
            )
        if theme_required > engine_version:
            raise ContextValidationError(
                f"theme '{theme.stable_id}' requires engine {theme_required} but the context targets {engine_version}"
            )

    if content_ref is not None and not content_ref.stable_id:
        raise ContextValidationError("content reference must declare a stable id")
