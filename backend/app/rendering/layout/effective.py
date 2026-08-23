"""Shared effective-layout resolution for preview and export.

Single source of truth for the layout precedence:

    request-explicit layout_config
        > auto_balance=True
        > persisted layout_config
        > base layout

Both the preview API and the export service delegate here so that preview and
export always select the identical effective :class:`LayoutDefinition` and the
same effective :class:`LayoutConfig` (which carries ``density`` for HTML/PDF).
The frozen P3.6/P3.7 components (``LayoutBalancer``, ``apply_layout_balancer_result``,
``LayoutResolver``) are used directly — no logic is duplicated here.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.rendering.content import ContentView
from app.rendering.content_analyzer import ContentAnalyzer
from app.rendering.layout.layout_balancer import LayoutBalancer, LayoutBalanceResult
from app.rendering.layout.layout_config import LayoutConfig
from app.rendering.layout.layout_definition import LayoutDefinition
from app.rendering.layout.layout_mutator import apply_layout_balancer_result
from app.rendering.layout.layout_resolver import LayoutResolver, LayoutResolverError

logger = get_logger(__name__)


def resolve_effective_layout(
    base_layout: LayoutDefinition,
    cvm: ContentView,
    *,
    explicit_config: LayoutConfig | None = None,
    auto_balance: bool = False,
    base_config: LayoutConfig | None = None,
    return_balance_result: bool = False,
) -> tuple[LayoutDefinition, LayoutConfig | None] | tuple[LayoutDefinition, LayoutConfig | None, LayoutBalanceResult | None]:
    """Resolve the effective layout for a request.

    Returns ``(LayoutDefinition, effective LayoutConfig | None)``. The effective
    config carries the ``density`` used by HTML/PDF renderers; it is ``None``
    when the base layout is used unchanged (matching DOCX behavior).

    Precedence:
      * ``explicit_config`` is authoritative and resolved via ``LayoutResolver``;
        the balancer does NOT run. Resolver errors propagate (explicit intent).
      * ``auto_balance`` (with no explicit config) runs
        ContentAnalyzer -> LayoutBalancer -> LayoutMutator. The persisted
        ``base_config`` seeds ``density``/``gap``/``sections`` so user preferences
        survive while the balancer still decides ``mode``/``ratio``/``sidebar``.
        Any failure falls back to the base layout safely.
      * otherwise ``base_config`` (the persisted configuration) is the effective
        config; the base layout is used unchanged when none is present.

    When ``return_balance_result`` is True the tuple carries a third element:
    the ``LayoutBalanceResult`` produced during balancing (or ``None`` when no
    balancing occurred / it fell back). This lets callers surface the
    deterministic rationale without running the balancer a second time.
    """
    balance_result: LayoutBalanceResult | None = None

    if explicit_config is not None:
        # Explicit request configuration wins; resolver errors must surface.
        layout = LayoutResolver().resolve(base_layout, explicit_config)
        result: tuple[LayoutDefinition, LayoutConfig | None] = (layout, explicit_config)
    elif auto_balance:
        # Auto-balance: content-aware recommendation seeded with persisted prefs.
        try:
            analysis = ContentAnalyzer().analyze(cvm)
            balance_result = LayoutBalancer().balance(analysis, base_layout, base_config=base_config)
            layout = apply_layout_balancer_result(balance_result, base_layout, base_config=base_config)
            result = (layout, balance_result.config)
        except LayoutResolverError:
            # Expected: recommendation cannot be resolved (e.g. two-column on a
            # single-column-only base). Fall back to base layout silently.
            balance_result = None
            result = (base_layout, None)
        except Exception as e:
            logger.warning(
                "Auto-balance failed unexpectedly, falling back to base layout",
                layout_id=base_layout.layout_id,
                error=str(e),
                exc_info=True,
            )
            balance_result = None
            result = (base_layout, None)
    else:
        # No explicit config, no auto-balance: persisted config (if any) applies.
        if base_config is not None:
            layout = LayoutResolver().resolve(base_layout, base_config)
            result = (layout, base_config)
        else:
            result = (base_layout, None)

    if return_balance_result:
        return (result[0], result[1], balance_result)
    return result
