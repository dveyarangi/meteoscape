"""`Calculator` — a derived-parameter composite Manifold.

A selectable producer that co-produces an output group from input parameters via a combine kernel,
resolving those inputs through a scoped `Arbiter` (its `resolver`). The kernel returns
`(domain, ranges)` only; this node authors capability, provenance (propagate or synthesize), and
well-formedness. See ADR-0004.
"""

from __future__ import annotations

from collections.abc import Mapping

from ..errors import RuntimeFailure
from ..manifold.capability import Capability, DerivedCapability, EnumerableCapability
from ..manifold.core import Coverage, Manifold, Selection
from ..manifold.coverage import CoverageRecord
from ..manifold.provenance import Uniform
from ..parameters import ParameterDef, ParameterId
from .catalog.calculators import CombineFn


class Calculator:
    def __init__(
        self,
        outputs: Mapping[ParameterId, ParameterDef],
        inputs: frozenset[ParameterId],
        fn: CombineFn,
        resolver: Manifold,
    ) -> None:
        self.outputs = outputs
        self.inputs = inputs
        self.fn = fn
        self.resolver = resolver  # scoped Arbiter over the input parameters

    async def project(self, selection: Selection) -> Manifold:
        resolved = await self.resolver.project(Selection(selection.domain, self.inputs))
        if not isinstance(resolved, Coverage):
            raise RuntimeFailure("calculator resolver returned a non-Coverage Manifold")
        domain, ranges = self.fn(resolved)
        if ranges.keys() != self.outputs.keys():
            raise RuntimeFailure(
                f"calculator kernel ranges {set(ranges)} != declared outputs {set(self.outputs)}"
            )
        # Propagate: lossless single-origin transform (v1 wind). Method-bearing synthesis is post-v1.
        provenance = Uniform(resolved.provenance.summary(next(iter(self.inputs))))
        return CoverageRecord(
            capability=EnumerableCapability(domain=domain, parameters=dict(self.outputs)),
            ranges=ranges,
            provenance=provenance,
        )

    @property
    def capability(self) -> Capability:
        return DerivedCapability(self.outputs, self.inputs, self.resolver.capability)
