"""CoverageRecord.project / private sampling engine — aligned crop."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from fakes import point_timeline_domain
from meteoscape.identity import SourceKey
from meteoscape.manifold.capability import EnumerableCapability
from meteoscape.manifold.core import Selection
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
from meteoscape.manifold.provenance import AtomicOrigin, PerParameter, Provenance, Uniform
from meteoscape.nodes.catalog.paramtable import StaticParameterTable
from meteoscape.parameters import AIR_TEMPERATURE, PRECIPITATION, WIND_U


def _params(*ids):
    table = StaticParameterTable.core()
    return {pid: table.get(pid) for pid in ids}


def _prov(pid_stamp: str = "fake") -> Provenance:
    return Provenance(
        origin=AtomicOrigin(SourceKey(pid_stamp, "default"), datetime(2026, 7, 11, tzinfo=UTC)),
        fetched_at=datetime(2026, 7, 11, 12, tzinfo=UTC),
        expiration=datetime(2026, 7, 11, 13, tzinfo=UTC),
    )


def _record(
    domain: GridDomain,
    *,
    values: dict | None = None,
    present: dict | None = None,
    provenance=None,
) -> CoverageRecord:
    parameters = _params(AIR_TEMPERATURE, PRECIPITATION)
    n = len(domain)
    ranges = {
        pid: ParameterData(
            values=(values or {}).get(pid, [float(i) for i in range(n)]),
            present=(present or {}).get(pid),
        )
        for pid in parameters
    }
    return CoverageRecord(
        capability=EnumerableCapability(domain=domain, parameters=parameters),
        ranges=ranges,
        provenance=provenance or Uniform(_prov()),
    )


async def _project(record: CoverageRecord, selection: Selection) -> CoverageRecord:
    result = await record.project(selection)
    assert isinstance(result, CoverageRecord)
    return result


@pytest.mark.asyncio
async def test_identity_projection() -> None:
    domain = point_timeline_domain(hours=4)
    record = _record(domain)
    selection = Selection(domain=domain, parameters=frozenset(record.capability.parameters))
    assert await _project(record, selection) == record


@pytest.mark.asyncio
async def test_parameter_subset_restricts_ranges_and_capability() -> None:
    domain = point_timeline_domain(hours=3)
    record = _record(domain)
    selection = Selection(domain=domain, parameters=frozenset({AIR_TEMPERATURE}))
    result = await _project(record, selection)
    assert set(result.capability.parameters) == {AIR_TEMPERATURE}
    assert set(result.ranges) == {AIR_TEMPERATURE}
    assert result.ranges[AIR_TEMPERATURE] == record.ranges[AIR_TEMPERATURE]
    assert result.provenance is record.provenance
    assert PRECIPITATION not in result.capability.parameters


@pytest.mark.asyncio
async def test_parameter_subset_restricts_per_parameter_provenance() -> None:
    domain = point_timeline_domain(hours=2)
    temp_p, precip_p = _prov("temp"), _prov("precip")
    record = _record(
        domain,
        provenance=PerParameter({AIR_TEMPERATURE: temp_p, PRECIPITATION: precip_p}),
    )
    result = await _project(
        record, Selection(domain=domain, parameters=frozenset({AIR_TEMPERATURE}))
    )
    assert isinstance(result.provenance, PerParameter)
    assert set(result.provenance.by_parameter) == {AIR_TEMPERATURE}
    assert result.provenance.by_parameter[AIR_TEMPERATURE] is temp_p


@pytest.mark.asyncio
async def test_aligned_valid_time_crop() -> None:
    domain = point_timeline_domain(hours=6)
    record = _record(
        domain,
        values={AIR_TEMPERATURE: [10.0, 11.0, 12.0, 13.0, 14.0, 15.0]},
        present={AIR_TEMPERATURE: [True, True, False, True, True, True]},
    )
    cropped_domain = GridDomain(
        axes={
            AxisName.X: domain.axes[AxisName.X],
            AxisName.Y: domain.axes[AxisName.Y],
            AxisName.Z: domain.axes[AxisName.Z],
            AxisName.T: RegularAxis(
                AxisName.T, datetime(2026, 7, 11, 1, tzinfo=UTC), timedelta(hours=1), 3, False
            ),
        }
    )
    result = await _project(
        record, Selection(domain=cropped_domain, parameters=frozenset({AIR_TEMPERATURE}))
    )
    assert result.domain == cropped_domain
    assert list(result.ranges[AIR_TEMPERATURE].values) == [11.0, 12.0, 13.0]
    temp = result.ranges[AIR_TEMPERATURE]
    assert temp.is_present(0) is True
    assert temp.is_present(1) is False
    assert temp.is_present(2) is True
    assert result.provenance is record.provenance


@pytest.mark.asyncio
async def test_crop_away_absent_ticks_yields_all_present() -> None:
    domain = point_timeline_domain(hours=4)
    record = _record(
        domain,
        values={AIR_TEMPERATURE: [10.0, 11.0, 12.0, 13.0]},
        present={AIR_TEMPERATURE: [False, True, True, False]},
    )
    cropped_domain = GridDomain(
        axes={
            AxisName.X: domain.axes[AxisName.X],
            AxisName.Y: domain.axes[AxisName.Y],
            AxisName.Z: domain.axes[AxisName.Z],
            AxisName.T: RegularAxis(
                AxisName.T, datetime(2026, 7, 11, 1, tzinfo=UTC), timedelta(hours=1), 2, False
            ),
        }
    )
    result = await _project(
        record, Selection(domain=cropped_domain, parameters=frozenset({AIR_TEMPERATURE}))
    )
    temp = result.ranges[AIR_TEMPERATURE]
    assert list(temp.values) == [11.0, 12.0]
    assert all(temp.is_present(i) for i in range(2))
    assert temp.present is None


@pytest.mark.asyncio
async def test_parameter_not_held_raises_value_error() -> None:
    domain = point_timeline_domain(hours=2)
    record = _record(domain)
    with pytest.raises(ValueError, match="not held"):
        await record.project(Selection(domain=domain, parameters=frozenset({WIND_U})))


@pytest.mark.asyncio
async def test_off_phase_and_continuous_raise_not_implemented() -> None:
    domain = point_timeline_domain(hours=4)
    record = _record(domain)

    off_phase = GridDomain(
        axes={
            AxisName.X: domain.axes[AxisName.X],
            AxisName.Y: domain.axes[AxisName.Y],
            AxisName.Z: domain.axes[AxisName.Z],
            AxisName.T: RegularAxis(
                AxisName.T,
                datetime(2026, 7, 11, 0, 30, tzinfo=UTC),
                timedelta(hours=1),
                2,
                False,
            ),
        }
    )
    with pytest.raises(NotImplementedError, match="non-identical step or off-phase"):
        await record.project(Selection(domain=off_phase, parameters=frozenset({AIR_TEMPERATURE})))

    continuous = FootprintDomain(
        axes={
            AxisName.X: ContinuousAxis(AxisName.X, Interval(1.0, 1.0)),
            AxisName.Y: ContinuousAxis(AxisName.Y, Interval(2.0, 2.0)),
            AxisName.Z: ContinuousAxis(AxisName.Z, Interval(0.0, 0.0)),
            AxisName.T: ContinuousAxis(
                AxisName.T,
                Interval(datetime(2026, 7, 11, tzinfo=UTC), datetime(2026, 7, 11, 3, tzinfo=UTC)),
            ),
        }
    )
    with pytest.raises(NotImplementedError, match="continuous"):
        await record.project(Selection(domain=continuous, parameters=frozenset({AIR_TEMPERATURE})))


@pytest.mark.asyncio
async def test_vantage_z_identity_crop() -> None:
    """Non-RegularAxis Z uses identity offset — closed projection rides the vantage cell."""
    from meteoscape.manifold.domain import VantageAxis

    domain = GridDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 1.0, 1.0, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, 2.0, 1.0, 1, False),
            AxisName.Z: VantageAxis(AxisName.Z, Interval(0.0, 10.0)),
            AxisName.T: RegularAxis(
                AxisName.T, datetime(2026, 7, 11, tzinfo=UTC), timedelta(hours=1), 3, False
            ),
        }
    )
    record = _record(
        domain,
        values={AIR_TEMPERATURE: [10.0, 11.0, 12.0]},
    )
    cropped = GridDomain(
        axes={
            AxisName.X: domain.axes[AxisName.X],
            AxisName.Y: domain.axes[AxisName.Y],
            AxisName.Z: domain.axes[AxisName.Z],
            AxisName.T: RegularAxis(
                AxisName.T, datetime(2026, 7, 11, 1, tzinfo=UTC), timedelta(hours=1), 2, False
            ),
        }
    )
    result = await _project(
        record, Selection(domain=cropped, parameters=frozenset({AIR_TEMPERATURE}))
    )
    assert result.domain == cropped
    assert list(result.ranges[AIR_TEMPERATURE].values) == [11.0, 12.0]
    assert isinstance(result.domain, GridDomain)
    assert isinstance(result.domain.axes[AxisName.Z], VantageAxis)
