"""Layout mutator — apply a P3.6 LayoutBalancer recommendation to a base layout.

Responsibilities
----------------
* Consume a ``LayoutBalanceResult`` and a base ``LayoutDefinition``.
* Apply only the P3.6‑owned recommendation fields ``mode``, ``ratio``, ``sidebar``.
* Preserve ``density``, ``gap``, and ``sections`` from an optional ``base_config``.
* Re‑validate the resulting configuration through the existing ``LayoutResolver``.
* Fall back to the original ``base_layout`` when the recommendation cannot be safely resolved.
* Never mutate input objects; return a new immutable ``LayoutDefinition``.
"""

from __future__ import annotations

from app.rendering.layout.layout_balancer import LayoutBalanceResult
from app.rendering.layout.layout_config import LayoutConfig
from app.rendering.layout.layout_definition import LayoutDefinition
from app.rendering.layout.layout_resolver import LayoutResolver, LayoutResolverError


def apply_layout_balancer_result(
    result: LayoutBalanceResult,
    base_layout: LayoutDefinition,
    *,
    base_config: LayoutConfig | None = None,
) -> LayoutDefinition:
    """Apply a ``LayoutBalancer`` recommendation to a base layout.

    The recommendation fields ``mode``, ``ratio``, and ``sidebar`` are taken from
    ``result.config``.  ``density``, ``gap``, and ``sections`` are preserved from
    ``base_config`` when supplied; otherwise the ``LayoutConfig`` defaults are used.

    If ``LayoutResolver.resolve`` raises ``LayoutResolverError`` the original
    ``base_layout`` is returned unchanged — the mutation is **safe by default**.

    Parameters
    ----------
    result:
        The ``LayoutBalanceResult`` produced by ``LayoutBalancer.balance``.
    base_layout:
        The base layout definition to which the recommendation is applied.
    base_config:
        Optional per‑resume configuration that supplies ``density``, ``gap``,
        and ``sections``.  When ``None`` the ``LayoutConfig`` defaults are used.

    Returns
    -------
    LayoutDefinition
        The resolved layout definition reflecting the recommendation, or the
        original ``base_layout`` if the recommendation could not be resolved.
    """
    # Seed a LayoutConfig with the base config's persistent preferences.
    seed = LayoutConfig(
        density=base_config.density if base_config else LayoutConfig().density,
        gap=base_config.gap if base_config else LayoutConfig().gap,
        sections=base_config.sections if base_config else {},
    )

    # Apply only the P3.6 recommendation fields; everything else (density, gap,
    # sections) stays as seeded from ``base_config``.
    config = seed.model_copy(
        update={
            "mode": result.config.mode,
            "ratio": result.config.ratio,
            "sidebar": result.config.sidebar,
        }
    )

    # Try to resolve; on failure return the base layout unchanged.
    try:
        return LayoutResolver().resolve(base_layout, config)
    except LayoutResolverError:
        return base_layout
