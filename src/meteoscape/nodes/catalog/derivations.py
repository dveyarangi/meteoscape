"""Derivation plugin catalogue: the formula plus its invocation constraints.

`DerivationCatalog` is `fn_id → DerivationManifest`. Each manifest is a cohesive plugin face — the
combine function alongside the declarative constraints on the shapes it may be invoked over. A
`DerivationSpec` (in `ProfileConfig`) only enables one against this catalogue. See ADR-0005.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

DerivationCatalog = Mapping[str, "DerivationManifest"]


@dataclass(frozen=True)
class DerivationManifest:
    """Cohesive derivation plugin face — formula plus declarative invocation constraints."""

    fn_id: str
    fn: Callable[..., object]
    # Constraint fields land with behavior; catalogue row stays settings, not data-flow.
