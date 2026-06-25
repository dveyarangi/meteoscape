"""`ParameterData` - one parameter's materialized data slice in a Coverage.

Positional to the Coverage's Domain (`values[i]` at the i-th `enumerate()` point). `unit` and
`aggregation` are cloned by value from the `ParameterDef` so a stored / serialized Coverage is
self-describing without the parameter table; provenance is carried per-parameter as a
`ProvenanceField`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..provenance import ProvenanceField
from .vocabulary import CellAggregation, ParameterId, Unit


@dataclass(frozen=True)
class ParameterData:
    """`present is None` => all cells present; `present[i] is False` => nodata (a successful gap).

    `values` is typed abstractly here; its concrete array backing is decided when behaviour lands
    (numpy/xarray stay behind this interface).
    """

    parameter: ParameterId
    values: Sequence[float]
    present: Sequence[bool] | None
    unit: Unit
    aggregation: CellAggregation
    provenance: ProvenanceField
