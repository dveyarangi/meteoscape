"""The Manifold algebra and its materialized leaf.

`Manifold.project` is the single, closed, logically read-only operation. `Countable` and `Writable`
are capabilities (interface segregation), never a type hierarchy. `Coverage` is the materialized-leaf
*contract* (`Manifold ∧ Countable ∧ ranges`); it lives here with the algebra because `Writable`
consumes it and `Coverage <: Manifold`, which keeps the algebra acyclic. Its concrete realizations
are in `coverage.py`. The retention layer that composes these capabilities (`Store`, `Reservoir`) are
concrete nodes - they only *use* the algebra (one direction, no cycle) and so live in `nodes/`.

Everything here is an interface (bar the `Selection` value type); behaviour and the concrete data
backing are deferred to the slices that build each node and to `coverage.py`. This module fixes only
the contracts - the `Selection` request input, the enumerable `domain` seam, and the
`enumerate()`-positional `Coverage` that serialization binds to.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .domain import Domain, EnumerableDomain
from .parameters.data import ParameterData
from .parameters.vocabulary import ParameterId


@dataclass(frozen=True)
class Selection:
    """The one request type the algebra consumes - `project`'s input, dual to the `Coverage` it
    returns. `Selection = Domain + parameters`; the Domain's **shape** (Continuous / Snapped /
    Enumerable) *is* the mode, so there is no separate `mode` field that could disagree with it
    (ADR-0002).
    """

    domain: Domain
    parameters: frozenset[ParameterId]


@runtime_checkable
class Manifold(Protocol):
    """A projectable space with one closed operation. Returns a field/view until sampled."""

    def project(self, selection: Selection) -> Manifold: ...


@runtime_checkable
class Countable(Protocol):
    """Capability: the node/result exposes an enumerable (discrete) coordinate `domain`.

    Discrete-vs-continuous only - nothing about writing. Geometry enumeration and index access live on
    the `EnumerableDomain` itself (`domain.enumerate()`, `domain[i]`, `len(domain)`); a *node* uses its
    domain as the canonical lattice (the `quantize`/retention target), a *result* `Coverage` exposes
    the domain it was sampled onto.
    """

    @property
    def domain(self) -> EnumerableDomain: ...


@runtime_checkable
class Writable(Protocol):
    """Capability: the materialization boundary - sample a view onto the node grid and store it."""

    def assimilate(self, coverage: Coverage) -> None: ...


@runtime_checkable
class Coverage(Manifold, Countable, Protocol):
    """The materialized leaf: a field sampled onto an enumerable `domain`, one `ParameterData` range
    per parameter (positional to `domain`). The shape-agnostic exchange unit and itself a Manifold -
    `Coverage = Manifold ∧ Countable ∧ ranges`. Mirrors CoverageJSON's `domain` + `parameters` +
    `ranges`. Realizations (`Timeline`, v1) choose the value backing (dense now; numpy/xarray later)
    behind this contract, in `coverage.py`.

    Two orthogonal read axes, each a member object indexed by its own key: positions by the shared
    geometric index `i` of `domain` (`domain[i]` / `domain.enumerate()`); values by `ParameterId`
    through `ranges` (`ranges[pid]`, a keyed map - never an ordinal; iterate or `.keys()` it for the
    parameter set). They align as `ranges[pid].values[i]` identically across every parameter. `domain`
    (from `Countable`) and `project` (from `Manifold`) complete the surface. CoverageJSON's `parameters`
    descriptor block is recovered at the edge by joining the `ParameterTable` on these keys.
    """

    @property
    def ranges(self) -> Mapping[ParameterId, ParameterData]: ...
