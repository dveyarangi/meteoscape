"""`Store` substrate and its construction face.

`Store` is the only Writable, Countable Manifold (the sole `assimilate` target). The Weaver allocates
every store via an injected `StoreFactory` — it owns *where* stores exist; the factory owns *what* a
store is. See architecture.md ("Store") and ADR-0005.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..manifold.capability import Capability
from ..manifold.core import Countable, Coverage, Manifold, Selection, Writable
from ..manifold.domain import EnumerableDomain


@runtime_checkable
class Store(Manifold, Countable, Writable, Protocol):
    """The substrate a `Reservoir` owns: a Writable, Countable Manifold leaf.

    Holds sampled Coverages on its declared `domain` in whole assimilable units (a unit is replaced
    atomically, so it carries one origin); the only `assimilate` target. Its `capability` is what it
    currently holds (an `EnumerableCapability` over the retained content), distinct from `domain` - the
    full grid lattice it *could* hold.
    """


class StubStore:
    """Weave-time placeholder — no retention, no lattice; real store lands at issue 006.

    Exists so `Reservoir` can be constructed. `assimilate` is a no-op; `project` / `capability` /
    `domain` raise until a retentive store replaces this.
    """

    async def project(self, selection: Selection) -> Manifold:
        raise NotImplementedError

    @property
    def capability(self) -> Capability:
        raise NotImplementedError

    @property
    def domain(self) -> EnumerableDomain:
        raise NotImplementedError("StubStore declares no lattice")

    async def assimilate(self, coverage: Coverage) -> None:
        return None


class StoreFactory:
    """Allocates interim `StubStore`s (ignores lattice). Retentive factory lands at issue 006."""

    def create(self, lattice: EnumerableDomain | None) -> Store:
        return StubStore()
