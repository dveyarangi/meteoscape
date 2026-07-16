"""Calculator plugin catalogue: the formula plus its invocation constraints.

`CalculatorCatalog` is `fn_id → CalculatorManifest`. Each manifest is a cohesive plugin face — the
combine function alongside the declarative constraints on the shapes it may be invoked over. A
`CalculatorDef` (in `ProfileConfig`) only enables one against this catalogue. See ADR-0005.
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
    """Cohesive calculator plugin face — formula plus declarative invocation constraints."""

    fn_id: str
    fn: CombineFn
    # Method tag (for a method-bearing output's SyntheticOrigin) + invocation constraints land with
    # behaviour; the node reads the tag to stamp provenance. Catalogue row stays settings, not data-flow.
