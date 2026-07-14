"""Concrete `Coverage` realizations (the contract itself lives in `core.py`).

Realizations satisfy the contract *structurally*, not by inheritance: a frozen dataclass field would
clash with the protocol's `domain` property descriptor. v1 ships `CoverageRecord` — the one
memory-backed realization; Timeline / Grid are domain *shapes*, not classes (session 0008).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ..parameters import ParameterId
from .capability import EnumerableCapability
from .core import Manifold, Selection
from .data import ParameterData
from .domain import EnumerableDomain
from .provenance import ProvenanceField


@dataclass(frozen=True)
class CoverageRecord:
    """The canonical memory-backed `Coverage`: inert value object over an enumerable `domain`.

    `capability` is the materialized `EnumerableCapability` - it carries the parameter set co-domained on
    its one enumerable grid, so the `Countable.domain` derives from `capability.domain` rather than being
    stored twice. `ranges` are positional to `domain`. Implementations may vary by backing later;
    never by domain shape.
    """

    capability: EnumerableCapability
    ranges: Mapping[ParameterId, ParameterData]
    provenance: ProvenanceField

    @property
    def domain(self) -> EnumerableDomain:
        return self.capability.domain

    async def project(self, selection: Selection) -> Manifold:
        from .sampling import resample

        return resample(self, selection)
