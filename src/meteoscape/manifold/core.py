"""The Manifold algebra and its materialized leaf.

`project` is the single closed, read-only operation; `Countable` and `Writable` are optional facets,
never a type hierarchy. The `Coverage` *contract* lives here (its realizations live in `coverage.py`)
because `Writable` consumes it and `Coverage <: Manifold` - co-locating it with the algebra keeps the
dependency acyclic. Everything here is an interface bar the `Selection` value type.

See architecture.md ("Core concepts") and ADR-0001.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ..catalog.vocabulary import ParameterId
from .capability import Capability
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


@runtime_checkable
class Manifold(Protocol):
    """A projectable space with one closed operation. Returns a field/view until sampled."""

    def project(self, selection: Selection) -> Manifold: ...


@runtime_checkable
class Countable(Protocol):
    """Facet: exposes an enumerable coordinate `domain` (discrete-vs-continuous only, nothing about
    writing).

    A *node* uses its `domain` as the canonical lattice (the `quantize` / retention target); a *result*
    `Coverage` exposes the domain it was sampled onto. Enumeration and index access live on the
    `EnumerableDomain` itself.
    """

    @property
    def domain(self) -> EnumerableDomain: ...


@runtime_checkable
class Writable(Protocol):
    """Facet: the materialization boundary - sample a view onto the node grid and store it."""

    def assimilate(self, coverage: Coverage) -> None: ...


@runtime_checkable
class Coverage(Manifold, Countable, Protocol):
    """A Manifold sampled onto its enumerable `domain` - the shape-agnostic exchange unit.

    `capability` is the sole carrier of the parameter set (its `ParameterDef`s) and the `Domain` they
    sit on - there is no separate `parameters` map; a Coverage's capability is co-domained (every
    parameter on the one sampled `domain`). Invariant: `capability`, `ranges`, and `provenance` share
    one parameter key set and align positionally over `domain` - `ranges[pid].values[i]` is parameter
    `pid` at the domain's i-th point (ADR-0002 / ADR-0003).
    """

    @property
    def ranges(self) -> Mapping[ParameterId, ParameterData]: ...

    @property
    def provenance(self) -> ProvenanceField: ...

    @property
    def capability(self) -> Capability: ...
