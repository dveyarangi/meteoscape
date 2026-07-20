"""`Store` substrate and its construction face.

`Store` is the only Writable, Countable Manifold (the sole `assimilate` target). The Weaver allocates
every store via an injected `StoreFactory` — it owns *where* stores exist; the factory owns *what* a
store is. See architecture.md ("Store") and ADR-0005.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol, runtime_checkable

from ..config import StoreSpec
from ..manifold.capability import Capability
from ..manifold.core import Countable, Coverage, Manifold, Selection, Writable
from ..manifold.domain import AxisName, EnumerableDomain, GridDomain, RegularAxis

# Structural Countable placeholder only — not a fidelity claim. A retentive Store will replace it.
_STUB_DOMAIN = GridDomain(
    axes={
        AxisName.X: RegularAxis(AxisName.X, 0.0, 1.0, 1, False),
        AxisName.Y: RegularAxis(AxisName.Y, 0.0, 1.0, 1, False),
        AxisName.Z: RegularAxis(AxisName.Z, 0.0, 1.0, 1, False),
        AxisName.T: RegularAxis(
            AxisName.T, datetime(1970, 1, 1, tzinfo=UTC), timedelta(hours=1), 1, False
        ),
    }
)


@runtime_checkable
class Store(Manifold, Countable, Writable, Protocol):
    """The substrate a `Reservoir` owns: a Writable, Countable Manifold leaf.

    Holds sampled Coverages on its declared `domain` in whole assimilable units (a unit is replaced
    atomically, so it carries one origin); the only `assimilate` target. Its `capability` is what it
    currently holds (an `EnumerableCapability` over the retained content), distinct from `domain` - the
    full grid lattice it *could* hold.
    """


class StubStore:
    """Non-retentive weave-time placeholder for the planned retentive Store.

    Exists so `Reservoir` can be constructed. `assimilate` is a no-op; `project` / `capability`
    raise until a retentive store replaces this. `domain` is a harmless dummy GridDomain
    (structural Countable only).
    """

    async def project(self, selection: Selection) -> Manifold:
        raise NotImplementedError

    @property
    def capability(self) -> Capability:
        raise NotImplementedError

    @property
    def domain(self) -> EnumerableDomain:
        return _STUB_DOMAIN

    async def assimilate(self, coverage: Coverage) -> None:
        return None


class StoreFactory:
    """Allocates interim `StubStore`s; a retentive factory will honor the construction grid."""

    def create(self, grid: EnumerableDomain | StoreSpec | None) -> Store:
        return StubStore()
