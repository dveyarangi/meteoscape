"""`Store` and `Reservoir` - the retention layer.

`Store` is the only Writable, Countable Manifold (the sole `assimilate` target); `Reservoir` is the
generic retention composite (`Store` + one child) that adds retention, not selection. Both are
concrete *nodes* - they only *use* the algebra capabilities (one direction, no cycle), so they live
here rather than in the algebra contract. Behaviour (quantize / serve-vs-refill / read-back
homogenization) is deferred to this slice's successors.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..manifold.core import Countable, Manifold, Selection, Writable
from ..manifold.domain import EnumerableDomain


@runtime_checkable
class Store(Manifold, Countable, Writable, Protocol):
    """The substrate a `Reservoir` owns: a Writable, Countable Manifold leaf.

    Holds sampled Coverages on its declared `domain` in whole assimilable units; the only assimilate
    target. The concrete in-memory retentive implementation is built in its own slice.
    """


class Reservoir:
    """A read-only Manifold composed of a `Store` + one child (Source / best view).

    Node-`Countable` *by delegation* to its `Store` (it forwards `domain`, it does not inherit it), so
    it structurally satisfies `Countable` without an inheritance tie. Adds retention, not selection;
    the serve-vs-refill + read-back-homogenization `project` is deferred.
    """

    def __init__(self, store: Store, child: Manifold) -> None:
        self.store = store
        self.child = child

    def project(self, selection: Selection) -> Manifold:
        raise NotImplementedError

    @property
    def domain(self) -> EnumerableDomain:
        return self.store.domain
