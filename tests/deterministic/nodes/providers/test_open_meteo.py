"""Open-Meteo leaf — its Probe's query and envelope parse, and the shape it is composed into."""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx

from fakes import STOPPED, core_parameters, snapped_point_domain
from meteoscape.api.mcp_app import serialize_coverage
from meteoscape.errors import CapabilityMismatch, RuntimeFailure
from meteoscape.identity import SourceKey
from meteoscape.manifold.cadence import RollingAxis
from meteoscape.manifold.core import Coverage, Selection
from meteoscape.manifold.domain import (
    Axis,
    AxisName,
    ContinuousAxis,
    FootprintDomain,
    GridDomain,
    Interval,
    IntervalAxis,
    RegularAxis,
    SelectionDomain,
    SnappedAxis,
    VantageAxis,
)
from meteoscape.manifold.provenance import AtomicOrigin, Uniform
from meteoscape.nodes.providers.base import FetchRequest, HttpxTransport, Transport
from meteoscape.nodes.providers.open_meteo import (
    BASE_URL,
    BEST_MATCH,
    CADENCE,
    PROVIDER_ID,
    TAPS,
    OpenMeteoProbe,
)
from meteoscape.nodes.providers.timeline import (
    HOURLY_STEP,
    TOA_M,
    Z_2M,
    Z_10M,
    Z_COLUMN,
    Z_SURFACE,
    TimelineDelivery,
    TimelineProvider,
)
from meteoscape.parameters import (
    AIR_TEMPERATURE,
    CLOUD_COVER,
    PRECIPITATION,
    RELATIVE_HUMIDITY,
    WIND_U,
    WIND_V,
    ParameterId,
)


class _CapturingTransport:
    def __init__(self, response: object) -> None:
        self.requests: list[FetchRequest] = []
        self._response = response

    async def fetch(self, request: FetchRequest) -> object:
        self.requests.append(request)
        return self._response


def _provider(transport: Transport) -> TimelineProvider:
    """The shipped composition — the timeline shape carrying this vendor's Probe and declarations."""
    return TimelineProvider(
        probe=OpenMeteoProbe(transport),
        taps=TAPS,
        step=HOURLY_STEP,
        cadence=CADENCE,
        clock=STOPPED,
        parameters=core_parameters(),
        source_key=SourceKey(PROVIDER_ID, BEST_MATCH),
    )


async def _delivered(raw: object, *variables: str) -> TimelineDelivery:
    """One canned response through the real Probe — the Transport is mocked, the Probe never is."""
    return await OpenMeteoProbe(_CapturingTransport(raw)).retrieve(
        longitude=13.41,
        latitude=52.52,
        over=Interval(
            datetime(2026, 7, 11, 12, tzinfo=UTC),
            datetime(2026, 7, 11, 15, tzinfo=UTC),
        ),
        variables=variables,
    )


def _selection(*, hours: int = 4, parameters=None) -> Selection:
    start = datetime(2026, 7, 11, 12, 0, tzinfo=UTC)
    return Selection(
        domain=GridDomain(
            axes={
                AxisName.X: RegularAxis(AxisName.X, 13.41, 1.0, 1, False),
                AxisName.Y: RegularAxis(AxisName.Y, 52.52, 1.0, 1, False),
                AxisName.Z: RegularAxis(AxisName.Z, 2.0, 1.0, 1, False),
                AxisName.T: RegularAxis(AxisName.T, start, timedelta(hours=1), hours, True),
            }
        ),
        parameters=frozenset(parameters)
        if parameters is not None
        else frozenset({AIR_TEMPERATURE}),
    )


