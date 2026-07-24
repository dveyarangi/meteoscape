"""`Arbiter` — the one producer-resolution composite.

Two folds over the same candidates. At **construction** it composes each parameter's published reaches
into the `UnionCapability` it advertises (the reconciler's `compose_domains`, cached as one object), so
a sheared profile fails the build here. At **request** it folds that parameter's candidates onto the
target lattice with the `Reconciler` (v1: `priority` = select + fallback), then assembles the
per-parameter `ParameterData` into one Coverage.

Constructed as `Arbiter(producers, reconciler, scope=...)` — priority is registry data flattened into
the reconciler by `build_reconciler`; the Weaver never ranks. `scope` (a Calculator's inputs) limits
which declared parameters it composes and admits; `scope=None` is the top Arbiter over everything.
See ADR-0004 / ADR-0007.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from ..config import ArbiterPolicy
from ..errors import CapabilityMismatch, RuntimeFailure
from ..identity import ProducerKey
from ..manifold.capability import Capability, EnumerableCapability, UnionCapability
from ..manifold.core import Coverage, Manifold, Selection
from ..manifold.coverage import CoverageRecord
from ..manifold.data import ParameterData
from ..manifold.domain import (
    Domain,
    Separable,
    as_separable,
    contains_extents,
    first_incomparable,
    split_extents,
)
from ..manifold.provenance import PerParameter, Provenance
from ..parameters import ParameterDef, ParameterId
from .composition import CalculatorRegistry, CompositionError, SourceRegistry


@dataclass(frozen=True)
class Producer:
    """Neutral Arbiter candidate — a live node paired with its `ProducerKey` (no priority)."""

    node: Manifold
    key: ProducerKey


class Reconciler(Protocol):
    """Per-parameter selection / combination policy over competing producers.

    Two members, both policy over competing producers: `select` orders them at request time; the eager
    `compose_domains` folds their published reaches into the one a composite advertises (ADR-0007).
    """

    def select(
        self, parameter: ParameterId, candidates: Sequence[Producer]
    ) -> Sequence[Producer]: ...

    def compose_domains(
        self, parameter: ParameterId, candidates: Sequence[tuple[ProducerKey, Domain]]
    ) -> Domain:
        """The composed Reach for one parameter over its candidates' published reaches (ADR-0007)."""
        ...


@dataclass(frozen=True)
class PriorityReconciler:
    """Lower priority wins; equal priority keeps candidate (bind) order — stable sort."""

    priority: Mapping[ProducerKey, int]

    def select(self, parameter: ParameterId, candidates: Sequence[Producer]) -> Sequence[Producer]:
        return sorted(candidates, key=lambda p: self.priority[p.key])

    def compose_domains(
        self, parameter: ParameterId, candidates: Sequence[tuple[ProducerKey, Domain]]
    ) -> Domain:
        """Dominance-or-raise: the candidate whose reach contains all others, else `CompositionError`.

        Ignores priority — dominance is geometric (ADR-0007). Separability is the precondition of
        *comparing* per axis, so a lone candidate is returned unchecked (it compares against nothing);
        two or more must all be separable. This raise site is the sole author of the whole error, so it
        names the parameter, the producers, and both failing axes. Returns an existing candidate
        `Domain`, never a synthesized one, so a clock-anchored `RollingAxis` stays live.
        """
        if not candidates:
            raise CompositionError(
                f"reach composition for {parameter} requires at least one candidate"
            )
        if len(candidates) == 1:
            return candidates[0][1]

        checked = [(key, _require_separable(parameter, key, domain)) for key, domain in candidates]
        for index, (_key, domain) in enumerate(checked):
            if all(contains_extents(domain, other) for _k, other in checked):
                return candidates[index][1]

        witness = first_incomparable(checked)
        # Containment is transitive: no maximum ⇒ some pair nests neither way.
        assert witness is not None
        (left_key, left), (right_key, right) = witness
        raise CompositionError(
            f"incomparable reach footprints for {parameter}: "
            f"{split_extents(left_key, left, right_key, right)}; "
            f"candidates {_names(candidates)}; X/Y preference is unbuilt"
        )


def build_reconciler(
    policy: ArbiterPolicy,
    sources: SourceRegistry,
    calcs: CalculatorRegistry,
) -> Reconciler:
    """Flatten both registries' priority recipe fields into a bare `ProducerKey → int` lookup."""
    if policy.default_reconciler != "priority":
        raise CompositionError(
            f"unsupported reconciler {policy.default_reconciler!r}; v1 ships only 'priority'"
        )
    priority: dict[ProducerKey, int] = {
        key: registered.priority for key, registered in sources.sources.items()
    }
    priority.update({key: registered.priority for key, registered in calcs.calculators.items()})
    return PriorityReconciler(priority)


