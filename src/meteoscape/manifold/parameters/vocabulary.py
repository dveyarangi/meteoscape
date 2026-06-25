"""Parameter vocabulary: the identity types and closed enums fixed by ADR-0002.

A requestable parameter is a functional `(quantity, aggregation)`. Extent is *not* in the key - it
rides the Domain's `valid_time` bounds. `kind` is a property of the `Quantity` (its relationship to
a cell's temporal extent); `ParameterDef.kind` is sourced from the quantity, so there is a single
source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import NewType

ParameterId = NewType("ParameterId", str)
"""Stable identifier of a `ParameterDef` within a `ParameterTable`."""

Unit = NewType("Unit", str)
"""A canonical unit token. Concrete canonical-unit conventions are deferred (parameter conventions)."""


class Kind(Enum):
    """A quantity's relationship to a cell's temporal extent (extent-scaling). Closed."""

    INTENSIVE = "intensive"
    EXTENSIVE = "extensive"


class CellAggregation(Enum):
    """The window statistic a value summarizes its cell with - dimension-preserving. Closed.

    `point` is the degenerate window (an instant). The calculus axis (accumulation) is the quantity
    `kind`, not a value here.
    """

    POINT = "point"
    MAX = "max"
    MIN = "min"
    MEAN = "mean"


@dataclass(frozen=True)
class Quantity:
    """The identity root of a parameter - a physical field carrying a `kind`.

    Rain-intensity (intensive rate) and precipitation (extensive integral) are distinct quantities
    related by integration.
    """

    name: str
    kind: Kind


@dataclass(frozen=True)
class ParameterDef:
    """The canonical definition a `ParameterData` clones `unit` / `aggregation` from.

    `kind` is exposed for convenience but sourced from `quantity` (single source of truth, ADR-0002).
    """

    id: ParameterId
    quantity: Quantity
    canonical_unit: Unit
    aggregation: CellAggregation

    @property
    def kind(self) -> Kind:
        return self.quantity.kind
