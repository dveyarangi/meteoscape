"""The `ParameterTable` seam and its v1 static representation.

`ParameterTable` is the injected lookup of `ParameterDef`s keyed by `ParameterId`; producers and the
edge resolve canonical parameter facts from it. v1 ships `StaticParameterTable` hosting the v1
parameters (5 canonical + 2 derived wind views). File / UI-backed representations are deferred.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator

from .vocabulary import (
    CellStatistic,
    ExtentScaling,
    MeasurementScale,
    ParameterDef,
    ParameterId,
    Quantity,
    Unit,
)


class ParameterTable(ABC):
    """Injected lookup of `ParameterDef`s keyed by `ParameterId` (a swappable interface)."""

    @abstractmethod
    def get(self, parameter: ParameterId) -> ParameterDef:
        """Resolve a parameter's canonical definition; raise `KeyError` if absent."""
        ...

    @abstractmethod
    def __contains__(self, parameter: ParameterId) -> bool: ...

    @abstractmethod
    def __iter__(self) -> Iterator[ParameterId]: ...


class StaticParameterTable(ParameterTable):
    """An in-memory `ParameterTable` over a fixed set of `ParameterDef`s (v1)."""

    def __init__(self, definitions: Iterable[ParameterDef]) -> None:
        self._defs: dict[ParameterId, ParameterDef] = {d.id: d for d in definitions}

    def get(self, parameter: ParameterId) -> ParameterDef:
        return self._defs[parameter]

    def __contains__(self, parameter: ParameterId) -> bool:
        return parameter in self._defs

    def __iter__(self) -> Iterator[ParameterId]:
        return iter(self._defs)

    @classmethod
    def core(cls) -> StaticParameterTable:
        """The v1 parameter table: 5 canonical (provider-served) + 2 derived wind views.

        Canonical units are provisional - concrete parameter conventions are deferred
        (v1-requirements - Open / TBD).
        """
        return cls(_CORE)


# Parameter ids. Ids are the functional `(quantity, statistic)`, never the surface height:
# `temperature_2m` / `wind_u_10m` are edge aliases desugaring to a functional id + a Domain Z cell
# (ADR-0002). With v1's uniform `point` statistic the id collapses to the quantity name.
AIR_TEMPERATURE = ParameterId("air_temperature")
PRECIPITATION = ParameterId("precipitation")
WIND_U = ParameterId("wind_u")
WIND_V = ParameterId("wind_v")
RELATIVE_HUMIDITY = ParameterId("relative_humidity")
WIND_SPEED = ParameterId("wind_speed")
WIND_DIRECTION = ParameterId("wind_direction")

# The 5 canonical parameters providers deliver (post-Normalizer). Precipitation is the only extensive
# one; wind is canonical as u/v components (both linear), so linear interpolation of u/v is correct
# wind interpolation and the vector coupling stays out of per-parameter resamplers (ADR-0002).
_CANONICAL: tuple[ParameterDef, ...] = (
    ParameterDef(
        id=AIR_TEMPERATURE,
        quantity=Quantity("air_temperature", ExtentScaling.INTENSIVE),
        canonical_unit=Unit("degC"),
        statistic=CellStatistic.POINT,
    ),
    ParameterDef(
        id=PRECIPITATION,
        quantity=Quantity("precipitation", ExtentScaling.EXTENSIVE),
        canonical_unit=Unit("mm"),
        statistic=CellStatistic.POINT,
    ),
    ParameterDef(
        id=WIND_U,
        quantity=Quantity("eastward_wind", ExtentScaling.INTENSIVE),
        canonical_unit=Unit("m/s"),
        statistic=CellStatistic.POINT,
    ),
    ParameterDef(
        id=WIND_V,
        quantity=Quantity("northward_wind", ExtentScaling.INTENSIVE),
        canonical_unit=Unit("m/s"),
        statistic=CellStatistic.POINT,
    ),
    ParameterDef(
        id=RELATIVE_HUMIDITY,
        quantity=Quantity("relative_humidity", ExtentScaling.INTENSIVE),
        canonical_unit=Unit("percent"),
        statistic=CellStatistic.POINT,
    ),
)

# The 2 derived wind views served by Calculators over `(wind_u, wind_v)` - both lossless functions of
# the vector: `speed = hypot(u, v)`, `direction = atan2(...)`. `wind_direction` is `circular`, the
# first non-linear scale, but v1's nearest-neighbor read-back never interpolates it (ADR-0004 / #5).
_DERIVED: tuple[ParameterDef, ...] = (
    ParameterDef(
        id=WIND_SPEED,
        quantity=Quantity("wind_speed", ExtentScaling.INTENSIVE),
        canonical_unit=Unit("m/s"),
        statistic=CellStatistic.POINT,
    ),
    ParameterDef(
        id=WIND_DIRECTION,
        quantity=Quantity("wind_direction", ExtentScaling.INTENSIVE, MeasurementScale.CIRCULAR),
        canonical_unit=Unit("degree"),
        statistic=CellStatistic.POINT,
    ),
)

_CORE: tuple[ParameterDef, ...] = _CANONICAL + _DERIVED
