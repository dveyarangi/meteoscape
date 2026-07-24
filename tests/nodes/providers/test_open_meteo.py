"""Open-Meteo leaf — request mapping, normalizer, provenance, and HttpxTransport."""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx

from fakes import STOPPED, core_parameters
from meteoscape.api.mcp_app import serialize_coverage
from meteoscape.errors import RuntimeFailure
from meteoscape.identity import SourceKey
from meteoscape.manifold.cadence import RollingAxis
from meteoscape.manifold.core import Coverage, Selection
from meteoscape.manifold.domain import (
    Axis,
    AxisName,
    ContinuousAxis,
    FootprintDomain,
    GridDomain,
    IntervalAxis,
    RegularAxis,
)
from meteoscape.manifold.provenance import AtomicOrigin, Provenance, Uniform
from meteoscape.nodes.providers.base import FetchRequest, HttpxTransport, Transport
from meteoscape.nodes.providers.open_meteo import (
    BASE_URL,
    CADENCE,
    TAPS,
    OpenMeteoNormalizer,
    OpenMeteoProvider,
)
from meteoscape.nodes.providers.timeline import TOA_M
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


def _canned_hourly(*, hours: int = 4, **overrides) -> dict:
    start = datetime(2026, 7, 11, 12, 0, tzinfo=UTC)
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
    provider = OpenMeteoProvider(
        transport=transport,
        clock=STOPPED,
        parameters=core_parameters(),
    )
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


@pytest.mark.asyncio
async def test_project_assembles_onto_selection_domain() -> None:
    transport = _CapturingTransport(_canned_hourly(hours=4))
    provider = OpenMeteoProvider(
        transport=transport,
        clock=STOPPED,
        parameters=core_parameters(),
    )
    selection = _selection(hours=4)
    coverage = await provider.project(selection)
    assert isinstance(coverage, Coverage)
    assert coverage.domain == selection.domain
    assert list(coverage.ranges[AIR_TEMPERATURE].values) == [18.0, 19.0, 20.0, 21.0]
    temp = coverage.ranges[AIR_TEMPERATURE]
    assert all(temp.is_present(i) for i in range(4))
    # Pins the all-present elision optimization, not a presence contract.
    assert temp.present is None


def test_normalize_returns_native_records_by_z() -> None:
    normalizer = OpenMeteoNormalizer(core_parameters())
    records = normalizer.normalize(
        _canned_hourly(hours=2),
        _sample_provenance(),
        parameters=frozenset(
            {AIR_TEMPERATURE, RELATIVE_HUMIDITY, WIND_U, WIND_V, PRECIPITATION, CLOUD_COVER}
        ),
    )
    assert len(records) == 4  # 2m, 10m, surface, column
    by_params = {frozenset(r.ranges): r for r in records}

    # `Coverage.domain` is an `EnumerableDomain` — an enumerable curvilinear coverage stays open
    # (#12, source role), so the grid path is asserted here rather than assumed.
    def _grid_of(coverage: Coverage) -> GridDomain:
        domain = coverage.domain
        assert isinstance(domain, GridDomain)
        return domain

    near = by_params[frozenset({AIR_TEMPERATURE, RELATIVE_HUMIDITY})]
    assert _grid_of(near).axis(AxisName.Z).extent.lower == pytest.approx(2.0)
    assert list(near.ranges[AIR_TEMPERATURE].values) == [18.0, 19.0]

    wind = by_params[frozenset({WIND_U, WIND_V})]
    assert _grid_of(wind).axis(AxisName.Z).extent.lower == pytest.approx(10.0)
    # 36 km/h from east → 10 m/s, u=-10, v≈0
    assert list(wind.ranges[WIND_U].values) == pytest.approx([-10.0, -10.0])
    assert list(wind.ranges[WIND_V].values) == pytest.approx([0.0, 0.0], abs=1e-9)

    precip = by_params[frozenset({PRECIPITATION})]
    assert _grid_of(precip).axis(AxisName.Z).extent.lower == pytest.approx(0.0)

    cloud = by_params[frozenset({CLOUD_COVER})]
    z = _grid_of(cloud).axis(AxisName.Z)
    assert isinstance(z, IntervalAxis)
    assert z.extent.upper == pytest.approx(TOA_M)


