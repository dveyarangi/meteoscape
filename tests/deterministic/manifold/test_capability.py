"""Capability family — serves predicates over real Domain.contains, and per-parameter reach."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import assert_type

import pytest

from fakes import STOPPED, footprint_domain, point_timeline_domain
from meteoscape.identity import SourceKey
from meteoscape.manifold.cadence import CadenceDef
from meteoscape.manifold.capability import (
    DerivedCapability,
    EnumerableCapability,
    GranularCapability,
    UnionCapability,
)
from meteoscape.manifold.domain import (
    AxisName,
    Domain,
    EnumerableDomain,
    GridDomain,
    RegularAxis,
    ScatterDomain,
)
from meteoscape.manifold.provenance import AtomicOrigin
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
    leaf = GranularCapability(reaches={AIR_TEMPERATURE: (temp, footprint)})

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

    union = UnionCapability(
        members={SourceKey("a", "default"): leaf, SourceKey("b", "default"): enumerable},
        domains={AIR_TEMPERATURE: footprint, PRECIPITATION: enumerable.domain},
    )
    assert union.serves(AIR_TEMPERATURE, inside) is True
    assert PRECIPITATION in union.parameters

    derived = DerivedCapability(
        parameters={
            WIND_SPEED: table.get(WIND_SPEED),
            WIND_DIRECTION: table.get(WIND_DIRECTION),
        },
        inputs=frozenset({WIND_U, WIND_V}),
        upstream=GranularCapability(
            reaches={
                WIND_U: (table.get(WIND_U), footprint),
                WIND_V: (table.get(WIND_V), footprint),
            }
        ),
        domain=footprint,
    )
    assert derived.serves(WIND_SPEED, inside) is True
    assert derived.serves(WIND_DIRECTION, inside) is True
    assert derived.serves(WIND_SPEED, outside) is False
    assert derived.serves(AIR_TEMPERATURE, inside) is False
    assert set(derived.parameters) == {WIND_SPEED, WIND_DIRECTION}


# ---- reach: the per-parameter Domain a leaf publishes (ADR-0007) --------------------------------


class _NonSeparable(Domain):
    """A Domain with no per-axis decomposition — a curvilinear stand-in (never Separable)."""

    def matches(self, other: Domain) -> bool:
        return False

    def intersect(self, other: Domain) -> Domain:
        raise NotImplementedError


def _cadence() -> CadenceDef:
    return CadenceDef(
        cadence=timedelta(hours=1),
        publication_latency=timedelta(0),
        max_lead=timedelta(hours=6),
    )


def test_granular_capability_reach_returns_the_declared_footprint() -> None:
    table = StaticParameterTable.core()
    footprint = footprint_domain(STOPPED, cadence=_cadence())
    leaf = GranularCapability(reaches={AIR_TEMPERATURE: (table.get(AIR_TEMPERATURE), footprint)})

    assert leaf.reach(AIR_TEMPERATURE) is footprint
    with pytest.raises(KeyError):
        leaf.reach(PRECIPITATION)


def test_enumerable_capability_reach_narrows_to_enumerable_domain() -> None:
    table = StaticParameterTable.core()
    domain = _point(datetime(2026, 7, 11, 12, tzinfo=UTC))
    leaf = EnumerableCapability(
        domain=domain,
        parameters={AIR_TEMPERATURE: table.get(AIR_TEMPERATURE)},
    )

    reach = leaf.reach(AIR_TEMPERATURE)
    # The shared grid is part of this capability form's type contract, not only its runtime value.
    assert_type(reach, EnumerableDomain)
    assert reach is domain
    with pytest.raises(KeyError):
        leaf.reach(PRECIPITATION)


def test_granular_capability_reach_returns_a_lone_non_separable_unchanged() -> None:
    """A lone non-separable reach is published unchanged because nothing must be compared."""
    table = StaticParameterTable.core()
    curvilinear = _NonSeparable()
    leaf = GranularCapability(reaches={AIR_TEMPERATURE: (table.get(AIR_TEMPERATURE), curvilinear)})

    assert leaf.reach(AIR_TEMPERATURE) is curvilinear


# ---- DerivedCapability: a carrier — reach is the domain its Calculator composed (ADR-0007) ------


def test_derived_capability_carries_the_composed_domain() -> None:
    table = StaticParameterTable.core()
    footprint = footprint_domain(STOPPED, cadence=_cadence())
    derived = DerivedCapability(
        parameters={WIND_SPEED: table.get(WIND_SPEED)},
        inputs=frozenset({WIND_U, WIND_V}),
        upstream=GranularCapability(
            reaches={
                WIND_U: (table.get(WIND_U), footprint),
                WIND_V: (table.get(WIND_V), footprint),
            }
        ),
        domain=footprint,
    )
    assert derived.reach(WIND_SPEED) is footprint
    with pytest.raises(KeyError):
        derived.reach(AIR_TEMPERATURE)


# ---- origins: declared provenance over the reach (ADR-0003) -------------------------------------


def test_unbound_granular_capability_declares_no_origins() -> None:
    """Served-but-undeclared is empty; unserved is KeyError — the same split as reach()."""
    table = StaticParameterTable.core()
    footprint = footprint_domain(STOPPED, cadence=_cadence())
    leaf = GranularCapability(reaches={AIR_TEMPERATURE: (table.get(AIR_TEMPERATURE), footprint)})
    assert leaf.origins(AIR_TEMPERATURE) == ()
    with pytest.raises(KeyError):
        leaf.origins(PRECIPITATION)


_RUSSEL = (-33.0129, -68.7473)
_MENDOZA = (-32.890, -68.845)
_OBS = SourceKey("collector-obs", "stations")


def _station_scatter(*points: tuple[float, float]) -> ScatterDomain:
    noon = datetime(2026, 7, 11, 12, tzinfo=UTC)
    return ScatterDomain(
        points=points,
        t=RegularAxis(AxisName.T, noon, timedelta(hours=1), 4, False),
        z=RegularAxis(AxisName.Z, 2.0, 1.0, 1, False),
    )


def test_scatter_capability_publishes_origins_before_any_request() -> None:
    table = StaticParameterTable.core()
    reach = _station_scatter(_RUSSEL, _MENDOZA)
    russel = _station_scatter(_RUSSEL)
    mendoza = _station_scatter(_MENDOZA)
    leaf = GranularCapability(
        reaches={AIR_TEMPERATURE: (table.get(AIR_TEMPERATURE), reach)},
        declared_origins={
            AIR_TEMPERATURE: (
                (
                    russel,
                    AtomicOrigin(
                        _OBS, None, authority="agrometeo", process="instant", unit="Russel"
                    ),
                ),
                (
                    mendoza,
                    AtomicOrigin(
                        _OBS, None, authority="agrometeo", process="instant", unit="Mendoza"
                    ),
                ),
            )
        },
    )

    entries = leaf.origins(AIR_TEMPERATURE)
    published: list[ScatterDomain] = []
    units: list[str | None] = []
    # Containment of declared data, not matches() between two declared domains (ADR-0003).
    for place, origin in entries:
        assert isinstance(place, ScatterDomain)
        assert origin.issue_time is None
        assert set(place.points) <= set(reach.points)
        assert reach.t.extent.contains(place.t.extent)
        assert reach.z.extent.contains(place.z.extent)
        published.append(place)
        units.append(origin.unit)
    assert [place.points for place in published] == [(_RUSSEL,), (_MENDOZA,)]
    assert units == ["Russel", "Mendoza"]


def test_enumerable_capability_declares_no_origins() -> None:
    table = StaticParameterTable.core()
    leaf = EnumerableCapability(
        domain=_point(datetime(2026, 7, 11, 12, tzinfo=UTC)),
        parameters={AIR_TEMPERATURE: table.get(AIR_TEMPERATURE)},
    )
    assert leaf.origins(AIR_TEMPERATURE) == ()
    with pytest.raises(KeyError):
        leaf.origins(PRECIPITATION)


def test_derived_capability_declares_no_origins() -> None:
    table = StaticParameterTable.core()
    footprint = footprint_domain(STOPPED, cadence=_cadence())
    derived = DerivedCapability(
        parameters={WIND_SPEED: table.get(WIND_SPEED)},
        inputs=frozenset({WIND_U, WIND_V}),
        upstream=GranularCapability(
            reaches={
                WIND_U: (table.get(WIND_U), footprint),
                WIND_V: (table.get(WIND_V), footprint),
            }
        ),
        domain=footprint,
    )
    assert derived.origins(WIND_SPEED) == ()
    with pytest.raises(KeyError):
        derived.origins(AIR_TEMPERATURE)


def test_union_capability_concatenates_origins_in_bind_order() -> None:
    table = StaticParameterTable.core()
    reach = _station_scatter(_RUSSEL, _MENDOZA)
    footprint = footprint_domain(STOPPED, cadence=_cadence())
    first = GranularCapability(
        reaches={AIR_TEMPERATURE: (table.get(AIR_TEMPERATURE), reach)},
        declared_origins={
            AIR_TEMPERATURE: (
                (
                    _station_scatter(_RUSSEL),
                    AtomicOrigin(
                        _OBS, None, authority="agrometeo", process="instant", unit="Russel"
                    ),
                ),
            )
        },
    )
    precip_only = GranularCapability(reaches={PRECIPITATION: (table.get(PRECIPITATION), footprint)})
    second = GranularCapability(
        reaches={AIR_TEMPERATURE: (table.get(AIR_TEMPERATURE), reach)},
        declared_origins={
            AIR_TEMPERATURE: (
                (
                    _station_scatter(_MENDOZA),
                    AtomicOrigin(
                        _OBS, None, authority="agrometeo", process="instant", unit="Mendoza"
                    ),
                ),
            )
        },
    )
    union = UnionCapability(
        members={
            SourceKey("obs", "west"): first,
            SourceKey("obs", "precip"): precip_only,
            SourceKey("obs", "east"): second,
        },
        domains={AIR_TEMPERATURE: reach, PRECIPITATION: footprint},
    )

    units = [origin.unit for _, origin in union.origins(AIR_TEMPERATURE)]
    assert units == ["Russel", "Mendoza"]
    with pytest.raises(KeyError):
        union.origins(WIND_SPEED)
