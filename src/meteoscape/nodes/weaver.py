"""`Weaver` - the build-time graph constructor.

`weave(ProfileDef)` allocates every `Store`, builds Source `Reservoir`s, and hands the source map +
`SourceRegistry` to the `Arbiter` (reconciler policy stays on the Arbiter). Takes plain values by
injection, never the `config.py` `Settings` type. See architecture.md ("Config, binders, Weaver") and
ADR-0005 / ADR-0004.
"""

from __future__ import annotations

from ..manifold.core import Manifold
from .arbiter import Arbiter
from .composition import ProfileDef
from .reservoir import Reservoir
from .store import StoreFactory


class Weaver:
    def __init__(self, stores: StoreFactory) -> None:
        self.stores = stores

    def weave(self, profile: ProfileDef) -> Manifold:
        """Wire Sources → Arbiter → best-view Reservoir (Calculator graph → issue 002b)."""
        if profile.calculators.calculators:
            raise NotImplementedError("Calculator graph weave lands with issue 002b")

        sources = {
            key: Reservoir(self.stores.create(registered.source_lattice), registered.provider)
            for key, registered in profile.sources.sources.items()
        }
        return Reservoir(
            self.stores.create(None),
            Arbiter(sources, profile.sources, profile.arbiter),
        )
