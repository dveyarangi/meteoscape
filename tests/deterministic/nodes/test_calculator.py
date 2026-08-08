"""Calculator node — multi-output project, provenance propagation, well-formedness."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from fakes import point_timeline_domain
from meteoscape.errors import CompositionError, RuntimeFailure
from meteoscape.identity import CalculatorKey, SourceKey
from meteoscape.manifold.capability import EnumerableCapability, GranularCapability
from meteoscape.manifold.core import Manifold, Selection
from meteoscape.manifold.coverage import CoverageRecord
from meteoscape.manifold.data import ParameterData
from meteoscape.manifold.domain import (
    AxisName,
    ContinuousAxis,
    Domain,
    FootprintDomain,
    GridDomain,
    Interval,
    RegularAxis,
)
from meteoscape.manifold.provenance import AtomicOrigin, Provenance, Uniform
from meteoscape.nodes.calculator import Calculator
from meteoscape.nodes.calculators.wind import wind_from_uv
from meteoscape.nodes.catalog.paramtable import StaticParameterTable
from meteoscape.nodes.providers.normalization import u_component, v_component
from meteoscape.parameters import WIND_DIRECTION, WIND_SPEED, WIND_U, WIND_V


class _FixedResolver:
    def __init__(self, coverage: CoverageRecord) -> None:
        self.coverage = coverage
        self.calls: list[Selection] = []

    async def project(self, selection: Selection) -> Manifold:
        self.calls.append(selection)
        return self.coverage

    @property
    def capability(self):
        table = StaticParameterTable.core()
        footprint = FootprintDomain(
            axes={
                AxisName.X: ContinuousAxis(AxisName.X, Interval(-180.0, 180.0)),
                AxisName.Y: ContinuousAxis(AxisName.Y, Interval(-90.0, 90.0)),
                AxisName.Z: ContinuousAxis(AxisName.Z, Interval(0.0, 100.0)),
                AxisName.T: ContinuousAxis(
                    AxisName.T,
                    Interval(datetime(2026, 7, 1, tzinfo=UTC), datetime(2026, 8, 1, tzinfo=UTC)),
                ),
            }
        )
        return GranularCapability(
            reaches={
                WIND_U: (table.get(WIND_U), footprint),
                WIND_V: (table.get(WIND_V), footprint),
            }
        )


def _uv_input(*, speed: float = 10.0, direction: float = 90.0) -> CoverageRecord:
    table = StaticParameterTable.core()
    domain = point_timeline_domain(hours=1, lon=13.41, lat=52.52)
    origin = AtomicOrigin(SourceKey("open-meteo", "best_match"), datetime(2026, 7, 11, tzinfo=UTC))
    return CoverageRecord(
        capability=EnumerableCapability(
            domain=domain,
            parameters={WIND_U: table.get(WIND_U), WIND_V: table.get(WIND_V)},
        ),
        ranges={
            WIND_U: ParameterData(values=[u_component(speed, direction)], present=None),
            WIND_V: ParameterData(values=[v_component(speed, direction)], present=None),
        },
        provenance=Uniform(
            Provenance(
                origin=origin,
                fetched_at=datetime(2026, 7, 11, 12, tzinfo=UTC),
                expiration=datetime(2026, 7, 11, 13, tzinfo=UTC),
            )
        ),
    )


def _selection() -> Selection:
    return Selection(
        domain=GridDomain(
            axes={
                AxisName.X: RegularAxis(AxisName.X, 13.41, 1.0, 1, False),
                AxisName.Y: RegularAxis(AxisName.Y, 52.52, 1.0, 1, False),
                AxisName.Z: RegularAxis(AxisName.Z, 10.0, 1.0, 1, False),
                AxisName.T: RegularAxis(
                    AxisName.T,
                    datetime(2026, 7, 11, 12, tzinfo=UTC),
                    timedelta(hours=1),
                    1,
                    True,
                ),
            }
        ),
        parameters=frozenset({WIND_SPEED, WIND_DIRECTION}),
    )


@pytest.mark.asyncio
async def test_calculator_propagates_input_origin_and_emits_both_outputs() -> None:
    table = StaticParameterTable.core()
    inp = _uv_input()
    resolver = _FixedResolver(inp)
    calc = Calculator(
        key=CalculatorKey("wind", "default"),
        outputs={
            WIND_SPEED: table.get(WIND_SPEED),
            WIND_DIRECTION: table.get(WIND_DIRECTION),
        },
        inputs=frozenset({WIND_U, WIND_V}),
        fn=wind_from_uv,
        resolver=resolver,
    )
    result = await calc.project(_selection())
    assert isinstance(result, CoverageRecord)
    assert set(result.ranges) == {WIND_SPEED, WIND_DIRECTION}
    assert result.ranges[WIND_SPEED].values == pytest.approx([10.0])
    assert result.ranges[WIND_DIRECTION].values == pytest.approx([90.0])
    origin = result.provenance.summary(WIND_SPEED).origin
    assert isinstance(origin, AtomicOrigin)
    assert origin.source == SourceKey("open-meteo", "best_match")
    assert len(resolver.calls) == 1
    assert resolver.calls[0].parameters == frozenset({WIND_U, WIND_V})
    assert calc.capability.serves(WIND_SPEED, _selection().domain)
    assert calc.capability.serves(WIND_DIRECTION, _selection().domain)


@pytest.mark.asyncio
async def test_calculator_rejects_malformed_kernel_ranges() -> None:
    table = StaticParameterTable.core()
    resolver = _FixedResolver(_uv_input())

    def bad_fn(cov):
        return cov.domain, {WIND_SPEED: ParameterData(values=[1.0], present=None)}

    calc = Calculator(
        key=CalculatorKey("wind", "default"),
        outputs={
            WIND_SPEED: table.get(WIND_SPEED),
            WIND_DIRECTION: table.get(WIND_DIRECTION),
        },
        inputs=frozenset({WIND_U, WIND_V}),
        fn=bad_fn,
        resolver=resolver,
    )
    with pytest.raises(RuntimeFailure, match="ranges"):
        await calc.project(_selection())


# --- The Calculator composes its reach eagerly at construction (ADR-0007) ---

_T0 = datetime(2026, 7, 11, 12, tzinfo=UTC)
_GLOBAL_X = Interval(-180.0, 180.0)


class _CapabilityOnlyResolver:
    """A resolver stub for construction-time reach tests; the fold never projects."""

    def __init__(self, capability: GranularCapability) -> None:
        self._capability = capability

    async def project(self, selection: Selection) -> Manifold:
        raise AssertionError("the reach fold never projects")

    @property
    def capability(self) -> GranularCapability:
        return self._capability


def _fp(*, x: Interval[float] = _GLOBAL_X, days: int) -> FootprintDomain:
    return FootprintDomain(
        axes={
            AxisName.X: ContinuousAxis(AxisName.X, x),
            AxisName.Y: ContinuousAxis(AxisName.Y, Interval(-90.0, 90.0)),
            AxisName.Z: ContinuousAxis(AxisName.Z, Interval(0.0, 0.0)),
            AxisName.T: ContinuousAxis(AxisName.T, Interval(_T0, _T0 + timedelta(days=days))),
        }
    )


def _wind_calc(u: Domain, v: Domain) -> Calculator:
    table = StaticParameterTable.core()
    upstream = GranularCapability(
        reaches={WIND_U: (table.get(WIND_U), u), WIND_V: (table.get(WIND_V), v)}
    )
    return Calculator(
        key=CalculatorKey("wind", "default"),
        outputs={WIND_SPEED: table.get(WIND_SPEED)},
        inputs=frozenset({WIND_U, WIND_V}),
        fn=wind_from_uv,
        resolver=_CapabilityOnlyResolver(upstream),
    )


def test_calculator_reach_is_the_input_contained_in_all() -> None:
    small = _fp(days=10)
    calc = _wind_calc(small, _fp(days=16))
    assert calc.capability.reach(WIND_SPEED) is small


def test_calculator_reach_equal_extent_tie_returns_an_input() -> None:
    """v1's derived wind hits this on every parameter: `wind_u` / `wind_v` are distinct objects with
    equal extents, so any may be returned (ADR-0007)."""
    u = _fp(days=10)
    v = _fp(days=10)
    assert u is not v
    reach = _wind_calc(u, v).capability.reach(WIND_SPEED)
    assert reach is u or reach is v


def test_calculator_sheared_inputs_fail_the_build_naming_calculator_and_inputs() -> None:
    globe = _fp(x=Interval(-180.0, 180.0), days=10)
    europe = _fp(x=Interval(-10.0, 40.0), days=16)
    with pytest.raises(CompositionError) as exc:
        _wind_calc(globe, europe)
    message = str(exc.value)
    assert "shear" in message
    assert "wind:default" in message  # Identifies the calculator an operator must fix.
    assert "wind_u" in message and "wind_v" in message


class _NonSeparable(Domain):
    """Curvilinear stand-in: satisfies `Domain`, exposes no axes (concern #12, source role)."""

    def matches(self, other: Domain) -> bool:
        return False

    def intersect(self, other: Domain) -> Domain:
        return self


def test_calculator_non_separable_input_among_several_fails_the_build() -> None:
    with pytest.raises(CompositionError) as exc:
        _wind_calc(_NonSeparable(), _fp(days=10))
    message = str(exc.value)
    assert "wind:default" in message
    assert "wind_u" in message
    assert "separable" in message.lower()
