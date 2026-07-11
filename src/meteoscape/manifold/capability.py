"""`Capability` - what a Manifold can serve: the dual of `project`.

`project` *consumes* a `Selection`; a `Capability` *advertises* which Selections are servable, through
two members - `serves(parameter, requested)` (the admission predicate the Arbiter folds over) and
`parameters` (the served `ParameterDef`s). A concrete `Domain` is deliberately kept **off** the
interface, living only where it is singular and exact: privately inside a leaf's `serves`, and publicly
as `EnumerableCapability.domain` on a materialized `Coverage`.

The forms below mirror the Manifold algebra (a leaf declares, a composite derives), so capability
composes bottom-up like `project` - unioning parameter sets and AND/OR-ing the predicate, never
synthesising a `Domain`. The composition and matching rules are in ADR-0004; the resampler-reachability
step inside `serves` and *probed* real availability stay deferred seams.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ..parameters import ParameterDef, ParameterId
from .domain import Domain, EnumerableDomain


@runtime_checkable
class Capability(Protocol):
    """What a Manifold serves: an admission predicate plus the served parameter set."""

    def serves(self, parameter: ParameterId, requested: Domain) -> bool: ...

    @property
    def parameters(self) -> Mapping[ParameterId, ParameterDef]: ...


@dataclass(frozen=True)
class FootprintCapability:
    """General leaf (a `Provider`'s declaration): per-parameter covered `Domain` footprint, kept private.

    A footprint interprets `serves` but is **not** on the `Capability` surface - only the materialized
    `EnumerableCapability` publishes a `domain`.
    """

    footprints: Mapping[ParameterId, tuple[ParameterDef, Domain]]

    @property
    def parameters(self) -> Mapping[ParameterId, ParameterDef]:
        return {pid: definition for pid, (definition, _) in self.footprints.items()}

    def serves(self, parameter: ParameterId, requested: Domain) -> bool:
        entry = self.footprints.get(parameter)
        # v1: geometric containment. Resampler-reachability (via the ParameterDef) is a seam (ADR-0004).
        return entry is not None and entry[1].contains(requested)


@dataclass(frozen=True)
class EnumerableCapability:
    """The materialized, co-domained leaf a `Coverage` exposes: every parameter on one enumerable
    `domain`, which is the Coverage's positional grid (its `Countable.domain` derives from here).
    """

    domain: EnumerableDomain
    parameters: Mapping[ParameterId, ParameterDef]

    def serves(self, parameter: ParameterId, requested: Domain) -> bool:
        return parameter in self.parameters and self.domain.contains(requested)


@dataclass(frozen=True)
class UnionCapability:
    """An `Arbiter`'s capability: the union of its members - serves a parameter iff *some* member does
    (the admission half of the per-parameter fold; the reconciler decides *which* member at `project`).

    Takes members flat: each `Capability` already carries its own `parameters`, so no per-parameter
    pre-indexing is needed, and `serves` self-filters. (Its future dual is an intersection/consensus
    fold - `serves` iff *all* members do - the capability of the deferred `consensus` reconcilers.)
    """

    members: Sequence[Capability]

    @property
    def parameters(self) -> Mapping[ParameterId, ParameterDef]:
        return {pid: definition for m in self.members for pid, definition in m.parameters.items()}

    def serves(self, parameter: ParameterId, requested: Domain) -> bool:
        return any(m.serves(parameter, requested) for m in self.members)


@dataclass(frozen=True)
class DerivedCapability:
    """A `Calculator`'s induced capability: serves its `output` iff *all* its inputs are servable
    through the scoped resolver (its input Arbiter's capability)."""

    output: ParameterDef
    inputs: frozenset[ParameterId]
    upstream: Capability

    @property
    def parameters(self) -> Mapping[ParameterId, ParameterDef]:
        return {self.output.id: self.output}

    def serves(self, parameter: ParameterId, requested: Domain) -> bool:
        return parameter == self.output.id and all(
            self.upstream.serves(i, requested) for i in self.inputs
        )
