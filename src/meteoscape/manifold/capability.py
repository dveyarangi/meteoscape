"""`Capability` - what a Manifold can serve: the dual of `project`.

`project` *consumes* a `Selection`; a `Capability` *advertises* which Selections are servable, through
three members - `serves(parameter, requested)` (the admission predicate the Arbiter folds over),
`parameters` (the served `ParameterDef`s), and `reach(parameter)` (the `Domain` served for it, a
Manifold's Reach). `parameters` is the sole membership authority: `p in parameters` ⟺ `reach(p)`
answers (ADR-0007).

The forms below mirror the Manifold algebra (a leaf declares, a composite derives), so capability
composes bottom-up like `project` - unioning parameter sets, AND/OR-ing the predicate, and folding the
per-parameter reach (dominance up a union, contained-in-all through a Calculator). A composed Reach is
always some producer's own `Domain`, never a synthesised one, so a clock-anchored `RollingAxis` stays
live. The composition and matching rules are in ADR-0004 / ADR-0007; the resampler-reachability step
inside `serves` and *probed* real availability stay deferred seams.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ..errors import CompositionError
from ..identity import CalculatorKey, ProducerKey
from ..parameters import ParameterDef, ParameterId
from .domain import (
    Domain,
    EnumerableDomain,
    Separable,
    as_separable,
    contains_extents,
    first_incomparable,
    split_extents,
)


@runtime_checkable
class Capability(Protocol):
    """What a Manifold serves: an admission predicate, the served parameter set, and the per-parameter
    `Domain` it reaches."""

    def serves(self, parameter: ParameterId, requested: Domain) -> bool: ...

    def reach(self, parameter: ParameterId) -> Domain:
        """The `Domain` served for `parameter` — a Manifold's Reach; raises for an unserved one.

        `parameters` stays the sole membership authority: `p in parameters` ⟺ `reach(p)` answers
        (ADR-0007).
        """
        ...

    @property
    def parameters(self) -> Mapping[ParameterId, ParameterDef]: ...


@dataclass(frozen=True)
class FootprintCapability:
    """General leaf (a `Provider`'s declaration): per-parameter covered `Domain` footprint.

    Each footprint is both the operand of that parameter's `serves` predicate and the `Domain` its
    `reach` returns. It is a general `Domain` (separable or curvilinear); only the materialized
    `EnumerableCapability` narrows its reach to an `EnumerableDomain`.
    """

    footprints: Mapping[ParameterId, tuple[ParameterDef, Domain]]

    @property
    def parameters(self) -> Mapping[ParameterId, ParameterDef]:
        return {pid: definition for pid, (definition, _) in self.footprints.items()}

    def serves(self, parameter: ParameterId, requested: Domain) -> bool:
        entry = self.footprints.get(parameter)
        # v1: geometric matches. Resampler-reachability (via the ParameterDef) is a seam (ADR-0004).
        return entry is not None and entry[1].matches(requested)

    def reach(self, parameter: ParameterId) -> Domain:
        entry = self.footprints.get(parameter)
        if entry is None:
            raise KeyError(f"{parameter!r} is not served")
        return entry[1]


@dataclass(frozen=True)
class EnumerableCapability:
    """The materialized, co-domained leaf a `Coverage` exposes: every parameter on one enumerable
    `domain`, which is the Coverage's positional grid (its `Countable.domain` derives from here).
    """

    domain: EnumerableDomain
    parameters: Mapping[ParameterId, ParameterDef]

    def serves(self, parameter: ParameterId, requested: Domain) -> bool:
        return parameter in self.parameters and self.domain.matches(requested)

    def reach(self, parameter: ParameterId) -> EnumerableDomain:
        # Narrows covariantly to EnumerableDomain: this form's one reach *is* enumerable, so the
        # type states "materialized ⇒ enumerable reach" rather than leaving it a runtime fact.
        if parameter not in self.parameters:
            raise KeyError(f"{parameter!r} is not served")
        return self.domain


@dataclass(frozen=True)
class UnionCapability:
    """An `Arbiter`'s capability: serves a parameter iff *some* member does, over the reach the
    reconciler composed for it (the admission half of the per-parameter fold; the reconciler decides
    *which* member at `project`).

    `domains` is both the composed per-parameter reach and the **membership authority** - `parameters`
    reads its keys, so a scoped Arbiter declares exactly what it composed, never a member's out-of-scope
    parameter. Members are keyed by `ProducerKey` for provenance and error attribution.

    Construction precondition: `domains.keys()` is a subset of the members' combined parameters - the
    Arbiter satisfies it by composing `domains` *from* the members it holds; hand-built instances must
    honour it.
    """

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


@dataclass(frozen=True)
class DerivedCapability:
    """A `Calculator`'s induced capability: serves each co-produced parameter iff *all* inputs are
    servable through the scoped resolver (its input Arbiter's capability).

    Every co-produced parameter shares one reach - the domain contained in all inputs' reaches, since a
    Calculator serves exactly where every input does. It is composed **eagerly at construction**, so a
    profile whose inputs shear (nest neither way) fails the build here, not at request.

    Carries its `CalculatorKey` so that a sheared-inputs failure names the calculator an operator must
    fix - the mirror of a composite carrying its members' `ProducerKey`s (ADR-0007).
    """

    key: CalculatorKey
    parameters: Mapping[ParameterId, ParameterDef]
    inputs: frozenset[ParameterId]
    upstream: Capability
    _reach: Domain = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_reach", _contained_in_all(self.key, self.inputs, self.upstream))

    def serves(self, parameter: ParameterId, requested: Domain) -> bool:
        return parameter in self.parameters and all(
            self.upstream.serves(i, requested) for i in self.inputs
        )

    def reach(self, parameter: ParameterId) -> Domain:
        if parameter not in self.parameters:
            raise KeyError(f"{parameter!r} is not served")
        return self._reach


def _contained_in_all(
    calculator: CalculatorKey, inputs: frozenset[ParameterId], upstream: Capability
) -> Domain:
    """The input reach contained in every other - a Calculator serves exactly where all inputs do.

    The reconciler's dominance fold inverted (the minimum, not the maximum); it returns an input's own
    `Domain`, never a synthesized one, so a `RollingAxis` stays live. Sheared inputs (nesting neither
    way) or a non-separable multi-input set raise a build-time `CompositionError` naming the calculator
    and its inputs - the sole author of that message (ADR-0007).
    """
    candidates = [(i, upstream.reach(i)) for i in inputs]
    if not candidates:
        raise CompositionError(f"calculator {calculator} has no inputs to resolve reach from")
    if len(candidates) == 1:
        return candidates[0][1]

    checked = [(key, _require_separable(calculator, key, domain)) for key, domain in candidates]
    for index, (_key, domain) in enumerate(checked):
        if all(contains_extents(other, domain) for _k, other in checked):
            return candidates[index][1]

    witness = first_incomparable(checked)
    # Containment is transitive: no minimum ⇒ some pair nests neither way.
    assert witness is not None
    (left_key, left), (right_key, right) = witness
    raise CompositionError(
        f"sheared calculator input reaches for {calculator}: "
        f"{split_extents(left_key, left, right_key, right)}; inputs {_names(candidates)}"
    )


def _require_separable(calculator: CalculatorKey, key: ParameterId, domain: Domain) -> Separable:
    """Separability is the precondition of comparing per axis; author the message with the input."""
    separable = as_separable(domain)
    if separable is None:
        raise CompositionError(
            f"calculator {calculator} reach requires separable geometry; input {key} declares "
            f"{type(domain).__name__}, which exposes no axes"
        )
    return separable


def _names(candidates: list[tuple[ParameterId, Domain]]) -> list[str]:
    return [str(key) for key, _ in candidates]