def _canned_hourly(*, hours: int = 4, start: datetime | None = None, **overrides) -> dict:
    start = start or datetime(2026, 7, 11, 12, 0, tzinfo=UTC)
    times = [(start + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(hours)]
    hourly_units = {
        "time": "iso8601",
        "temperature_2m": "°C",
        "relative_humidity_2m": "%",
        "wind_speed_10m": "km/h",
        "wind_direction_10m": "°",
        "precipitation": "mm",
        "cloud_cover": "%",
    }
    hourly = {
        "time": times,
        "temperature_2m": [18.0 + i for i in range(hours)],
        "relative_humidity_2m": [50.0 + i for i in range(hours)],
        "wind_speed_10m": [36.0] * hours,  # 36 km/h → 10 m/s
        "wind_direction_10m": [90.0] * hours,  # from east → u=-10, v=0
        "precipitation": [0.1 * i for i in range(hours)],
        "cloud_cover": [40.0 + i for i in range(hours)],
    }
    hourly_units.update(overrides.pop("hourly_units", {}))
    hourly.update(overrides.pop("hourly", {}))
    return {
        "latitude": 52.52,
        "longitude": 13.419998,
        "hourly_units": hourly_units,
        "hourly": hourly,
        **overrides,
    }


@pytest.mark.asyncio
async def test_selection_maps_to_forecast_request() -> None:
    transport: Transport = _CapturingTransport(_canned_hourly(hours=4))
    provider = _provider(transport)
    await provider.project(_selection(hours=4))

    assert len(transport.requests) == 1
    request = transport.requests[0]
    assert request.path == "/v1/forecast"
    assert request.params["latitude"] == "52.52"
    assert request.params["longitude"] == "13.41"
    assert request.params["hourly"] == "temperature_2m"
    assert request.params["start_hour"] == "2026-07-11T12:00"
    assert request.params["end_hour"] == "2026-07-11T15:00"
    assert request.params["timezone"] == "UTC"


def _snapped_selection(*, start: datetime, end: datetime) -> Selection:
    return Selection(
        domain=snapped_point_domain(start=start, end=end, lon=13.41, lat=52.52),
        parameters=frozenset({AIR_TEMPERATURE}),
    )


@pytest.mark.asyncio
async def test_snapped_bounds_inside_window_map_to_floored_hours() -> None:
    """STOPPED + day-quantum CADENCE → window [00:00, +383h]; interior bounds pass through floored."""
    start = datetime(2026, 7, 12, 0, tzinfo=UTC)
    transport = _CapturingTransport(_canned_hourly(hours=4, start=start))
    provider = _provider(transport)
    selection = _snapped_selection(start=start, end=datetime(2026, 7, 12, 3, tzinfo=UTC))
    coverage = await provider.project(selection)
    assert isinstance(coverage, Coverage)
    assert len(transport.requests) == 1
    assert transport.requests[0].params["start_hour"] == "2026-07-12T00:00"
    assert transport.requests[0].params["end_hour"] == "2026-07-12T03:00"
    assert isinstance(coverage.domain, GridDomain)
    assert list(coverage.ranges[AIR_TEMPERATURE].values) == [18.0, 19.0, 20.0, 21.0]


@pytest.mark.asyncio
async def test_snapped_bounds_straddling_window_clamp_to_window() -> None:
    transport = _CapturingTransport(
        _canned_hourly(hours=4, start=datetime(2026, 7, 11, 12, tzinfo=UTC))
    )
    provider = _provider(transport)
    window = CADENCE.valid_time(STOPPED.now())
    selection = _snapped_selection(
        start=datetime(2026, 7, 1, tzinfo=UTC),
        end=datetime(2026, 8, 1, tzinfo=UTC),
    )
    coverage = await provider.project(selection)
    assert isinstance(coverage, Coverage)
    assert len(transport.requests) == 1
    assert transport.requests[0].params["start_hour"] == window.lower.strftime("%Y-%m-%dT%H:%M")
    assert transport.requests[0].params["end_hour"] == window.upper.strftime("%Y-%m-%dT%H:%M")
    # Honest shorter answer: four vendor hours inside the wide bounds.
    assert len(coverage.domain) == 4


@pytest.mark.asyncio
async def test_snapped_mid_hour_bounds_floor_both_edges() -> None:
    """Flooring the upper bound is end-inclusivity (last tick ≤ end)."""
    start = datetime(2026, 7, 11, 12, tzinfo=UTC)
    transport = _CapturingTransport(_canned_hourly(hours=3, start=start))
    provider = _provider(transport)
    selection = _snapped_selection(
        start=datetime(2026, 7, 11, 12, 30, tzinfo=UTC),
        end=datetime(2026, 7, 11, 14, 45, tzinfo=UTC),
    )
    coverage = await provider.project(selection)
    assert isinstance(coverage, Coverage)
    assert isinstance(coverage.domain, GridDomain)
    assert len(transport.requests) == 1
    assert transport.requests[0].params["start_hour"] == "2026-07-11T12:00"
    assert transport.requests[0].params["end_hour"] == "2026-07-11T14:00"
    assert len(coverage.domain.axis(AxisName.T)) == 3


@pytest.mark.asyncio
async def test_snapped_raced_empty_raises_without_vendor_call() -> None:
    transport = _CapturingTransport(_canned_hourly(hours=1))
    provider = _provider(transport)
    # Day-quantum CADENCE makes window.lower = today00 at STOPPED; end before that is empty.
    selection = _snapped_selection(
        start=datetime(2026, 7, 1, tzinfo=UTC),
        end=datetime(2026, 7, 10, 23, tzinfo=UTC),
    )
    with pytest.raises(CapabilityMismatch, match="no t within the requested bounds"):
        await provider.project(selection)
    assert transport.requests == []


@pytest.mark.asyncio
async def test_enumerable_t_in_a_selection_domain_is_served() -> None:
    """Nothing snapped is an exact request in request form: `ground` passes every member through."""
    instant = datetime(2026, 7, 12, tzinfo=UTC)
    transport = _CapturingTransport(_canned_hourly(hours=2, start=instant))
    provider = _provider(transport)
    selection = Selection(
        domain=SelectionDomain(
            axes={
                AxisName.X: RegularAxis(AxisName.X, 13.41, 1.0, 1, False),
                AxisName.Y: RegularAxis(AxisName.Y, 52.52, 1.0, 1, False),
                AxisName.Z: VantageAxis(AxisName.Z, Interval(0.0, 10.0)),
                AxisName.T: RegularAxis(AxisName.T, instant, timedelta(hours=1), 2, False),
            }
        ),
        parameters=frozenset({AIR_TEMPERATURE}),
    )
    coverage = await provider.project(selection)
    assert isinstance(coverage, Coverage)
    assert transport.requests[0].params["start_hour"] == "2026-07-12T00:00"
    assert transport.requests[0].params["end_hour"] == "2026-07-12T01:00"
    assert list(coverage.ranges[AIR_TEMPERATURE].values) == [18.0, 19.0]


@pytest.mark.asyncio
async def test_snapped_non_t_axis_raises_without_vendor_call() -> None:
    """A snapped X declines at `ground`: temporal bounds never meet the leaf's spatial axis."""
    transport = _CapturingTransport(_canned_hourly(hours=1))
    provider = _provider(transport)
    instant = datetime(2026, 7, 12, tzinfo=UTC)
    snapped_x = Selection(
        domain=SelectionDomain(
            axes={
                AxisName.X: SnappedAxis(
                    AxisName.X, Interval(instant, instant + timedelta(hours=1))
                ),
                AxisName.Y: RegularAxis(AxisName.Y, 52.52, 1.0, 1, False),
                AxisName.Z: VantageAxis(AxisName.Z, Interval(0.0, 10.0)),
                AxisName.T: SnappedAxis(
                    AxisName.T, Interval(instant, instant + timedelta(hours=3))
                ),
            }
        ),
        parameters=frozenset({AIR_TEMPERATURE}),
    )
    with pytest.raises(CapabilityMismatch, match="no x within the requested bounds"):
        await provider.project(snapped_x)
    assert transport.requests == []


@pytest.mark.asyncio
async def test_snapped_assembles_request_xyz_and_vendor_t() -> None:
    start = datetime(2026, 7, 12, 0, tzinfo=UTC)
    end = datetime(2026, 7, 12, 3, tzinfo=UTC)
    transport = _CapturingTransport(_canned_hourly(hours=4, start=start))
    provider = _provider(transport)
    selection = _snapped_selection(start=start, end=end)
    coverage = await provider.project(selection)
    assert isinstance(coverage, Coverage)
    assert isinstance(coverage.domain, GridDomain)
    assert isinstance(selection.domain, SelectionDomain)
    assert coverage.domain.axis(AxisName.X) is selection.domain.axis(AxisName.X)
    assert coverage.domain.axis(AxisName.Y) is selection.domain.axis(AxisName.Y)
    assert coverage.domain.axis(AxisName.Z) is selection.domain.axis(AxisName.Z)
    t = coverage.domain.axis(AxisName.T)
    assert isinstance(t, RegularAxis)
    assert t.anchor == start
    assert t.count == 4
    assert list(coverage.ranges[AIR_TEMPERATURE].values) == [18.0, 19.0, 20.0, 21.0]


@pytest.mark.asyncio
async def test_snapped_shorter_vendor_response_is_honest() -> None:
    start = datetime(2026, 7, 12, 0, tzinfo=UTC)
    transport = _CapturingTransport(_canned_hourly(hours=2, start=start))
    provider = _provider(transport)
    selection = _snapped_selection(start=start, end=datetime(2026, 7, 12, 10, tzinfo=UTC))
    coverage = await provider.project(selection)
    assert isinstance(coverage, Coverage)
    assert isinstance(coverage.domain, GridDomain)
    assert len(coverage.domain.axis(AxisName.T)) == 2
    assert list(coverage.ranges[AIR_TEMPERATURE].values) == [18.0, 19.0]


@pytest.mark.asyncio
async def test_snapped_disjoint_vendor_window_is_mismatch() -> None:
    transport = _CapturingTransport(
        _canned_hourly(hours=4, start=datetime(2026, 7, 11, 12, tzinfo=UTC))
    )
    provider = _provider(transport)
    selection = _snapped_selection(
        start=datetime(2026, 7, 12, 0, tzinfo=UTC),
        end=datetime(2026, 7, 12, 3, tzinfo=UTC),
    )
    with pytest.raises(CapabilityMismatch, match="no t within the requested bounds"):
        await provider.project(selection)


@pytest.mark.asyncio
async def test_snapped_wider_vendor_response_is_trimmed() -> None:
    """A vendor loose with start_hour/end_hour is clipped, not rejected — snapping clamps."""
    start = datetime(2026, 7, 12, 0, tzinfo=UTC)
    transport = _CapturingTransport(_canned_hourly(hours=6, start=start))
    provider = _provider(transport)
    selection = _snapped_selection(start=start, end=datetime(2026, 7, 12, 3, tzinfo=UTC))
    coverage = await provider.project(selection)
    assert isinstance(coverage, Coverage)
    assert isinstance(coverage.domain, GridDomain)
    t = coverage.domain.axis(AxisName.T)
    assert isinstance(t, RegularAxis)
    assert (t.anchor, t.count) == (start, 4)
    assert list(coverage.ranges[AIR_TEMPERATURE].values) == [18.0, 19.0, 20.0, 21.0]


@pytest.mark.asyncio
async def test_snapped_vendor_series_starting_early_is_trimmed_at_the_front() -> None:
    """The lower bound cuts the head off too — the kept head is the cell containing it."""
    transport = _CapturingTransport(
        _canned_hourly(hours=6, start=datetime(2026, 7, 12, 0, tzinfo=UTC))
    )
    provider = _provider(transport)
    selection = _snapped_selection(
        start=datetime(2026, 7, 12, 2, tzinfo=UTC),
        end=datetime(2026, 7, 12, 3, tzinfo=UTC),
    )
    coverage = await provider.project(selection)
    assert isinstance(coverage, Coverage)
    assert isinstance(coverage.domain, GridDomain)
    t = coverage.domain.axis(AxisName.T)
    assert isinstance(t, RegularAxis)
    assert (t.anchor, t.count) == (datetime(2026, 7, 12, 2, tzinfo=UTC), 2)
    assert list(coverage.ranges[AIR_TEMPERATURE].values) == [20.0, 21.0]


@pytest.mark.asyncio
async def test_series_off_the_declared_step_is_a_vendor_fault() -> None:
    """The tick lattice is derived and held against the declared step, never taken on the vendor's word."""
    start = datetime(2026, 7, 12, 0, tzinfo=UTC)
    raw = _canned_hourly(hours=3, start=start)
    raw["hourly"]["time"] = [
        "2026-07-12T00:00",
        "2026-07-12T00:30",  # half an hour into an hourly declaration
        "2026-07-12T01:00",
    ]
    transport = _CapturingTransport(raw)
    provider = _provider(transport)
    selection = _snapped_selection(start=start, end=datetime(2026, 7, 12, 2, tzinfo=UTC))
    with pytest.raises(RuntimeFailure, match="off its declared step"):
        await provider.project(selection)


@pytest.mark.asyncio
async def test_project_assembles_onto_selection_domain() -> None:
    transport = _CapturingTransport(_canned_hourly(hours=4))
    provider = _provider(transport)
    selection = _selection(hours=4)
    coverage = await provider.project(selection)
    assert isinstance(coverage, Coverage)
    assert coverage.domain == selection.domain
    assert list(coverage.ranges[AIR_TEMPERATURE].values) == [18.0, 19.0, 20.0, 21.0]
    temp = coverage.ranges[AIR_TEMPERATURE]
    assert all(temp.is_present(i) for i in range(4))
    # Pins the all-present elision optimization, not a presence contract.
    assert temp.present is None


@pytest.mark.asyncio
async def test_short_vendor_series_against_an_exact_request_is_a_vendor_fault() -> None:
    """An exact request pins its own length, so a short series is the vendor falling short."""
    transport = _CapturingTransport(_canned_hourly(hours=2))
    provider = _provider(transport)
    with pytest.raises(RuntimeFailure, match="delivered less than it declared"):
        await provider.project(_selection(hours=4))


def test_taps_group_into_four_native_levels() -> None:
    """One native record per Z cell (ADR-0006) — the grouping the six parameters fall into."""
    groups = TAPS.by_level()
    assert {spec: {tap.produces for tap in group} for spec, group in groups.items()} == {
        Z_2M: {AIR_TEMPERATURE, RELATIVE_HUMIDITY},
        Z_10M: {WIND_U, WIND_V},
        Z_SURFACE: {PRECIPITATION},
        Z_COLUMN: {CLOUD_COVER},
    }


@pytest.mark.asyncio
async def test_interpret_converts_and_decodes_every_served_parameter() -> None:
    delivery = await _delivered(_canned_hourly(hours=2), *TAPS.variables)
    values = TAPS.interpret(delivery, source=PROVIDER_ID)

    assert list(values[AIR_TEMPERATURE].values) == [18.0, 19.0]
    assert list(values[RELATIVE_HUMIDITY].values) == [50.0, 51.0]
    # 36 km/h from east → 10 m/s, u=-10, v≈0
    assert list(values[WIND_U].values) == pytest.approx([-10.0, -10.0])
    assert list(values[WIND_V].values) == pytest.approx([0.0, 0.0], abs=1e-9)
    assert list(values[PRECIPITATION].values) == pytest.approx([0.0, 0.1])
    assert list(values[CLOUD_COVER].values) == [40.0, 41.0]


def test_capability_declares_six_native_z_facts() -> None:
    provider = _provider(_CapturingTransport({}))
    caps = provider.capability.parameters
    assert set(caps) == {
        AIR_TEMPERATURE,
        RELATIVE_HUMIDITY,
        WIND_U,
        WIND_V,
        PRECIPITATION,
        CLOUD_COVER,
    }
    assert len(TAPS) == 6

    # The Capability advertises geometry as bare `Domain` — the leaf's own type is narrower.
    footprints = provider.capability.reaches

    def _native_z(pid: ParameterId) -> Axis:
        domain = footprints[pid][1]
        assert isinstance(domain, FootprintDomain)
        return domain.axis(AxisName.Z)

    assert _native_z(AIR_TEMPERATURE).extent.lower == pytest.approx(2.0)
    assert _native_z(WIND_U).extent.lower == pytest.approx(10.0)
    assert _native_z(PRECIPITATION).extent.lower == pytest.approx(0.0)
    cloud_z = _native_z(CLOUD_COVER)
    assert isinstance(cloud_z, IntervalAxis)
    assert cloud_z.extent.upper == pytest.approx(TOA_M)


def test_capability_reach_exposes_leaf_domains() -> None:
    """`capability.reach(pid)` is the leaf's own declared Domain — same object, live rolling T."""
    provider = _provider(_CapturingTransport({}))
    capability = provider.capability
    declared = {pid: domain for pid, (_, domain) in capability.reaches.items()}
    for pid in capability.parameters:
        reach = capability.reach(pid)
        assert reach is declared[pid]
        assert isinstance(reach, FootprintDomain)
        assert reach.axis(AxisName.X).extent.lower == pytest.approx(-180.0)
        assert reach.axis(AxisName.X).extent.upper == pytest.approx(180.0)
        assert reach.axis(AxisName.Y).extent.lower == pytest.approx(-90.0)
        assert reach.axis(AxisName.Y).extent.upper == pytest.approx(90.0)
        assert isinstance(reach.axis(AxisName.X), ContinuousAxis)
        assert isinstance(reach.axis(AxisName.T), RollingAxis)


@pytest.mark.asyncio
async def test_unit_mismatch_raises_runtime_failure() -> None:
    """A vendor that reports units has its claim checked against the taps, not trusted."""
    bad = await _delivered(_canned_hourly(hourly_units={"temperature_2m": "°F"}), "temperature_2m")
    with pytest.raises(RuntimeFailure, match="unit"):
        TAPS.engaged_by({AIR_TEMPERATURE}).interpret(bad, source=PROVIDER_ID)


@pytest.mark.asyncio
async def test_malformed_payload_raises_runtime_failure() -> None:
    """The envelope parse is the Probe's, and it declines a body it cannot read as a series."""
    with pytest.raises(RuntimeFailure, match="missing required forecast fields"):
        await _delivered({"latitude": 1.0}, "temperature_2m")
    ragged = _canned_hourly(hours=4)
    ragged["hourly"]["temperature_2m"] = [1.0, 2.0]
    with pytest.raises(RuntimeFailure, match="malformed"):
        await _delivered(ragged, "temperature_2m")


@pytest.mark.asyncio
async def test_provenance_authored_from_cadence_and_clock() -> None:
    transport = _CapturingTransport(_canned_hourly(hours=2))
    provider = _provider(transport)
    # `project` is closed — it returns a `Manifold` (ADR-0001); a sampled result is a `Coverage`.
    coverage = await provider.project(_selection(hours=2))
    assert isinstance(coverage, Coverage)
    assert isinstance(coverage.provenance, Uniform)
    prov = coverage.provenance.summary(AIR_TEMPERATURE)
    now = STOPPED.now()
    assert isinstance(prov.origin, AtomicOrigin)
    assert prov.origin.source == SourceKey("open-meteo", "best_match")
    assert prov.origin.issue_time == CADENCE.anchor(now)
    assert prov.fetched_at == now
    assert prov.expiration == CADENCE.expiration(now)


@pytest.mark.asyncio
async def test_wind_fetch_requests_shared_vendor_vars_once() -> None:
    transport = _CapturingTransport(_canned_hourly(hours=1))
    provider = _provider(transport)
    await provider.project(_selection(hours=1, parameters={WIND_U, WIND_V}))
    hourly = transport.requests[0].params["hourly"]
    assert hourly == "wind_speed_10m,wind_direction_10m"


@pytest.mark.asyncio
async def test_wind_direction_from_north() -> None:
    """From north at 3.6 km/h → 1 m/s, u≈0, v=-1."""
    delivery = await _delivered(
        _canned_hourly(hours=1, hourly={"wind_speed_10m": [3.6], "wind_direction_10m": [0.0]}),
        "wind_speed_10m",
        "wind_direction_10m",
    )
    wind = TAPS.engaged_by({WIND_U, WIND_V}).interpret(delivery, source=PROVIDER_ID)
    assert wind[WIND_U].values[0] == pytest.approx(0.0, abs=1e-9)
    assert wind[WIND_V].values[0] == pytest.approx(-1.0, abs=1e-9)
    assert math.isclose(wind[WIND_U].values[0] ** 2 + wind[WIND_V].values[0] ** 2, 1.0)


def _reject_nonfinite(token: str) -> float:
    raise ValueError(f"non-finite JSON constant: {token}")


@pytest.mark.asyncio
async def test_vendor_null_serializes_as_json_null() -> None:
    """A vendor null reaches the MCP wire as JSON null, never NaN."""
    transport = _CapturingTransport(
        _canned_hourly(hours=3, hourly={"temperature_2m": [18.5, None, 19.1]})
    )
    provider = _provider(transport)
    coverage = await provider.project(_selection(hours=3))
    assert isinstance(coverage, Coverage)
    temp = coverage.ranges[AIR_TEMPERATURE]
    assert temp.is_present(0) is True
    assert temp.is_present(1) is False
    assert temp.is_present(2) is True

    payload = serialize_coverage(coverage)
    wire = json.dumps(payload)
    parsed = json.loads(wire, parse_constant=_reject_nonfinite)
    assert parsed["air_temperature"]["values"] == [18.5, None, 19.1]


@pytest.mark.asyncio
async def test_null_wind_speed_marks_both_components_absent() -> None:
    delivery = await _delivered(
        _canned_hourly(
            hours=2,
            hourly={"wind_speed_10m": [36.0, None], "wind_direction_10m": [90.0, 90.0]},
        ),
        "wind_speed_10m",
        "wind_direction_10m",
    )
    wind = TAPS.engaged_by({WIND_U, WIND_V}).interpret(delivery, source=PROVIDER_ID)
    assert wind[WIND_U].is_present(0) is True
    assert wind[WIND_U].is_present(1) is False
    assert wind[WIND_V].is_present(0) is True
    assert wind[WIND_V].is_present(1) is False


@pytest.mark.asyncio
@respx.mock
async def test_httpx_transport_decodes_json() -> None:
    respx.get(f"{BASE_URL}/v1/forecast").mock(return_value=httpx.Response(200, json={"ok": True}))
    transport = HttpxTransport(BASE_URL)
    result = await transport.fetch(FetchRequest(path="/v1/forecast", params={"latitude": "1"}))
    assert result == {"ok": True}


@pytest.mark.asyncio
@respx.mock
async def test_httpx_transport_5xx_is_runtime_failure() -> None:
    respx.get(f"{BASE_URL}/v1/forecast").mock(return_value=httpx.Response(503))
    transport = HttpxTransport(BASE_URL)
    with pytest.raises(RuntimeFailure, match="HTTP 503"):
        await transport.fetch(FetchRequest(path="/v1/forecast", params={}))


@pytest.mark.asyncio
@respx.mock
async def test_httpx_transport_timeout_is_runtime_failure() -> None:
    respx.get(f"{BASE_URL}/v1/forecast").mock(side_effect=httpx.TimeoutException("boom"))
    transport = HttpxTransport(BASE_URL)
    with pytest.raises(RuntimeFailure, match="timeout"):
        await transport.fetch(FetchRequest(path="/v1/forecast", params={}))


@pytest.mark.asyncio
@respx.mock
async def test_httpx_transport_non_json_is_runtime_failure() -> None:
    respx.get(f"{BASE_URL}/v1/forecast").mock(
        return_value=httpx.Response(200, text="not-json", headers={"content-type": "text/plain"})
    )
    transport = HttpxTransport(BASE_URL)
    with pytest.raises(RuntimeFailure, match="non-JSON"):
        await transport.fetch(FetchRequest(path="/v1/forecast", params={}))
