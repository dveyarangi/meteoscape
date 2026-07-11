"""`Reservoir` - the retention composite.

A read-only Manifold composed of a `Store` + one child. Adds retention, not selection. See
architecture.md ("Reservoir") and ADR-0001. The `Store` protocol and factories live in `store.py`.
"""

from __future__ import annotations

from ..manifold.capability import Capability
from ..manifold.core import Manifold, Selection
from ..manifold.domain import EnumerableDomain
from .store import Store


class Reservoir:
    """A read-only Manifold composed of a `Store` + one child - a Provider (the *source* role) or an
    Arbiter (the *best view*).

    Node-`Countable` *by delegation* to its `Store` (it forwards `domain`, it does not inherit it), so
    it structurally satisfies `Countable` without an inheritance tie. Adds retention, not selection, so
    its `capability` forwards the source's unchanged (the `Store` grid is an internal fidelity floor,
    not a capability boundary).
    """

    def __init__(self, store: Store, source: Manifold) -> None:
        self.store = store
        self.source = source

    async def project(self, selection: Selection) -> Manifold:
        raise NotImplementedError

    @property
    def domain(self) -> EnumerableDomain:
        return self.store.domain

    @property
    def capability(self) -> Capability:
        return self.source.capability
