"""The `ParameterTable` seam and its v1 static representation.

`ParameterTable` is the injected lookup of `ParameterDef`s keyed by `ParameterId`; producers and the
edge resolve canonical parameter facts from it. v1 ships `StaticParameterTable` hosting the core-5.
File / UI-backed representations are deferred.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator

from .vocabulary import (
    CellStatistic,
    ExtentScaling,
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
    def core_5(cls) -> StaticParameterTable:
        """The v1 core-5 table.

        Canonical units are provisional - concrete parameter conventions are deferred
        (v1-requirements - Open / TBD).
        """
        return cls(_CORE_5)


# Core-5 parameter ids. Ids are the functional `(quantity, statistic)`, never the surface height:
# `temperature_2m` / `wind_u_10m` are edge aliases desugaring to a functional id + a Domain Z cell
# (ADR-0002). With v1's uniform `point` statistic the id collapses to the quantity name.
AIR_TEMPERATURE = ParameterId("air_temperature")
PRECIPITATION = ParameterId("precipitation")
WIND_U = ParameterId("wind_u")
WIND_V = ParameterId("wind_v")
RELATIVE_HUMIDITY = ParameterId("relative_humidity")

# Precipitation is the only extensive parameter; wind rides as u/v components (speed/direction are
# derived views) so the vector coupling stays out of per-parameter resamplers. See v1-requirements / ADR-0002.
_CORE_5: tuple[ParameterDef, ...] = (
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
