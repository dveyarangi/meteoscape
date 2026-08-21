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
    Interval,
    contains_extents,
    first_incomparable,
    split_extents,
)
from ..manifold.provenance import PerParameter, Provenance
from ..parameters import ParameterDef, ParameterId
from .composition import (
    CalculatorRegistry,
    CompositionError,
    SourceRegistry,
    require_separable,
)


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
        self,
        definition: ParameterDef,
        candidates: Sequence[tuple[ProducerKey, Domain]],
    ) -> Domain:
        """The composed Reach for `definition` over its candidates' published reaches (ADR-0007)."""
        ...


@dataclass(frozen=True)
class PriorityReconciler:
    """Lower priority wins; equal priority keeps candidate (bind) order — stable sort."""

    priority: Mapping[ProducerKey, int]

    def select(self, parameter: ParameterId, candidates: Sequence[Producer]) -> Sequence[Producer]:
        return sorted(candidates, key=lambda p: self.priority[p.key])

    def compose_domains(
        self,
        definition: ParameterDef,
        candidates: Sequence[tuple[ProducerKey, Domain]],
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
                f"reach composition for {definition.id} requires at least one candidate"
            )
        if len(candidates) == 1:
            return candidates[0][1]

        band = None if definition.z_allowance is None else Interval(*definition.z_allowance)
        checked = [
            (
                key,
                require_separable(
                    domain, rule=f"reach composition for {definition.id}", declarer=key
                ),
            )
            for key, domain in candidates
        ]
        for index, (_key, domain) in enumerate(checked):
            if all(contains_extents(domain, other, z_allowance=band) for _k, other in checked):
                return candidates[index][1]

        witness = first_incomparable(checked, z_allowance=band)
        # Containment is transitive: no maximum ⇒ some pair nests neither way.
        assert witness is not None
        (left_key, left), (right_key, right) = witness
        raise CompositionError(
            f"incomparable reach footprints for {definition.id}: "
            f"{split_extents(left_key, left, right_key, right, z_allowance=band)}; "
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
                parameter: reconciler.compose_domains(
                    candidates[0].node.capability.parameters[parameter],
                    _reaches(parameter, candidates),
                )
                for parameter, candidates in self.by_parameter.items()
            },
        )

    async def project(self, selection: Selection) -> Manifold:
        """Admit per parameter; project each winner; on a child's `RuntimeFailure`, try the next.

        Unserved parameters are omitted; an empty admitted set → `CapabilityMismatch`. A fault
        re-enters selection for that producer's parameters, skipping anyone who already faulted
        in this call — wholesale, one origin per parameter (docs/v1-requirements.md). Exhaustion
        of every candidate still fails the whole request
        (docs/concerns.md#30-response-membership-under-runtime-degraded-fallback).
        """
        winners = self._admit(selection)
        if not winners:
            raise CapabilityMismatch("no producer admits any requested parameter")

        served: list[tuple[Producer, frozenset[ParameterId], Manifold]] = []
        pending = list(_group_by_producer(winners).values())
        faulted: list[ProducerKey] = []

        while pending:
            producer, params = pending.pop(0)
            try:
                result = await producer.node.project(selection.with_params(params))
            except RuntimeFailure as fault:
                faulted.append(producer.key)
                pending.extend(self._reroute(params, selection, faulted, fault))
                continue
            served.append((producer, params, result))

        if len(served) == 1:
            return served[0][2]
        return self._assemble(served)

    def _admit(self, selection: Selection) -> dict[ParameterId, Producer]:
        """First candidate that `serves`, per requested parameter — no projection yet."""
        winners: dict[ParameterId, Producer] = {}
        for parameter in selection.parameters:
            winner = self._first_admitted(parameter, selection, faulted=())
            if winner is not None:
                winners[parameter] = winner
        return winners

    def _first_admitted(
        self,
        parameter: ParameterId,
        selection: Selection,
        faulted: Sequence[ProducerKey],
    ) -> Producer | None:
        skipped = set(faulted)
        for candidate in self.reconciler.select(parameter, self.by_parameter.get(parameter, ())):
            if candidate.key in skipped:
                continue
            if candidate.node.capability.serves(parameter, selection.domain):
                return candidate
        return None

    def _reroute(
        self,
        params: frozenset[ParameterId],
        selection: Selection,
        faulted: Sequence[ProducerKey],
        last_fault: RuntimeFailure,
    ) -> list[tuple[Producer, frozenset[ParameterId]]]:
        """Re-select the faulted group's parameters, skipping producers that already blew up."""
        next_winners: dict[ParameterId, Producer] = {}
        for parameter in params:
            winner = self._first_admitted(parameter, selection, faulted)
            if winner is None:
                # TODO(#30): dissolve this whole-request failure into per-parameter reasons.
                names = ", ".join(str(key) for key in faulted)
                raise RuntimeFailure(
                    f"{parameter} exhausted after {names} faulted: {last_fault}"
                ) from last_fault
            next_winners[parameter] = winner
        return list(_group_by_producer(next_winners).values())

    def _assemble(
        self,
        served: Sequence[tuple[Producer, frozenset[ParameterId], Manifold]],
    ) -> CoverageRecord:
        """Merge already-projected parameter groups on the shared domain via `PerParameter`."""
        ranges: dict[ParameterId, ParameterData] = {}
        defs: dict[ParameterId, ParameterDef] = {}
        prov: dict[ParameterId, Provenance] = {}
        domain = None
        for producer, params, result in served:
            if not isinstance(result, Coverage):
                raise RuntimeFailure(
                    f"producer {producer.key} returned a non-Coverage Manifold from project"
                )
            if domain is None:
                domain = result.domain
            elif result.domain != domain:
                # TODO(#39): an engine invariant break wearing a producer's category — no producer
                # faulted here. `RuntimeFailure` remains only because no engine-failure category exists.
                # Guarded by `test_winner_domains_that_differ_fail_the_whole_request`.
                raise RuntimeFailure("closed-projection invariant broken: winner domains differ")
            for pid in params:
                ranges[pid] = result.ranges[pid]
                defs[pid] = result.capability.parameters[pid]
                prov[pid] = result.provenance.summary(pid)

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
