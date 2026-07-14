"""`Calculator` - a derived-parameter composite Manifold.

A selectable producer that computes one output `ParameterDef` from input parameters via a function,
resolving those inputs through a scoped `Arbiter` (its `resolver`). It lets requestable derived views
(v1: `wind_speed` / `wind_direction` from canonical `wind_u` / `wind_v`) enter the algebra without
persisting synthetic parameters.

Its capability is *induced*: it serves its output wherever every input is servable through the
resolver - a `DerivedCapability` over `resolver.capability`. Provenance for a projected result is
synthetic (the derivation over its inputs' lineage). See ADR-0004.
"""

from __future__ import annotations

from ..manifold.capability import Capability, DerivedCapability
from ..manifold.core import Manifold, Selection
from ..parameters import ParameterDef, ParameterId


class Calculator:
    def __init__(
        self, output: ParameterDef, inputs: frozenset[ParameterId], resolver: Manifold
    ) -> None:
        self.output = output
        self.inputs = inputs
        self.resolver = resolver  # scoped Arbiter over the input parameters

    async def project(self, selection: Selection) -> Manifold:
        raise NotImplementedError

    @property
    def capability(self) -> Capability:
        return DerivedCapability(self.output, self.inputs, self.resolver.capability)
