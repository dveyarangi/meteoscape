"""Capability family — serves predicates over real Domain.contains."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fakes import STOPPED, footprint_domain, point_timeline_domain
from meteoscape.manifold.cadence import CadenceDef
from meteoscape.manifold.capability import (
    DerivedCapability,
    EnumerableCapability,
    FootprintCapability,
    UnionCapability,
)
from meteoscape.manifold.domain import AxisName, GridDomain, RegularAxis
from meteoscape.nodes.catalog.paramtable import StaticParameterTable
from meteoscape.parameters import (
    AIR_TEMPERATURE,
    PRECIPITATION,
    WIND_DIRECTION,
    WIND_SPEED,
    WIND_U,
    WIND_V,
)


def _point(at: datetime) -> GridDomain:
    base = point_timeline_domain(hours=1)
    return GridDomain(
        axes={
            AxisName.X: base.axes[AxisName.X],
            AxisName.Y: base.axes[AxisName.Y],
            AxisName.Z: base.axes[AxisName.Z],
            AxisName.T: RegularAxis(AxisName.T, at, timedelta(hours=1), 1, False),
        }
    )


def test_capability_family_serves() -> None:
    table = StaticParameterTable.core()
    cadence = CadenceDef(
        cadence=timedelta(hours=1),
        publication_latency=timedelta(0),
        max_lead=timedelta(hours=6),
    )
    footprint = footprint_domain(STOPPED, cadence=cadence)
    temp = table.get(AIR_TEMPERATURE)
    precip = table.get(PRECIPITATION)
    leaf = FootprintCapability(footprints={AIR_TEMPERATURE: (temp, footprint)})

    inside = _point(datetime(2026, 7, 11, 14, tzinfo=UTC))
    outside = _point(datetime(2026, 7, 11, 20, tzinfo=UTC))
    assert leaf.serves(AIR_TEMPERATURE, inside) is True
    assert leaf.serves(AIR_TEMPERATURE, outside) is False
    assert leaf.serves(PRECIPITATION, inside) is False

    enumerable = EnumerableCapability(
        domain=_point(datetime(2026, 7, 11, 12, tzinfo=UTC)),
        parameters={AIR_TEMPERATURE: temp, PRECIPITATION: precip},
    )
    assert enumerable.serves(AIR_TEMPERATURE, _point(datetime(2026, 7, 11, 12, tzinfo=UTC))) is True
    assert enumerable.serves(AIR_TEMPERATURE, outside) is False

    union = UnionCapability(members=[leaf, enumerable])
    assert union.serves(AIR_TEMPERATURE, inside) is True
    assert PRECIPITATION in union.parameters

    derived = DerivedCapability(
        parameters={
            WIND_SPEED: table.get(WIND_SPEED),
            WIND_DIRECTION: table.get(WIND_DIRECTION),
        },
        inputs=frozenset({WIND_U, WIND_V}),
        upstream=FootprintCapability(
            footprints={
                WIND_U: (table.get(WIND_U), footprint),
                WIND_V: (table.get(WIND_V), footprint),
            }
        ),
    )
    assert derived.serves(WIND_SPEED, inside) is True
    assert derived.serves(WIND_DIRECTION, inside) is True
    assert derived.serves(WIND_SPEED, outside) is False
    assert derived.serves(AIR_TEMPERATURE, inside) is False
    assert set(derived.parameters) == {WIND_SPEED, WIND_DIRECTION}
