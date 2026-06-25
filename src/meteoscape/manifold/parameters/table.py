"""The `ParameterTable` seam and its v1 static representation.

`ParameterTable` is the injected lookup of `ParameterDef`s keyed by `ParameterId`; producers and the
edge resolve canonical parameter facts from it. v1 ships `StaticParameterTable` hosting the core-5.
File / UI-backed representations are deferred.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator

from .vocabulary import (
    CellAggregation,
    Kind,
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


# Core-5 parameter ids (v1-requirements - Parameters).
TEMPERATURE_2M = ParameterId("temperature_2m")
PRECIPITATION = ParameterId("precipitation")
WIND_SPEED_10M = ParameterId("wind_speed_10m")
WIND_DIRECTION_10M = ParameterId("wind_direction_10m")
RELATIVE_HUMIDITY_2M = ParameterId("relative_humidity_2m")

# The set is deliberately heterogeneous: precipitation is the one extensive parameter; wind direction
# is circular (angular interpolation - a homogenization-kind concern, not an identity one). All five
# share `aggregation = point` in v1.
_CORE_5: tuple[ParameterDef, ...] = (
    ParameterDef(
        id=TEMPERATURE_2M,
        quantity=Quantity("air_temperature", Kind.INTENSIVE),
        canonical_unit=Unit("degC"),
        aggregation=CellAggregation.POINT,
    ),
    ParameterDef(
        id=PRECIPITATION,
        quantity=Quantity("precipitation", Kind.EXTENSIVE),
        canonical_unit=Unit("mm"),
        aggregation=CellAggregation.POINT,
    ),
    ParameterDef(
        id=WIND_SPEED_10M,
        quantity=Quantity("wind_speed", Kind.INTENSIVE),
        canonical_unit=Unit("m/s"),
        aggregation=CellAggregation.POINT,
    ),
    ParameterDef(
        id=WIND_DIRECTION_10M,
        quantity=Quantity("wind_direction", Kind.INTENSIVE),
        canonical_unit=Unit("deg"),
        aggregation=CellAggregation.POINT,
    ),
    ParameterDef(
        id=RELATIVE_HUMIDITY_2M,
        quantity=Quantity("relative_humidity", Kind.INTENSIVE),
        canonical_unit=Unit("percent"),
        aggregation=CellAggregation.POINT,
    ),
)
