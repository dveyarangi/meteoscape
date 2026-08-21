"""`Capability` - what a Manifold can serve: the dual of `project`.

`project` *consumes* a `Selection`; a `Capability` *advertises* which Selections are servable, through
four members - `serves(parameter, requested)` (the admission predicate the Arbiter folds over),
`parameters` (the served `ParameterDef`s), `reach(parameter)` (the `Domain` served for it, a
Manifold's Reach), and `origins(parameter)` (declared provenance over that reach, empty when
nothing is declared). `parameters` is the sole membership authority: `p in parameters` ⟺ `reach(p)`
answers (ADR-0007). `origins` raises for an unserved parameter, matching `reach`; `serves` alone
answers softly.

The forms below mirror the Manifold algebra (a leaf declares, a composite derives), so capability
composes bottom-up like `project` - unioning parameter sets, AND/OR-ing the predicate, and carrying
the per-parameter reach its composing node folded (the reconciler's dominance up a union, the
`Calculator` node's contained-in-all). A composed Reach is always some producer's own `Domain`, never
a synthesised one, so a clock-anchored `RollingAxis` stays live; the rules and their
`CompositionError`s live with the composing nodes, these forms carry results. The composition and
matching rules are in ADR-0004 / ADR-0007; the resampler-reachability step inside `serves` and
*probed* real availability stay deferred seams.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ..identity import ProducerKey
from ..parameters import ParameterDef, ParameterId
from .domain import Domain, EnumerableDomain
from .provenance import AtomicOrigin


@runtime_checkable
class Capability(Protocol):
    """What a Manifold serves: an admission predicate, the served parameter set, the per-parameter
    `Domain` it reaches, and declared provenance over that reach."""

    def serves(self, parameter: ParameterId, requested: Domain) -> bool: ...

    def reach(self, parameter: ParameterId) -> Domain:
        """The `Domain` served for `parameter` — a Manifold's Reach; raises for an unserved one.

        `parameters` stays the sole membership authority: `p in parameters` ⟺ `reach(p)` answers
        (ADR-0007).
        """
        ...

    def origins(self, parameter: ParameterId) -> Sequence[tuple[Domain, AtomicOrigin]]:
        """Declared provenance over the reach: each entry pairs a sub-domain with the origin
        that would serve it. Empty = nothing declared. An unserved parameter raises KeyError,
        mirroring `reach` — both read the declaration; `serves` alone answers softly.
        """
        ...

    @property
    def parameters(self) -> Mapping[ParameterId, ParameterDef]: ...


@dataclass(frozen=True)
class GranularCapability:
    """An own-geometry capability with one independently shaped `Domain` per parameter.

    Providers use it for declared footprints; multi-domain carriers and retentive stores use it for
    held records. Granular **in parameter only** - ADR-0006's Holding granularity is finer (parameter
    *and* cells); the shared word names the same co-domained-vs-per-parameter axis, not the same
    partition.

    Reaches stay typed as general `Domain`s because no caller consumes a narrower type: a carrier's
    happen to be enumerable, but only `EnumerableCapability` *states* enumerability, where its own
    single grid backs the claim (ADR-0007). `declared_origins` is the declaration side of provenance
    (ADR-0003); absent, `origins` answers empty for every served parameter.
    """

    reaches: Mapping[ParameterId, tuple[ParameterDef, Domain]]
    declared_origins: Mapping[ParameterId, Sequence[tuple[Domain, AtomicOrigin]]] | None = None

    @property
    def parameters(self) -> Mapping[ParameterId, ParameterDef]:
        return {pid: definition for pid, (definition, _) in self.reaches.items()}

    def serves(self, parameter: ParameterId, requested: Domain) -> bool:
        entry = self.reaches.get(parameter)
        # v1: geometric matches. Resampler-reachability (via the ParameterDef) is a seam (ADR-0004).
        return entry is not None and entry[1].matches(requested)

    def reach(self, parameter: ParameterId) -> Domain:
        entry = self.reaches.get(parameter)
        if entry is None:
            raise KeyError(f"{parameter!r} is not served")
        return entry[1]

    def origins(self, parameter: ParameterId) -> Sequence[tuple[Domain, AtomicOrigin]]:
        if parameter not in self.reaches:
            raise KeyError(f"{parameter!r} is not served")
        if self.declared_origins is None:
            return ()
        return self.declared_origins.get(parameter, ())


@dataclass(frozen=True)
class EnumerableCapability:
    """The materialized, co-domained leaf a `Coverage` exposes: every parameter on one enumerable
    `domain`, which is the Coverage's positional grid (its `Countable.domain` derives from here).
    `origins` is empty until a materialized producer declares.
    """

    domain: EnumerableDomain
    parameters: Mapping[ParameterId, ParameterDef]

    def serves(self, parameter: ParameterId, requested: Domain) -> bool:
        return parameter in self.parameters and self.domain.matches(requested)

    def reach(self, parameter: ParameterId) -> EnumerableDomain:
        # One shared grid, so the return type can state enumerability - a claim about this form,
        # not a narrowing any caller consumes today (ADR-0007).
        if parameter not in self.parameters:
            raise KeyError(f"{parameter!r} is not served")
        return self.domain

    def origins(self, parameter: ParameterId) -> Sequence[tuple[Domain, AtomicOrigin]]:
        if parameter not in self.parameters:
            raise KeyError(f"{parameter!r} is not served")
        return ()


@dataclass(frozen=True)
class UnionCapability:
    """An `Arbiter`'s capability: serves a parameter iff *some* member does, over the reach the
    reconciler composed for it (the admission half of the per-parameter fold; the reconciler decides
    *which* member at `project`).

    `domains` is both the composed per-parameter reach and the **membership authority** - `parameters`
    reads its keys, so a scoped Arbiter declares exactly what it composed, never a member's out-of-scope
    parameter.

    `serves` delegates to the members rather than reading `domains`: that is what leaves a member free
    to tighten below its declared geometry, so this never collapses into the per-parameter form
    (ADR-0007 rejects deriving `serves` from `reach`).

    Construction precondition: `domains.keys()` is a subset of the members' combined parameters - the
    Arbiter satisfies it by composing `domains` *from* the members it holds; hand-built instances must
    honour it.

    `origins` concatenates members' declarations in bind order, skipping who does not serve the
    parameter.
    """

    # TODO: Replace the unused keys with a collection; see concern #46.
    members: Mapping[ProducerKey, Capability]
    domains: Mapping[ParameterId, Domain]

    @property
    def parameters(self) -> Mapping[ParameterId, ParameterDef]:
        merged = {pid: d for m in self.members.values() for pid, d in m.parameters.items()}
        return {pid: merged[pid] for pid in self.domains}

    def serves(self, parameter: ParameterId, requested: Domain) -> bool:
        return parameter in self.domains and any(
            m.serves(parameter, requested) for m in self.members.values()
        )

    def reach(self, parameter: ParameterId) -> Domain:
        if parameter not in self.domains:
            raise KeyError(f"{parameter!r} is not served")
        return self.domains[parameter]

    def origins(self, parameter: ParameterId) -> Sequence[tuple[Domain, AtomicOrigin]]:
        if parameter not in self.domains:
            raise KeyError(f"{parameter!r} is not served")
        declared: list[tuple[Domain, AtomicOrigin]] = []
        for member in self.members.values():
            if parameter not in member.parameters:
                continue
            declared.extend(member.origins(parameter))
        return tuple(declared)


@dataclass(frozen=True)
class DerivedCapability:
    """A `Calculator`'s capability: serves each co-produced parameter iff *all* inputs are servable
    through the scoped resolver (its input Arbiter's capability).

    Every co-produced parameter shares one reach - `domain`, composed by the `Calculator` node
    (contained-in-all over its inputs' reaches, eager at construction). This form carries the
    composed result; the fold and its `CompositionError` are the node's (ADR-0007). Synthetic
    identity is minted at calculation, so `origins` is empty.
    """

    parameters: Mapping[ParameterId, ParameterDef]
    inputs: frozenset[ParameterId]
    upstream: Capability
    domain: Domain

    def serves(self, parameter: ParameterId, requested: Domain) -> bool:
        return parameter in self.parameters and all(
            self.upstream.serves(i, requested) for i in self.inputs
        )

    def reach(self, parameter: ParameterId) -> Domain:
        if parameter not in self.parameters:
            raise KeyError(f"{parameter!r} is not served")
        return self.domain

    def origins(self, parameter: ParameterId) -> Sequence[tuple[Domain, AtomicOrigin]]:
        if parameter not in self.parameters:
            raise KeyError(f"{parameter!r} is not served")
        return ()
