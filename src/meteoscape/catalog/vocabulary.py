"""Parameter vocabulary: the identity types (`ParameterId`, `Quantity`, `ParameterDef`) and closed
enums (`ExtentScaling`, `CellStatistic`, `MeasurementScale`) the catalog is built from.

The parameter model they encode - the `(quantity, statistic)` functional, extent on the Domain, the
resampler entailed by `(scale, statistic, extent_scaling)` - is fixed by ADR-0002.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import NewType

ParameterId = NewType("ParameterId", str)
"""Stable identifier of a `ParameterDef` within a `ParameterTable`."""

Unit = NewType("Unit", str)
"""A canonical unit token. Concrete canonical-unit conventions are deferred (parameter conventions)."""


class ExtentScaling(Enum):
    """A quantity's relationship to a cell's temporal extent. Closed.

    `intensive` is extent-independent (a window statistic applies); `extensive` is the integral over
    the cell extent (additive across adjacent cells).
    """

    INTENSIVE = "intensive"
    EXTENSIVE = "extensive"


class CellStatistic(Enum):
    """The window statistic a value summarizes its cell with - dimension-preserving. Closed.

    `point` is the degenerate window (an instant). The calculus axis (accumulation) is the quantity
    `extent_scaling`, not a value here.
    """

    POINT = "point"
    MAX = "max"
    MIN = "min"
    MEAN = "mean"


class MeasurementScale(Enum):
    """A quantity's measurement scale - the refine-up resampler family. Closed.

    `linear` interpolates and averages; `circular` is angular (shortest-arc, never linear-in-degrees);
    `nominal` / `ordinal` are categorical (fill / mode / priority, never averaged). Interpolability is
    thus a parameter fact, not a Domain/axis one (ADR-0002). v1's canonical quantities are all `linear`
    (wind rides as u/v); the derived `wind_direction` is `circular` but unexercised by v1's
    nearest-neighbor read-back.
    """

    LINEAR = "linear"
    CIRCULAR = "circular"
    NOMINAL = "nominal"
    ORDINAL = "ordinal"


@dataclass(frozen=True)
class Quantity:
    """The identity root of a parameter - a physical field carrying an `extent_scaling` and a `scale`.

    Rain-intensity (intensive rate) and precipitation (extensive integral) are distinct quantities
    related by integration. `scale` (measurement scale) selects the refine-up resampler; it defaults to
    `linear`, the v1 case for every canonical quantity.
    """

    name: str
    extent_scaling: ExtentScaling
    scale: MeasurementScale = MeasurementScale.LINEAR


@dataclass(frozen=True)
class ParameterDef:
    """What a `ParameterId` resolves to: a parameter's canonical, id-entailed facts (ADR-0002)."""

    id: ParameterId
    quantity: Quantity
    canonical_unit: Unit
    statistic: CellStatistic

    @property
    def extent_scaling(self) -> ExtentScaling:
        return self.quantity.extent_scaling
