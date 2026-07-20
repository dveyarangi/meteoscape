"""`Arbiter` — the one producer-resolution composite.

Per requested parameter it folds that parameter's candidates onto the target lattice with a
`Reconciler` (v1: `priority` = select + fallback), then assembles the per-parameter
`ParameterData` into one Coverage. Constructed as `Arbiter(producers, reconciler)` — priority is
registry data flattened into the reconciler by `build_reconciler`; the Weaver never ranks.
See ADR-0004.
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
from ..manifold.provenance import PerParameter, Provenance
from ..parameters import ParameterDef, ParameterId
from .composition import CalculatorRegistry, CompositionError, SourceRegistry


@dataclass(frozen=True)
class Producer:
    """Neutral Arbiter candidate — a live node paired with its `ProducerKey` (no priority)."""

    node: Manifold
    key: ProducerKey


class Reconciler(Protocol):
    """Per-parameter selection / combination policy over competing producers."""

    def select(
        self, parameter: ParameterId, candidates: Sequence[Producer]
    ) -> Sequence[Producer]: ...


@dataclass(frozen=True)
class PriorityReconciler:
    """Lower priority wins; equal priority keeps candidate (bind) order — stable sort."""

    priority: Mapping[ProducerKey, int]

    def select(self, parameter: ParameterId, candidates: Sequence[Producer]) -> Sequence[Producer]:
        return sorted(candidates, key=lambda p: self.priority[p.key])


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
    def __init__(self, producers: Sequence[Producer], reconciler: Reconciler) -> None:
        self.producers = tuple(producers)
        self.reconciler = reconciler
        self.by_parameter = _index(self.producers)

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
        """Combined: serves a parameter iff some producer does (`UnionCapability`)."""
        return UnionCapability([p.node.capability for p in self.producers])


def _index(producers: Sequence[Producer]) -> Mapping[ParameterId, tuple[Producer, ...]]:
    """Index each producer under every parameter it declares — one path for sources and calcs."""
    by_parameter: dict[ParameterId, list[Producer]] = defaultdict(list)
    for producer in producers:
        for parameter_id in producer.node.capability.parameters:
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
