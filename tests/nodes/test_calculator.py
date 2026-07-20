"""Calculator node — multi-output project, provenance propagation, well-formedness."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from fakes import point_timeline_domain
from meteoscape.errors import RuntimeFailure
from meteoscape.identity import SourceKey
from meteoscape.manifold.capability import EnumerableCapability, FootprintCapability
from meteoscape.manifold.core import Manifold, Selection
from meteoscape.manifold.coverage import CoverageRecord
from meteoscape.manifold.data import ParameterData
from meteoscape.manifold.domain import (
    AxisName,
    ContinuousAxis,
    FootprintDomain,
    GridDomain,
    Interval,
    RegularAxis,
)
from meteoscape.manifold.provenance import AtomicOrigin, Provenance, Uniform
from meteoscape.nodes.calculator import Calculator
from meteoscape.nodes.calculators.wind import wind_from_uv
from meteoscape.nodes.catalog.paramtable import StaticParameterTable
from meteoscape.nodes.providers.open_meteo import _u_component, _v_component
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
        return FootprintCapability(
            footprints={
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
            WIND_U: ParameterData(values=[_u_component(speed, direction)], present=None),
            WIND_V: ParameterData(values=[_v_component(speed, direction)], present=None),
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
