"""`Arbiter` - the one producer-resolution composite.

Per requested parameter it folds that parameter's ordered candidates onto the target lattice with a
reconciler (v1: the default `priority` = select + fallback), then assembles the per-parameter
`ParameterData` into one Coverage. A dumb iterator over Weaver-ordered candidates; per-cell fold
behaviour is test-driven from 002 onward.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..manifold.core import Manifold, Selection
from ..manifold.parameters.vocabulary import ParameterId


class Arbiter:
    def __init__(self, candidates: Mapping[ParameterId, Sequence[Manifold]]) -> None:
        self.candidates = candidates

    def project(self, selection: Selection) -> Manifold:
        raise NotImplementedError
