"""Point+timeline provider shape — shared tap / axis-spec vocabulary.

A timeline leaf fetches a single X/Y point and an hourly T series; only Z varies per parameter.
`PointSeriesTap` encodes that shape. Other provider shapes (gridded NWP, soundings) are a deferred
seam — not this module.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum

from ...manifold.domain import AxisName, Interval, IntervalAxis, RegularAxis
from ...parameters import ParameterId


class AxisMode(Enum):
    """How an `AxisSpec` materialises into an axis cell."""

    POINT = "point"
    SPAN = "span"


@dataclass(frozen=True)
class AxisSpec:
    """Geometric cell declaration: an interval plus whether it is a point sample or a span cell."""

    interval: Interval
    mode: AxisMode


@dataclass(frozen=True)
class VendorVar:
    """One vendor hourly field: its name and the unit token expected in the vendor's unit map."""

    name: str
    unit: str


Decode = Callable[[Mapping[str, Sequence[float | None]]], list[float]]
"""Quantity transform over already unit-converted vendor series (None cells stay None → nan)."""


@dataclass(frozen=True)
class PointSeriesTap:
    """Tap for a point+timeline provider shape: one output parameter, one Z cell.

    X/Y (request-derived points) and T (provider rolling / hourly series) are structural to the
    shape — only `z` varies per parameter.
    """

    produces: ParameterId
    vendor_vars: tuple[VendorVar, ...]
    z: AxisSpec
    decode: Decode


def axis(spec: AxisSpec, *, name: AxisName = AxisName.Z) -> RegularAxis | IntervalAxis:
    """Materialise an `AxisSpec` into a footprint / native-record axis (POINT or SPAN)."""
    if spec.mode is AxisMode.POINT:
        level = spec.interval.lower
        if not isinstance(level, float):
            raise ValueError(f"POINT AxisSpec requires float interval, got {spec.interval!r}")
        return RegularAxis(name, level, 1.0, 1, cellular=False)
    return IntervalAxis(name, spec.interval)


def cell(value: float | None) -> float:
    """Map a nullable vendor sample to a float (`None` → nan)."""
    return float("nan") if value is None else float(value)


def passthrough(var: str) -> Decode:
    """Decode that copies one already-converted vendor series into canonical values."""

    def decode(arrays: Mapping[str, Sequence[float | None]]) -> list[float]:
        return [cell(v) for v in arrays[var]]

    return decode


# --- Shared hourly / vertical presets (tap building blocks) ---

HOURLY_STEP = timedelta(hours=1)

# Conventional tropopause-scale upper for a total-cloud column cell (stand-in; vendors rarely publish TOA).
TOA_M = 15_000.0

Z_2M = AxisSpec(Interval(2.0, 2.0), AxisMode.POINT)
Z_10M = AxisSpec(Interval(10.0, 10.0), AxisMode.POINT)
Z_SURFACE = AxisSpec(Interval(0.0, 0.0), AxisMode.POINT)
Z_COLUMN = AxisSpec(Interval(0.0, TOA_M), AxisMode.SPAN)
