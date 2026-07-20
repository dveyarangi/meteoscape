"""Wind kernel — hypot / atan2 round-trip against Open-Meteo u/v encoding."""

from __future__ import annotations

import math
from datetime import UTC, datetime

import pytest

from fakes import point_timeline_domain
from meteoscape.identity import SourceKey
from meteoscape.manifold.capability import EnumerableCapability
from meteoscape.manifold.coverage import CoverageRecord
from meteoscape.manifold.data import ParameterData, and_present
from meteoscape.manifold.provenance import AtomicOrigin, Provenance, Uniform
from meteoscape.nodes.calculators.wind import wind_from_uv
from meteoscape.nodes.catalog.paramtable import StaticParameterTable
from meteoscape.nodes.providers.open_meteo import _u_component, _v_component
from meteoscape.parameters import WIND_DIRECTION, WIND_SPEED, WIND_U, WIND_V


def _uv_coverage(u_vals: list[float], v_vals: list[float]) -> CoverageRecord:
    table = StaticParameterTable.core()
    domain = point_timeline_domain(hours=len(u_vals), lon=13.41, lat=52.52)
    return CoverageRecord(
        capability=EnumerableCapability(
            domain=domain,
            parameters={WIND_U: table.get(WIND_U), WIND_V: table.get(WIND_V)},
        ),
        ranges={
            WIND_U: ParameterData(values=u_vals, present=None),
            WIND_V: ParameterData(values=v_vals, present=None),
        },
        provenance=Uniform(
            Provenance(
                origin=AtomicOrigin(
                    SourceKey("fake", "default"), datetime(2026, 7, 11, tzinfo=UTC)
                ),
                fetched_at=datetime(2026, 7, 11, 12, tzinfo=UTC),
                expiration=datetime(2026, 7, 11, 13, tzinfo=UTC),
            )
        ),
    )


def test_wind_round_trips_open_meteo_encoding() -> None:
    speeds = [0.0, 10.0, 3.5]
    directions = [0.0, 90.0, 225.0]
    u_vals = [_u_component(s, d) for s, d in zip(speeds, directions, strict=True)]
    v_vals = [_v_component(s, d) for s, d in zip(speeds, directions, strict=True)]
    cov = _uv_coverage(u_vals, v_vals)
    out_domain, ranges = wind_from_uv(cov)
    assert out_domain is cov.domain
    assert set(ranges) == {WIND_SPEED, WIND_DIRECTION}
    assert ranges[WIND_SPEED].present is None
    assert ranges[WIND_SPEED].values == pytest.approx(speeds)
    assert ranges[WIND_DIRECTION].values == pytest.approx(directions)


def test_present_mask_none_aware_and() -> None:
    assert and_present(None, None, n=3) is None
    assert and_present([True, False, True], None, n=3) == [True, False, True]
    assert and_present(None, [True, True, False], n=3) == [True, True, False]
    assert and_present([True, False], [True, True], n=2) == [True, False]


def test_nan_inputs_yield_nan_outputs() -> None:
    _, ranges = wind_from_uv(_uv_coverage([float("nan")], [1.0]))
    assert math.isnan(ranges[WIND_SPEED].values[0])
    assert math.isnan(ranges[WIND_DIRECTION].values[0])
