"""`Source` - a `Reservoir(store, Provider)` exposing one provider's data.

Declares its `Capability` to the Arbiter. Asks its Provider store-shaped, so its `assimilate` stores
as identity (no resampling, no stamping). See architecture.md ("Source").
"""

from __future__ import annotations

from ..manifold.capability import Capability
from ..manifold.core import Manifold, Selection
from .providers.base import Provider
from .reservoir import Store


class Source:
    def __init__(self, store: Store, provider: Provider, capability: Capability) -> None:
        self.store = store
        self.provider = provider
        self.capability = capability

    def project(self, selection: Selection) -> Manifold:
        raise NotImplementedError
