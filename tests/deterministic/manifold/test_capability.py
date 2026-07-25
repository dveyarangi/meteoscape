"""Capability family — serves predicates over real Domain.contains, and per-parameter reach."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import assert_type

import pytest

from fakes import STOPPED, footprint_domain, point_timeline_domain
from meteoscape.errors import CompositionError
from meteoscape.identity import CalculatorKey, SourceKey
from meteoscape.manifold.cadence import CadenceDef
from meteoscape.manifold.capability import (
    DerivedCapability,
    EnumerableCapability,
    FootprintCapability,
    UnionCapability,
)
from meteoscape.manifold.domain import (
    AxisName,
    ContinuousAxis,
    Domain,
    EnumerableDomain,
    FootprintDomain,
    GridDomain,
    Interval,
    RegularAxis,
)
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

    union = UnionCapability(
        members={SourceKey("a", "default"): leaf, SourceKey("b", "default"): enumerable},
        domains={AIR_TEMPERATURE: footprint, PRECIPITATION: enumerable.domain},
    )
    assert union.serves(AIR_TEMPERATURE, inside) is True
    assert PRECIPITATION in union.parameters

    derived = DerivedCapability(
        key=CalculatorKey("wind", "default"),
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


def test_footprint_capability_reach_returns_the_declared_footprint() -> None:
    table = StaticParameterTable.core()
    footprint = footprint_domain(STOPPED, cadence=_cadence())
    leaf = FootprintCapability(
        footprints={AIR_TEMPERATURE: (table.get(AIR_TEMPERATURE), footprint)}
    )

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
    assert_type(
        reach, EnumerableDomain
    )  # the materialized form narrows in the type, not just value
    assert reach is domain
    with pytest.raises(KeyError):
        leaf.reach(PRECIPITATION)


def test_footprint_capability_reach_returns_a_lone_non_separable_unchanged() -> None:
    """reach is a plain lookup: a single non-separable footprint is served as-is — the ex-build-time
    reach pass rejected it, but a leaf now just publishes what it declares (ADR-0007, defect 3)."""
    table = StaticParameterTable.core()
    curvilinear = _NonSeparable()
    leaf = FootprintCapability(
        footprints={AIR_TEMPERATURE: (table.get(AIR_TEMPERATURE), curvilinear)}
    )

    assert leaf.reach(AIR_TEMPERATURE) is curvilinear


# ---- DerivedCapability.reach: contained-in-all over inputs, eager at construction (ADR-0007) -----

_T0 = datetime(2026, 7, 11, 12, tzinfo=UTC)
_GLOBAL_X = Interval(-180.0, 180.0)


def _fp(*, x: Interval[float] = _GLOBAL_X, days: int) -> FootprintDomain:
    return FootprintDomain(
        axes={
            AxisName.X: ContinuousAxis(AxisName.X, x),
            AxisName.Y: ContinuousAxis(AxisName.Y, Interval(-90.0, 90.0)),
            AxisName.Z: ContinuousAxis(AxisName.Z, Interval(0.0, 0.0)),
            AxisName.T: ContinuousAxis(AxisName.T, Interval(_T0, _T0 + timedelta(days=days))),
        }
    )


def _wind_upstream(u: FootprintDomain, v: FootprintDomain) -> FootprintCapability:
    table = StaticParameterTable.core()
    return FootprintCapability(
        footprints={WIND_U: (table.get(WIND_U), u), WIND_V: (table.get(WIND_V), v)}
    )


def _derived(upstream: FootprintCapability) -> DerivedCapability:
    return DerivedCapability(
        key=CalculatorKey("wind", "default"),
        parameters={WIND_SPEED: StaticParameterTable.core().get(WIND_SPEED)},
        inputs=frozenset({WIND_U, WIND_V}),
        upstream=upstream,
    )


def test_derived_capability_reach_is_the_input_contained_in_all() -> None:
    small = _fp(days=10)
    large = _fp(days=16)
    derived = _derived(_wind_upstream(small, large))
    assert derived.reach(WIND_SPEED) is small


def test_derived_capability_reach_equal_extent_tie_returns_an_input() -> None:
    """v1's derived wind hits this on every parameter: `wind_u` / `wind_v` are distinct objects with
    equal extents, so any may be returned (ADR-0007)."""
    u = _fp(days=10)
    v = _fp(days=10)
    assert u is not v
    reach = _derived(_wind_upstream(u, v)).reach(WIND_SPEED)
    assert reach is u or reach is v


def test_derived_capability_sheared_inputs_raise_naming_the_calculator_and_inputs() -> None:
    globe = _fp(x=Interval(-180.0, 180.0), days=10)
    europe = _fp(x=Interval(-10.0, 40.0), days=16)
    with pytest.raises(CompositionError) as exc:
        _derived(_wind_upstream(globe, europe))
    message = str(exc.value)
    assert "shear" in message
    assert "wind:default" in message  # the calculator an operator must fix (defect 2)
    assert "wind_u" in message and "wind_v" in message
