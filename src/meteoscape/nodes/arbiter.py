"""`Arbiter` - the one producer-resolution composite.

Per requested parameter it folds that parameter's candidates onto the target lattice with a
reconciler (v1: the default `priority` = select + fallback), then assembles the per-parameter
`ParameterData` into one Coverage. Takes the woven Source map + `SourceRegistry` raw — reconciler
policy (including priority ranking) lives here, not in the Weaver. See ADR-0004.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping

from ..config import ArbiterPolicy
from ..identity import SourceKey
from ..manifold.capability import Capability, UnionCapability
from ..manifold.core import Manifold, Selection
from ..parameters import ParameterId
from .composition import CompositionError, SourceRegistry


class Arbiter:
    def __init__(
        self,
        sources: Mapping[SourceKey, Manifold],
        registry: SourceRegistry,
        policy: ArbiterPolicy,
    ) -> None:
        if policy.default_reconciler != "priority":
            raise CompositionError(
                f"unsupported reconciler {policy.default_reconciler!r}; "
                "v1 ships only 'priority'"
            )
        self.sources = sources
        self.registry = registry
        self.policy = policy
        self.candidates = _priority_candidates(sources, registry)

    async def project(self, selection: Selection) -> Manifold:
        raise NotImplementedError

    @property
    def capability(self) -> Capability:
        """Combined: serves a parameter iff some candidate does (`UnionCapability` over the candidates'
        capabilities). The admission half; the reconciler decides *which* candidate at `project`."""
        return UnionCapability([m.capability for seq in self.candidates.values() for m in seq])


def _priority_candidates(
    sources: Mapping[SourceKey, Manifold],
    registry: SourceRegistry,
) -> Mapping[ParameterId, tuple[Manifold, ...]]:
    """Index woven Sources by parameter; rank via registry priority (lower wins; map order ties)."""

    def rank(item: tuple[int, tuple[SourceKey, Manifold]]) -> tuple[int, int]:
        bind_index, (key, _) = item
        return registry.sources[key].priority, bind_index

    by_parameter: dict[ParameterId, list[Manifold]] = defaultdict(list)
    for _, (_, node) in sorted(enumerate(sources.items()), key=rank):
        for parameter_id in node.capability.parameters:
            by_parameter[parameter_id].append(node)
    return {parameter_id: tuple(nodes) for parameter_id, nodes in by_parameter.items()}
