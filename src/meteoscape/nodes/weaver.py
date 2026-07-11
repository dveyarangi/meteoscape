"""`Weaver` - the build-time graph constructor.

`weave(ProfileDef)` wires the static DAG and allocates every `Store`, then steps out (absent from the
request path). `ProfileDef` (from `composition.py`) already holds symmetrical build products:
`SourceRegistry` + `DerivationRegistry` (catalog-resolved bindings, not Calculator instances). Takes
plain values by injection, never the `config.py` `Settings` type. See architecture.md ("Config,
binders, Weaver") and ADR-0005.
"""

from __future__ import annotations

from ..manifold.core import Manifold
from .composition import ProfileDef


class Weaver:
    def weave(self, profile: ProfileDef) -> Manifold:
        """Wire the static DAG from `profile`: Sources → Calculators → Arbiter → best-view Reservoir."""
        raise NotImplementedError