def test_capability_declares_six_native_z_facts() -> None:
    provider = OpenMeteoProvider(
        transport=_CapturingTransport({}),
        clock=STOPPED,
        parameters=core_parameters(),
    )
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
    footprints = provider.capability.footprints

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
    provider = OpenMeteoProvider(
        transport=_CapturingTransport({}),
        clock=STOPPED,
        parameters=core_parameters(),
    )
    capability = provider.capability
    declared = {pid: domain for pid, (_, domain) in capability.footprints.items()}
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


def test_unit_mismatch_raises_runtime_failure() -> None:
    normalizer = OpenMeteoNormalizer(core_parameters())
    bad = _canned_hourly(hourly_units={"temperature_2m": "°F"})
    with pytest.raises(RuntimeFailure, match="unit"):
        normalizer.normalize(bad, _sample_provenance(), parameters=frozenset({AIR_TEMPERATURE}))


def test_malformed_payload_raises_runtime_failure() -> None:
    normalizer = OpenMeteoNormalizer(core_parameters())
    with pytest.raises(RuntimeFailure):
        normalizer.normalize({"latitude": 1.0}, _sample_provenance())
    ragged = _canned_hourly(hours=4)
    ragged["hourly"]["temperature_2m"] = [1.0, 2.0]
    with pytest.raises(RuntimeFailure, match="malformed"):
        normalizer.normalize(ragged, _sample_provenance(), parameters=frozenset({AIR_TEMPERATURE}))


@pytest.mark.asyncio
async def test_provenance_authored_from_cadence_and_clock() -> None:
    transport = _CapturingTransport(_canned_hourly(hours=2))
    provider = OpenMeteoProvider(
        transport=transport,
        clock=STOPPED,
        parameters=core_parameters(),
    )
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
    provider = OpenMeteoProvider(
        transport=transport,
        clock=STOPPED,
        parameters=core_parameters(),
    )
    await provider.project(_selection(hours=1, parameters={WIND_U, WIND_V}))
    hourly = transport.requests[0].params["hourly"]
    assert hourly == "wind_speed_10m,wind_direction_10m"


def test_wind_direction_from_north() -> None:
    """From north at 3.6 km/h → 1 m/s, u≈0, v=-1."""
    normalizer = OpenMeteoNormalizer(core_parameters())
    raw = _canned_hourly(
        hours=1,
        hourly={"wind_speed_10m": [3.6], "wind_direction_10m": [0.0]},
    )
    records = normalizer.normalize(
        raw, _sample_provenance(), parameters=frozenset({WIND_U, WIND_V})
    )
    wind = records[0]
    assert wind.ranges[WIND_U].values[0] == pytest.approx(0.0, abs=1e-9)
    assert wind.ranges[WIND_V].values[0] == pytest.approx(-1.0, abs=1e-9)
    assert math.isclose(
        wind.ranges[WIND_U].values[0] ** 2 + wind.ranges[WIND_V].values[0] ** 2, 1.0
    )


def _reject_nonfinite(token: str) -> float:
    raise ValueError(f"non-finite JSON constant: {token}")


@pytest.mark.asyncio
async def test_vendor_null_serializes_as_json_null() -> None:
    """A vendor null reaches the MCP wire as JSON null, never NaN."""
    transport = _CapturingTransport(
        _canned_hourly(hours=3, hourly={"temperature_2m": [18.5, None, 19.1]})
    )
    provider = OpenMeteoProvider(
        transport=transport,
        clock=STOPPED,
        parameters=core_parameters(),
    )
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


def test_null_wind_speed_marks_both_components_absent() -> None:
    normalizer = OpenMeteoNormalizer(core_parameters())
    raw = _canned_hourly(
        hours=2,
        hourly={
            "wind_speed_10m": [36.0, None],
            "wind_direction_10m": [90.0, 90.0],
        },
    )
    records = normalizer.normalize(
        raw, _sample_provenance(), parameters=frozenset({WIND_U, WIND_V})
    )
    wind = records[0]
    assert wind.ranges[WIND_U].is_present(0) is True
    assert wind.ranges[WIND_U].is_present(1) is False
    assert wind.ranges[WIND_V].is_present(0) is True
    assert wind.ranges[WIND_V].is_present(1) is False


def _sample_provenance() -> Provenance:
    now = STOPPED.now()
    return Provenance(
        origin=AtomicOrigin(SourceKey("open-meteo", "best_match"), CADENCE.anchor(now)),
        fetched_at=now,
        expiration=CADENCE.expiration(now),
    )


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
