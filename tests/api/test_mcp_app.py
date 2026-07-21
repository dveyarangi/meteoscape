"""MCP `forecast_hourly` — Selection building, serialization, errors, narration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from fakes import core_parameters, point_timeline_domain
from meteoscape.api.gateway import Gateway
from meteoscape.api.mcp_app import build_mcp_app, build_selection, serialize_coverage
from meteoscape.clock import StoppedClock, floor_to
from meteoscape.errors import CapabilityMismatch, RuntimeFailure
from meteoscape.identity import SourceKey
from meteoscape.manifold.capability import EnumerableCapability
from meteoscape.manifold.core import Coverage, Manifold, Selection
from meteoscape.manifold.coverage import CoverageRecord
from meteoscape.manifold.data import ParameterData
from meteoscape.manifold.domain import AxisName, GridDomain, RegularAxis, VantageAxis
from meteoscape.manifold.provenance import AtomicOrigin, Provenance, Uniform
from meteoscape.nodes.catalog.paramtable import StaticParameterTable
from meteoscape.parameters import (
    AIR_TEMPERATURE,
    CLOUD_COVER,
    PRECIPITATION,
    RELATIVE_HUMIDITY,
    WIND_DIRECTION,
    WIND_SPEED,
    WIND_U,
)

_HORIZON = timedelta(days=7)
_CLOCK = StoppedClock(datetime(2026, 7, 11, 12, 34, tzinfo=UTC))


def _coverage(
    *,
    values: list[float] | None = None,
    present: list[bool] | None = None,
    hours: int = 2,
) -> CoverageRecord:
    domain = point_timeline_domain(hours=hours, lon=13.42, lat=52.52)
    # Force Z=2 on the native domain for serializer tests that don't care about OM snap.
    domain = type(domain)(
        axes={
            **domain.axes,
            AxisName.Z: RegularAxis(AxisName.Z, 2.0, 1.0, 1, False),
        }
    )
    table = core_parameters()
    n = hours
    return CoverageRecord(
        capability=EnumerableCapability(
            domain=domain,
            parameters={AIR_TEMPERATURE: table.get(AIR_TEMPERATURE)},
        ),
        ranges={
            AIR_TEMPERATURE: ParameterData(
                values=values if values is not None else [18.5 + i for i in range(n)],
                present=present,
            )
        },
        provenance=Uniform(
            Provenance(
                origin=AtomicOrigin(
                    SourceKey("open-meteo", "best_match"),
                    datetime(2026, 7, 11, 12, tzinfo=UTC),
                ),
                fetched_at=datetime(2026, 7, 11, 12, tzinfo=UTC),
                expiration=datetime(2026, 7, 11, 14, tzinfo=UTC),
            )
        ),
    )


class _RecordingView:
    def __init__(self, result: Coverage, parameters=None) -> None:
        self.calls: list[Selection] = []
        self._result = result
        table = core_parameters()
        pids = parameters if parameters is not None else {AIR_TEMPERATURE}
        self._parameters = {pid: table.get(pid) for pid in pids}

    async def project(self, selection: Selection) -> Manifold:
        self.calls.append(selection)
        return self._result

    @property
    def capability(self):
        return EnumerableCapability(
            domain=self._result.domain,
            parameters=self._parameters,
        )


def test_build_selection_floors_now_and_uses_vantage_z() -> None:
    table = StaticParameterTable.core()
    envelope = {AIR_TEMPERATURE: table.get(AIR_TEMPERATURE)}
    selection = build_selection(
        latitude=52.52,
        longitude=13.41,
        parameter_names=None,
        start=None,
        end=None,
        clock=_CLOCK,
        default_horizon=_HORIZON,
        envelope=envelope,
        table=table,
    )
    assert selection.parameters == frozenset({AIR_TEMPERATURE})
    # `Selection.domain` is a bare `Domain` — a curvilinear request target is left open (#12).
    domain = selection.domain
    assert isinstance(domain, GridDomain)
    assert domain.axis(AxisName.X).extent.lower == pytest.approx(13.41)
    assert domain.axis(AxisName.Y).extent.lower == pytest.approx(52.52)
    z = domain.axis(AxisName.Z)
    assert isinstance(z, VantageAxis)
    assert z.extent.lower == pytest.approx(0.0)
    assert z.extent.upper == pytest.approx(10.0)
    t = domain.axis(AxisName.T)
    assert isinstance(t, RegularAxis)
    assert t.anchor == floor_to(_CLOCK.now(), timedelta(hours=1))
    assert t.count == 168
    assert t.cellular is True


def test_build_selection_default_menu_is_exposure_intersect_capability() -> None:
    table = StaticParameterTable.core()
    envelope = {pid: table.get(pid) for pid in table}
    selection = build_selection(
        latitude=0.0,
        longitude=0.0,
        parameter_names=None,
        start=None,
        end=None,
        clock=_CLOCK,
        default_horizon=_HORIZON,
        envelope=envelope,
        table=table,
    )
    assert selection.parameters == frozenset(
        {
            AIR_TEMPERATURE,
            PRECIPITATION,
            RELATIVE_HUMIDITY,
            CLOUD_COVER,
            WIND_SPEED,
            WIND_DIRECTION,
        }
    )
    assert WIND_U not in selection.parameters


def test_build_selection_rejects_internal_wind_components() -> None:
    table = StaticParameterTable.core()
    envelope = {pid: table.get(pid) for pid in table}
    with pytest.raises(Exception, match="not requestable"):
        build_selection(
            latitude=0.0,
            longitude=0.0,
            parameter_names=["wind_u"],
            start=None,
            end=None,
            clock=_CLOCK,
            default_horizon=_HORIZON,
            envelope=envelope,
            table=table,
        )


def test_build_selection_rejects_bad_lat_lon_and_window() -> None:
    table = StaticParameterTable.core()
    envelope = {AIR_TEMPERATURE: table.get(AIR_TEMPERATURE)}
    with pytest.raises(Exception, match="latitude"):
        build_selection(
            latitude=100.0,
            longitude=0.0,
            parameter_names=None,
            start=None,
            end=None,
            clock=_CLOCK,
            default_horizon=_HORIZON,
            envelope=envelope,
            table=table,
        )
    with pytest.raises(Exception, match="longitude"):
        build_selection(
            latitude=0.0,
            longitude=200.0,
            parameter_names=None,
            start=None,
            end=None,
            clock=_CLOCK,
            default_horizon=_HORIZON,
            envelope=envelope,
            table=table,
        )
    with pytest.raises(Exception, match="start/end"):
        build_selection(
            latitude=0.0,
            longitude=0.0,
            parameter_names=None,
            start="2026-07-11T00:00:00Z",
            end=None,
            clock=_CLOCK,
            default_horizon=_HORIZON,
            envelope=envelope,
            table=table,
        )


def test_build_selection_rejects_unknown_parameter() -> None:
    table = StaticParameterTable.core()
    envelope = {AIR_TEMPERATURE: table.get(AIR_TEMPERATURE)}
    with pytest.raises(Exception, match="unknown parameter"):
        build_selection(
            latitude=0.0,
            longitude=0.0,
            parameter_names=["not_a_param"],
            start=None,
            end=None,
            clock=_CLOCK,
            default_horizon=_HORIZON,
            envelope=envelope,
            table=table,
        )


def test_serialize_coverage_schema_and_nodata() -> None:
    coverage = _coverage(values=[18.5, 0.0], present=[True, False], hours=2)
    payload = serialize_coverage(coverage)
    assert payload["valid_time"] == [
        "2026-07-11T00:00:00Z",
        "2026-07-11T01:00:00Z",
    ]
    block = payload["air_temperature"]
    assert isinstance(block, dict)
    assert block["unit"] == "degC"
    assert block["values"] == [18.5, None]
    assert block["provenance"] == {
        "source": "open-meteo:best_match",
        "exp": "2026-07-11T14:00:00Z",
    }


@pytest.mark.asyncio
async def test_tool_error_prefixes() -> None:
    class _FailingView(_RecordingView):
        def __init__(self, exc: Exception) -> None:
            super().__init__(_coverage())
            self._exc = exc

        async def project(self, selection: Selection) -> Manifold:
            raise self._exc

    async def _call(exc: Exception) -> None:
        app = build_mcp_app(Gateway(_FailingView(exc)), _CLOCK, _HORIZON)
        async with Client(app) as client:
            await client.call_tool(
                "forecast_hourly",
                {"latitude": 52.52, "longitude": 13.41},
            )

    with pytest.raises(ToolError, match=r"^capability-mismatch:"):
        await _call(CapabilityMismatch("none"))
    with pytest.raises(ToolError, match=r"^runtime-failure:"):
        await _call(RuntimeFailure("upstream"))


@pytest.mark.asyncio
async def test_forecast_hourly_builds_selection_and_narrates() -> None:
    view = _RecordingView(_coverage(hours=2))
    app = build_mcp_app(Gateway(view), _CLOCK, _HORIZON)
    tool = await app.get_tool("forecast_hourly")
    assert tool is not None
    assert "air_temperature" in (tool.description or "")
    assert "168" in (tool.description or "")
    assert "wind_u" not in (tool.description or "")

    async with Client(app) as client:
        result = await client.call_tool(
            "forecast_hourly",
            {"latitude": 52.52, "longitude": 13.41},
        )
    assert result.data["air_temperature"]["unit"] == "degC"
    assert len(view.calls) == 1
    selection = view.calls[0]
    domain = selection.domain
    assert isinstance(domain, GridDomain)
    t = domain.axis(AxisName.T)
    assert isinstance(t, RegularAxis)
    assert t.count == 168
    assert isinstance(domain.axis(AxisName.Z), VantageAxis)
    assert selection.parameters == frozenset({AIR_TEMPERATURE})


@pytest.mark.asyncio
async def test_bad_request_via_tool() -> None:
    app = build_mcp_app(Gateway(_RecordingView(_coverage())), _CLOCK, _HORIZON)
    async with Client(app) as client:
        with pytest.raises(ToolError, match=r"^bad-request:"):
            await client.call_tool(
                "forecast_hourly",
                {"latitude": 999.0, "longitude": 0.0},
            )
