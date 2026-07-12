"""`Weaver` - the build-time graph constructor.

`weave(ProfileDef)` allocates every `Store`, builds Source `Reservoir`s, and hands the source map +
`SourceRegistry` to the `Arbiter` (reconciler policy stays on the Arbiter). Takes plain values by
injection, never the `config.py` `Settings` type. See architecture.md ("Config, binders, Weaver") and
ADR-0005 / ADR-0004.
"""

from __future__ import annotations

from ..config import StoreSpec
from ..manifold.core import Countable, Manifold
from ..manifold.domain import EnumerableDomain
from .arbiter import Arbiter
from .composition import ProfileDef, RegisteredSource
from .reservoir import Reservoir
from .store import StoreFactory


def _source_grid(registered: RegisteredSource) -> EnumerableDomain | StoreSpec:
    """Provider-exact domain when Countable; otherwise the Source `StoreSpec` knobs."""
    if registered.store is None:
        assert isinstance(registered.provider, Countable)
        return registered.provider.domain
    return registered.store


class Weaver:
    def __init__(self, stores: StoreFactory) -> None:
        self.stores = stores

    def weave(self, profile: ProfileDef) -> Manifold:
        """Wire Sources → Arbiter → best-view Reservoir (Calculator graph → issue 002b)."""
        if profile.calculators.calculators:
            raise NotImplementedError("Calculator graph weave lands with issue 002b")

        sources = {
            key: Reservoir(self.stores.create(_source_grid(registered)), registered.provider)
            for key, registered in profile.sources.sources.items()
        }
        return Reservoir(
            self.stores.create(profile.root_store),
            Arbiter(sources, profile.sources, profile.arbiter),
        )
