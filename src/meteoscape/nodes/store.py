"""`Store` substrate and its construction face.

`Store` is the only Writable Manifold leaf (the sole `assimilate` target). The Weaver allocates every
store via an injected `StoreFactory` — it owns *where* stores exist; the factory owns *what* a store
is. See architecture.md ("Store") and ADR-0005.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..config import StoreSpec
from ..manifold.capability import Capability
from ..manifold.core import Coverage, Manifold, Selection, Writable


@runtime_checkable
class Store(Manifold, Writable, Protocol):
    """The substrate a `Reservoir` owns: a Writable Manifold leaf.

    Holds sampled Coverages in whole assimilable units (a unit is replaced atomically, so it carries
    one origin); the only `assimilate` target. Its `capability` is what it currently holds. Its
    quantize/retention lattice is private — consumed internally, never exposed as a node `domain`.
    """


class StubStore:
    """Non-retentive weave-time placeholder for the planned retentive Store.

    Exists so `Reservoir` can be constructed. `assimilate` is a no-op; `project` / `capability` raise
    until a retentive store replaces this.
    """

    async def project(self, selection: Selection) -> Manifold:
        raise NotImplementedError

    @property
    def capability(self) -> Capability:
        raise NotImplementedError

    async def assimilate(self, coverage: Coverage) -> None:
        return None


class StoreFactory:
    """Allocates interim `StubStore`s; a retentive factory will honor the configured `StoreSpec`."""

    def create(self, spec: StoreSpec) -> Store:
        return StubStore()
