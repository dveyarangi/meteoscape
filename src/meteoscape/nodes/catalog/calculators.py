"""Calculator plugin catalogue: formulas plus their invocation constraints.

`CalculatorCatalog` is `fn_id → CalculatorManifest`. Each manifest is a cohesive plugin face — the
combine function alongside the declarative constraints on the shapes it may be invoked over. A
`CalculatorDef` (in `ProfileConfig`) enables one against this catalogue. See ADR-0005.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ...parameters import ParameterId

if TYPE_CHECKING:
    from ...manifold.core import Coverage
    from ...manifold.data import ParameterData
    from ...manifold.domain import EnumerableDomain

CalculatorCatalog = Mapping[str, "CalculatorManifest"]

CombineFn = Callable[
    ["Coverage"],
    tuple["EnumerableDomain", Mapping[ParameterId, "ParameterData"]],
]
"""The kernel: Coverage → (domain, ranges). Pure structure/computation — the `Calculator` node owns
capability, provenance authorship, and output well-formedness (ADR-0004)."""


@dataclass(frozen=True)
class CalculatorManifest:
    """Cohesive calculator plugin face — formula plus the co-produced I/O group.

    `outputs` / `inputs` are the kernel's own facts, mirroring `OfferingSpec` as the product row.
    A `CalculatorDef` selects and ranks; it does not restate this group. See ADR-0004 / ADR-0005.
    """

    fn_id: str
    fn: CombineFn
    outputs: frozenset[ParameterId]
    inputs: frozenset[ParameterId]
    # A method tag for SyntheticOrigin and further invocation constraints belong with the behavior;
    # the node reads them to stamp provenance. Catalogue rows remain settings, not data flow.
