"""`Store` and `Reservoir` - the retention layer.

`Store` is the only Writable, Countable Manifold (the sole `assimilate` target); `Reservoir` is the
generic retention composite (`Store` + one child) that adds retention, not selection. See
architecture.md ("Reservoir", "Store") and ADR-0001.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..manifold.core import Countable, Manifold, Selection, Writable
from ..manifold.domain import EnumerableDomain


@runtime_checkable
class Store(Manifold, Countable, Writable, Protocol):
    """The substrate a `Reservoir` owns: a Writable, Countable Manifold leaf.

    Holds sampled Coverages on its declared `domain` in whole assimilable units (a unit is replaced
    atomically, so it carries one origin); the only `assimilate` target.
    """


class Reservoir:
    """A read-only Manifold composed of a `Store` + one child (Source / best view).

    Node-`Countable` *by delegation* to its `Store` (it forwards `domain`, it does not inherit it), so
    it structurally satisfies `Countable` without an inheritance tie. Adds retention, not selection.
    """

    def __init__(self, store: Store, child: Manifold) -> None:
        self.store = store
        self.child = child

    def project(self, selection: Selection) -> Manifold:
        raise NotImplementedError

    @property
    def domain(self) -> EnumerableDomain:
        return self.store.domain
