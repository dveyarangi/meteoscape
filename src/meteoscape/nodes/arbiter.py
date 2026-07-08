"""`Arbiter` - the one producer-resolution composite.

Per requested parameter it folds that parameter's ordered candidates onto the target lattice with a
reconciler (v1: the default `priority` = select + fallback), then assembles the per-parameter
`ParameterData` into one Coverage. See ADR-0004.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..catalog.vocabulary import ParameterId
from ..manifold.capability import Capability, UnionCapability
from ..manifold.core import Manifold, Selection


class Arbiter:
    def __init__(self, candidates: Mapping[ParameterId, Sequence[Manifold]]) -> None:
        self.candidates = candidates

    async def project(self, selection: Selection) -> Manifold:
        raise NotImplementedError

    @property
    def capability(self) -> Capability:
        """Combined: serves a parameter iff some candidate does (`UnionCapability` over the candidates'
        capabilities). The admission half; the reconciler decides *which* candidate at `project`."""
        return UnionCapability([m.capability for seq in self.candidates.values() for m in seq])