class Arbiter:
    def __init__(
        self,
        producers: Sequence[Producer],
        reconciler: Reconciler,
        *,
        scope: frozenset[ParameterId] | None = None,
    ) -> None:
        self.producers = tuple(producers)
        self.reconciler = reconciler
        self.by_parameter = _index(self.producers, scope)
        self._capability = UnionCapability(
            members={p.key: p.node.capability for p in self.producers},
            domains={
                parameter: reconciler.compose_domains(parameter, _reaches(parameter, candidates))
                for parameter, candidates in self.by_parameter.items()
            },
        )

    async def project(self, selection: Selection) -> Manifold:
        """Admit per parameter; project each winning producer once; assemble if winners span nodes.

        Unserved parameters are omitted; an empty admitted set → `CapabilityMismatch`.
        `RuntimeFailure` propagates and fails the whole request.
        """
        winners: dict[ParameterId, Producer] = {}
        for parameter in selection.parameters:
            candidates = self.by_parameter.get(parameter, ())
            for candidate in self.reconciler.select(parameter, candidates):
                if candidate.node.capability.serves(parameter, selection.domain):
                    winners[parameter] = candidate
                    break

        if not winners:
            raise CapabilityMismatch("no producer admits any requested parameter")

        by_producer = _group_by_producer(winners)
        if len(by_producer) == 1:
            producer, params = next(iter(by_producer.values()))
            return await producer.node.project(selection.with_params(params))
        return await self._assemble(by_producer, selection)

    async def _assemble(
        self,
        by_producer: Mapping[ProducerKey, tuple[Producer, frozenset[ParameterId]]],
        selection: Selection,
    ) -> CoverageRecord:
        """Merge disjoint single-parameter winners on the shared domain via `PerParameter`."""
        results: dict[ProducerKey, Coverage] = {}
        for key, (producer, params) in by_producer.items():
            result = await producer.node.project(selection.with_params(params))
            if not isinstance(result, Coverage):
                raise RuntimeFailure(
                    f"producer {key} returned a non-Coverage Manifold from project"
                )
            results[key] = result

        ranges: dict[ParameterId, ParameterData] = {}
        defs: dict[ParameterId, ParameterDef] = {}
        prov: dict[ParameterId, Provenance] = {}
        domain = None
        for key, (_producer, params) in by_producer.items():
            cov = results[key]
            if domain is None:
                domain = cov.domain
            elif cov.domain != domain:
                raise RuntimeFailure("closed-projection invariant broken: winner domains differ")
            for pid in params:
                ranges[pid] = cov.ranges[pid]
                defs[pid] = cov.capability.parameters[pid]
                prov[pid] = cov.provenance.summary(pid)

        assert domain is not None
        return CoverageRecord(
            capability=EnumerableCapability(domain=domain, parameters=defs),
            ranges=ranges,
            provenance=PerParameter(by_parameter=prov),
        )

    @property
    def capability(self) -> Capability:
        """The eagerly-composed `UnionCapability`, one stored object across accesses. Typed to the
        algebra (`Capability`), not the composite it happens to construct."""
        return self._capability


def _require_separable(parameter: ParameterId, key: ProducerKey, domain: Domain) -> Separable:
    """Separability is dominance's precondition; raise here with the operator-facing message.

    `as_separable` returns `None` rather than raising (`manifold/` cannot import `CompositionError`),
    so this caller supplies the text — naming the parameter and the producer that declared geometry the
    `grid` rule cannot compare (ADR-0007, [#12](../concerns.md)).
    """
    separable = as_separable(domain)
    if separable is None:
        raise CompositionError(
            f"reach composition for {parameter} requires separable geometry; {key} declares "
            f"{type(domain).__name__}, which exposes no axes"
        )
    return separable


def _reaches(
    parameter: ParameterId, candidates: Sequence[Producer]
) -> list[tuple[ProducerKey, Domain]]:
    """Each candidate's published reach for `parameter` - `compose_domains`'s input.

    Every candidate is indexed under `parameter`, so `reach` answers for all of them
    (`p in parameters` ⟺ `reach(p)`).
    """
    return [(p.key, p.node.capability.reach(parameter)) for p in candidates]


def _names(candidates: Sequence[tuple[ProducerKey, Domain]]) -> list[str]:
    return [str(key) for key, _ in candidates]


def _index(
    producers: Sequence[Producer], scope: frozenset[ParameterId] | None
) -> Mapping[ParameterId, tuple[Producer, ...]]:
    """Index each producer under every parameter it declares, filtered to `scope` when given.

    `scope=None` (the top Arbiter) admits every declared parameter. A Calculator's scoped resolver
    passes `scope=reg.inputs`, so it composes and declares **exactly** the inputs the Calculator
    consumes — never a whole producer's out-of-scope parameter, which is what would shear a valid gust
    profile (ADR-0007). Filtering while building keeps `by_parameter` and the capability from
    ever being transiently inconsistent.
    """
    by_parameter: dict[ParameterId, list[Producer]] = defaultdict(list)
    for producer in producers:
        for parameter_id in producer.node.capability.parameters:
            if scope is None or parameter_id in scope:
                by_parameter[parameter_id].append(producer)
    return {parameter_id: tuple(ps) for parameter_id, ps in by_parameter.items()}


def _group_by_producer(
    winners: Mapping[ParameterId, Producer],
) -> Mapping[ProducerKey, tuple[Producer, frozenset[ParameterId]]]:
    """Group admitted parameters by winning producer key (shared domain assembly input)."""
    groups: dict[ProducerKey, tuple[Producer, set[ParameterId]]] = {}
    for parameter, producer in winners.items():
        if producer.key not in groups:
            groups[producer.key] = (producer, set())
        groups[producer.key][1].add(parameter)
    return {key: (producer, frozenset(params)) for key, (producer, params) in groups.items()}
