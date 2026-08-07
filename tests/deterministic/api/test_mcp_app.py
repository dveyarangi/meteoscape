"""MCP `forecast_hourly` — Selection building, serialization, errors, narration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from fakes import STOPPED, core_parameters, footprint_capability, point_timeline_domain
from meteoscape.api.gateway import Gateway
from meteoscape.api.mcp_app import build_mcp_app, build_selection, serialize_coverage
from meteoscape.clock import StoppedClock
from meteoscape.errors import BadRequest, CapabilityMismatch, RuntimeFailure
from meteoscape.identity import SourceKey
from meteoscape.manifold.cadence import CadenceDef
from meteoscape.manifold.capability import Capability, EnumerableCapability
from meteoscape.manifold.core import Coverage, Manifold, Selection
from meteoscape.manifold.coverage import CoverageRecord
from meteoscape.manifold.data import ParameterData
from meteoscape.manifold.domain import (
    AxisName,
    FootprintDomain,
    Interval,
    RegularAxis,
    SelectionDomain,
    SnappedAxis,
    VantageAxis,
)
from meteoscape.manifold.provenance import AtomicOrigin, Provenance, Uniform
from meteoscape.parameters import (
    AIR_TEMPERATURE,
    CLOUD_COVER,
    PRECIPITATION,
    RELATIVE_HUMIDITY,
    WIND_DIRECTION,
    WIND_SPEED,
    WIND_U,
    ParameterId,
)

# Mid-hour on purpose: raw instants must ride unfloored — the production Metronome floors to the
# hour, so only a mid-hour StoppedClock exercises the raw rule directly (RFC 0008 fact 7).
_CLOCK = StoppedClock(datetime(2026, 7, 11, 12, 34, tzinfo=UTC))


def _capability(*pids: ParameterId) -> Capability:
    """A rolling-reach envelope under the test clock — reach folds are asserted against it."""
    return footprint_capability(_CLOCK, core_parameters(), frozenset(pids))


def _reach_end(capability: Capability, pid: ParameterId = AIR_TEMPERATURE) -> datetime:
    reach = capability.reach(pid)
    assert isinstance(reach, FootprintDomain)
    upper = reach.axis(AxisName.T).extent.upper
    assert isinstance(upper, datetime)
    return upper


def _build(
    *,
    latitude: float = 52.52,
    longitude: float = 13.41,
    parameter_names: list[str] | None = None,
    start: str | None = None,
    end: str | None = None,
    capability: Capability | None = None,
) -> Selection:
    return build_selection(
        latitude=latitude,
        longitude=longitude,
        parameter_names=parameter_names,
        start=start,
        end=end,
        clock=_CLOCK,
        capability=capability if capability is not None else _capability(AIR_TEMPERATURE),
        table=core_parameters(),
    )


def _snapped_t(selection: Selection) -> SnappedAxis:
    domain = selection.domain
    assert isinstance(domain, SelectionDomain)
    t = domain.axis(AxisName.T)
    assert isinstance(t, SnappedAxis)
    return t


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
    def __init__(
        self,
        result: Coverage,
        parameters=None,
        *,
        cadence=None,
    ) -> None:
        self.calls: list[Selection] = []
        self._result = result
        pids = parameters if parameters is not None else {AIR_TEMPERATURE}
        self._pids = frozenset(pids)
        self._cadence = cadence

    async def project(self, selection: Selection) -> Manifold:
        self.calls.append(selection)
        return self._result

    @property
    def capability(self):
        # A rolling footprint, not the canned coverage's 2-hour lattice: the reach fold for an
        # omitted `end` must land after `now`, or every defaulted request degenerates (RFC 0008).
        return footprint_capability(STOPPED, core_parameters(), self._pids, cadence=self._cadence)


def test_build_selection_authors_snapped_window_and_vantage_z() -> None:
    capability = _capability(AIR_TEMPERATURE)
    selection = _build(capability=capability)
    assert selection.parameters == frozenset({AIR_TEMPERATURE})
    domain = selection.domain
    assert isinstance(domain, SelectionDomain)
    assert domain.axis(AxisName.X).extent.lower == pytest.approx(13.41)
    assert domain.axis(AxisName.Y).extent.lower == pytest.approx(52.52)
    z = domain.axis(AxisName.Z)
    assert isinstance(z, VantageAxis)
    assert z.extent.lower == pytest.approx(0.0)
    assert z.extent.upper == pytest.approx(10.0)
    # Omitted bounds: `start` is the raw mid-hour `now` (no edge flooring), `end` the folded
    # reach end read live off the capability.
    t = _snapped_t(selection)
    assert t.interval == Interval(_CLOCK.now(), _reach_end(capability))


def test_build_selection_carries_explicit_bounds_as_raw_utc_instants() -> None:
    selection = _build(start="2026-07-12T06:15", end="2026-07-13T18:30")
    t = _snapped_t(selection)
    # Naive datetimes read as UTC; mid-hour instants ride raw — fitting is the resolver's.
    assert t.interval == Interval(
        datetime(2026, 7, 12, 6, 15, tzinfo=UTC),
        datetime(2026, 7, 13, 18, 30, tzinfo=UTC),
    )


def test_build_selection_normalizes_offset_bounds_to_utc() -> None:
    selection = _build(start="2026-07-12T14:00+02:00", end="2026-07-12T20:00Z")
    t = _snapped_t(selection)
    assert t.interval == Interval(
        datetime(2026, 7, 12, 12, 0, tzinfo=UTC),
        datetime(2026, 7, 12, 20, 0, tzinfo=UTC),
    )


def test_build_selection_accepts_single_instant_window() -> None:
    instant = datetime(2026, 7, 12, 6, 0, tzinfo=UTC)
    selection = _build(start="2026-07-12T06:00", end="2026-07-12T06:00")
    assert _snapped_t(selection).interval == Interval(instant, instant)


@pytest.mark.parametrize("raw", ["2026-07-20", "2026-W30-1"])
def test_build_selection_rejects_bare_dates_with_guidance(raw: str) -> None:
    with pytest.raises(BadRequest, match="bare dates are not accepted") as excinfo:
        _build(start=raw)
    assert f"{raw}T00:00" in str(excinfo.value)


def test_build_selection_rejects_unparsable_bounds() -> None:
    with pytest.raises(BadRequest, match="unparsable"):
        _build(end="half past nine")


def test_build_selection_rejects_backwards_window() -> None:
    with pytest.raises(BadRequest, match="start is after end"):
        _build(start="2026-07-13T00:00", end="2026-07-12T00:00")


def test_build_selection_rejects_past_end_against_implicit_now() -> None:
    with pytest.raises(BadRequest, match="is before now"):
        _build(end="2026-07-10T00:00")


def test_build_selection_beyond_reach_start_authors_single_instant_ask() -> None:
    # Beyond the 7-day fake reach: the edge still never rejects on reach's word — it authors the
    # single-instant ask and admission answers capability-mismatch (RFC 0008 decision 7).
    capability = _capability(AIR_TEMPERATURE)
    start = datetime(2026, 8, 1, 0, 0, tzinfo=UTC)
    assert _reach_end(capability) < start
    selection = _build(start="2026-08-01T00:00", capability=capability)
    assert _snapped_t(selection).interval == Interval(start, start)


def test_build_selection_rejects_explicitly_empty_parameters() -> None:
    with pytest.raises(BadRequest, match="must not be empty"):
        _build(parameter_names=[])


def test_build_selection_empty_menu_is_capability_mismatch() -> None:
    with pytest.raises(CapabilityMismatch, match="serves no parameters"):
        _build(capability=_capability())


def test_build_selection_default_menu_is_exposure_intersect_capability() -> None:
    selection = _build(capability=_capability(*core_parameters()))
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
    with pytest.raises(BadRequest, match="not requestable"):
        _build(parameter_names=["wind_u"], capability=_capability(*core_parameters()))


def test_build_selection_rejects_bad_lat_lon() -> None:
    with pytest.raises(BadRequest, match="latitude"):
        _build(latitude=100.0)
    with pytest.raises(BadRequest, match="longitude"):
        _build(longitude=200.0)


def test_build_selection_rejects_unknown_parameter() -> None:
    with pytest.raises(BadRequest, match="unknown parameter"):
        _build(parameter_names=["not_a_param"])


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
        app = build_mcp_app(Gateway(_FailingView(exc)), _CLOCK)
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
    app = build_mcp_app(Gateway(view), _CLOCK)
    tool = await app.get_tool("forecast_hourly")
    assert tool is not None
    description = tool.description or ""
    assert "air_temperature" in description
    assert "wind_u" not in description
    # Relative horizon off the fake footprint (7-day cadence in fakes) — never absolute instants,
    # since the description is built once and frozen for the process lifetime.
    assert "Horizon: out to 7 days ahead of the latest model run." in description
    assert "`end` is inclusive" in description
    assert "servable part" in description
    assert "168" not in description
    assert "reserved" not in description

    async with Client(app) as client:
        result = await client.call_tool(
            "forecast_hourly",
            {"latitude": 52.52, "longitude": 13.41},
        )
    assert result.data["air_temperature"]["unit"] == "degC"
    assert len(view.calls) == 1
    selection = view.calls[0]
    t = _snapped_t(selection)
    assert t.interval == Interval(_CLOCK.now(), _reach_end(view.capability))
    domain = selection.domain
    assert isinstance(domain, SelectionDomain)
    assert isinstance(domain.axis(AxisName.Z), VantageAxis)
    assert selection.parameters == frozenset({AIR_TEMPERATURE})


@pytest.mark.asyncio
async def test_horizon_floors_non_exact_days_to_whole_days() -> None:
    """383 h of shelf reach narrates as 15 days — never overstates what every request can get."""
    cadence = CadenceDef(
        cadence=timedelta(hours=1),
        publication_latency=timedelta(0),
        max_lead=timedelta(hours=383),
        window_quantum=timedelta(hours=24),
    )
    view = _RecordingView(_coverage(hours=2), cadence=cadence)
    app = build_mcp_app(Gateway(view), _CLOCK)
    tool = await app.get_tool("forecast_hourly")
    assert tool is not None
    assert "Horizon: out to 15 days ahead of the latest model run." in (tool.description or "")


@pytest.mark.asyncio
async def test_horizon_narrates_sub_day_reach_in_hours() -> None:
    cadence = CadenceDef(
        cadence=timedelta(hours=1),
        publication_latency=timedelta(0),
        max_lead=timedelta(hours=18),
    )
    view = _RecordingView(_coverage(hours=2), cadence=cadence)
    app = build_mcp_app(Gateway(view), _CLOCK)
    tool = await app.get_tool("forecast_hourly")
    assert tool is not None
    assert "Horizon: out to 18 hours ahead of the latest model run." in (tool.description or "")


@pytest.mark.asyncio
async def test_narration_with_empty_menu_skips_horizon() -> None:
    # The no-provider profile: startup must not raise (a `min` over zero reaches would), and the
    # description simply has no horizon to narrate.
    view = _RecordingView(_coverage(), parameters=set())
    app = build_mcp_app(Gateway(view), _CLOCK)
    tool = await app.get_tool("forecast_hourly")
    assert tool is not None
    description = tool.description or ""
    assert "(none)" in description
    assert "Horizon" not in description


@pytest.mark.asyncio
async def test_bad_request_via_tool() -> None:
    app = build_mcp_app(Gateway(_RecordingView(_coverage())), _CLOCK)
    async with Client(app) as client:
        with pytest.raises(ToolError, match=r"^bad-request:"):
            await client.call_tool(
                "forecast_hourly",
                {"latitude": 999.0, "longitude": 0.0},
            )
