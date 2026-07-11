"""Calculator plugin catalogue: the formula plus its invocation constraints.

`CalculatorCatalog` is `fn_id → CalculatorManifest`. Each manifest is a cohesive plugin face — the
combine function alongside the declarative constraints on the shapes it may be invoked over. A
`CalculatorSpec` (in `ProfileConfig`) only enables one against this catalogue. See ADR-0005.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

CalculatorCatalog = Mapping[str, "CalculatorManifest"]


@dataclass(frozen=True)
class CalculatorManifest:
    """Cohesive calculator plugin face — formula plus declarative invocation constraints."""

    fn_id: str
    fn: Callable[..., object]
    # Constraint fields land with behavior; catalogue row stays settings, not data-flow.
