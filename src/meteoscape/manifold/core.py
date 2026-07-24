"""The Manifold algebra and its materialized leaf.

`project` is the single closed, read-only operation; `Countable` and `Writable` are optional facets,
never a type hierarchy. The `Coverage` *contract* lives here (its realizations live in `coverage.py`)
because `Writable` consumes it and `Coverage <: Manifold` - co-locating it with the algebra keeps the
dependency acyclic. Everything here is an interface bar the `Selection` value type.

See architecture.md ("Core concepts") and ADR-0001.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Protocol, runtime_checkable

from ..parameters import ParameterId
from .capability import Capability, EnumerableCapability
from .data import ParameterData
from .domain import Domain, EnumerableDomain
from .provenance import ProvenanceField


@dataclass(frozen=True)
class Selection:
    """`project`'s input: a `Domain` + the parameters to sample.

    Invariant: the Domain's shape (Continuous / Snapped / Enumerable) *is* the mode, so there is no
    separate `mode` field that could disagree with it (ADR-0002).
    """

    domain: Domain
    parameters: frozenset[ParameterId]

    def with_params(self, parameters: frozenset[ParameterId]) -> Selection:
        """Same domain, rewritten parameter set. `parameters` must be ⊆ `self.parameters`."""
        extras = parameters - self.parameters
        if extras:
            raise ValueError(f"parameters not in selection: {sorted(extras)}")
        return replace(self, parameters=parameters)


@runtime_checkable
class Manifold(Protocol):
    """A projectable space with two duals: `project` *consumes* a `Selection`; `capability`
    *advertises* which Selections it can serve.

    Every Manifold exposes both - a leaf declares its capability, a composite derives it from its
    children, a realized `Coverage` exposes its content. `project` returns a field/view until sampled.
    """

    async def project(self, selection: Selection) -> Manifold: ...

    @property
    def capability(self) -> Capability: ...


@runtime_checkable
class Countable(Protocol):
    """Facet: exposes an enumerable coordinate `domain` (discrete-vs-continuous only, nothing about
    writing).

    A *result* `Coverage` exposes the domain it was sampled onto. Enumeration and index access live on
    the `EnumerableDomain` itself.
    """

    @property
    def domain(self) -> EnumerableDomain: ...


@runtime_checkable
class Writable(Protocol):
    """Facet: the materialization boundary - sample a view onto the node grid and store it."""

    async def assimilate(self, coverage: Coverage) -> None: ...


@runtime_checkable
class Coverage(Manifold, Countable, Protocol):
    """A Manifold sampled onto its enumerable `domain` - the shape-agnostic exchange unit.

    Its `capability` narrows to the co-domained `EnumerableCapability` - every parameter on the one
    sampled `domain` (which *is* the `Countable.domain`, derived from `capability.domain`, not a second
    copy). Invariant: `capability`, `ranges`, and `provenance` share one parameter key set and align
    positionally over `domain` - `ranges[pid].values[i]` is parameter `pid` at the domain's i-th point
    (ADR-0002 / ADR-0003).
    """

    @property
    def capability(self) -> EnumerableCapability: ...

    @property
    def ranges(self) -> Mapping[ParameterId, ParameterData]: ...

    @property
    def provenance(self) -> ProvenanceField: ...
