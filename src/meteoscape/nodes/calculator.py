"""`Calculator` — a derived-parameter composite Manifold.

A selectable producer that co-produces an output group from input parameters via a combine kernel,
resolving those inputs through a scoped `Arbiter` (its `resolver`). The kernel returns
`(domain, ranges)` only; this node authors capability, provenance (propagate or synthesize), and
well-formedness. Its reach is composed here — contained-in-all over the inputs' reaches, eager at
construction, so a profile whose inputs shear fails the build — and handed to the `DerivedCapability`
that carries it. See ADR-0004 / ADR-0007.
"""

from __future__ import annotations

from collections.abc import Mapping

from ..errors import CompositionError, RuntimeFailure
from ..identity import CalculatorKey
from ..manifold.capability import Capability, DerivedCapability, EnumerableCapability
from ..manifold.core import Coverage, Manifold, Selection
from ..manifold.coverage import CoverageRecord
from ..manifold.domain import (
    Domain,
    contains_extents,
    first_incomparable,
    split_extents,
)
from ..manifold.provenance import Uniform
from ..parameters import ParameterDef, ParameterId
from .catalog.calculators import CombineFn
from .composition import require_separable


class Calculator:
    def __init__(
        self,
        key: CalculatorKey,
        outputs: Mapping[ParameterId, ParameterDef],
        inputs: frozenset[ParameterId],
        fn: CombineFn,
        resolver: Manifold,
    ) -> None:
        self.key = key
        self.outputs = outputs
        self.inputs = inputs
        self.fn = fn
        self.resolver = resolver  # scoped Arbiter over the input parameters
        self._capability = DerivedCapability(
            parameters=outputs,
            inputs=inputs,
            upstream=resolver.capability,
            domain=_contained_in_all(key, inputs, resolver.capability),
        )

    async def project(self, selection: Selection) -> Manifold:
        resolved = await self.resolver.project(Selection(selection.domain, self.inputs))
        if not isinstance(resolved, Coverage):
            raise RuntimeFailure("calculator resolver returned a non-Coverage Manifold")
        domain, ranges = self.fn(resolved)
        if ranges.keys() != self.outputs.keys():
            raise RuntimeFailure(
                f"calculator kernel ranges {set(ranges)} != declared outputs {set(self.outputs)}"
            )
        # Current kernels propagate one lossless origin; method-bearing synthesis is a planned extension.
        provenance = Uniform(resolved.provenance.summary(next(iter(self.inputs))))
        return CoverageRecord(
            capability=EnumerableCapability(domain=domain, parameters=dict(self.outputs)),
            ranges=ranges,
            provenance=provenance,
        )

    @property
    def capability(self) -> Capability:
        return self._capability


def _contained_in_all(
    calculator: CalculatorKey, inputs: frozenset[ParameterId], upstream: Capability
) -> Domain:
    """The input reach contained in every other - a Calculator serves exactly where all inputs do.

    The reconciler's dominance fold inverted (the minimum, not the maximum); it returns an input's own
    `Domain`, never a synthesized one, so a `RollingAxis` stays live. Sheared inputs (nesting neither
    way) or a non-separable multi-input set raise a build-time `CompositionError` naming the calculator
    and its inputs - this node is the sole author of that message (ADR-0007).
    """
    candidates = [(i, upstream.reach(i)) for i in inputs]
    if not candidates:
        raise CompositionError(f"calculator {calculator} has no inputs to resolve reach from")
    if len(candidates) == 1:
        return candidates[0][1]

    checked = [
        (
            key,
            require_separable(
                domain, rule=f"calculator {calculator} reach", declarer=f"input {key}"
            ),
        )
        for key, domain in candidates
    ]
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


def _names(candidates: list[tuple[ParameterId, Domain]]) -> list[str]:
    return [str(key) for key, _ in candidates]
