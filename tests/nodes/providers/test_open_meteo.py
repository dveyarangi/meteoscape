"""Open-Meteo leaf — request mapping, normalizer, provenance, and HttpxTransport."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx

from fakes import STOPPED, core_parameters
from meteoscape.errors import RuntimeFailure
from meteoscape.identity import SourceKey
from meteoscape.manifold.core import Selection
from meteoscape.manifold.coverage import CoverageRecord
from meteoscape.manifold.domain import AxisName, RegularAxis, RegularDomain
from meteoscape.manifold.provenance import AtomicOrigin, Provenance, Uniform
from meteoscape.nodes.providers.base import FetchRequest, HttpxTransport, Transport
from meteoscape.nodes.providers.open_meteo import (
    BASE_URL,
    CADENCE,
    OpenMeteoNormalizer,
    OpenMeteoProvider,
)
from meteoscape.parameters import AIR_TEMPERATURE


class _CapturingTransport:
    def __init__(self, response: object) -> None:
        self.requests: list[FetchRequest] = []
        self._response = response

    async def fetch(self, request: FetchRequest) -> object:
        self.requests.append(request)
        return self._response


def _selection(*, hours: int = 4) -> Selection:
    start = datetime(2026, 7, 11, 12, 0, tzinfo=UTC)
    return Selection(
        domain=RegularDomain(
            axes={
                AxisName.X: RegularAxis(AxisName.X, 13.41, 1.0, 1, False),
                AxisName.Y: RegularAxis(AxisName.Y, 52.52, 1.0, 1, False),
                AxisName.Z: RegularAxis(AxisName.Z, 2.0, 1.0, 1, False),
                AxisName.T: RegularAxis(AxisName.T, start, timedelta(hours=1), hours, True),
            }
        ),
        parameters=frozenset({AIR_TEMPERATURE}),
    )


def _canned_hourly(*, hours: int = 4, unit: str = "°C", values=None) -> dict:
    start = datetime(2026, 7, 11, 12, 0, tzinfo=UTC)
    times = [(start + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(hours)]
    return {
        "latitude": 52.52,
        "longitude": 13.419998,
        "hourly_units": {"time": "iso8601", "temperature_2m": unit},
        "hourly": {
            "time": times,
            "temperature_2m": values if values is not None else [float(i) for i in range(hours)],
        },
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
    assert request.params == {
        "latitude": "52.52",
        "longitude": "13.41",
        "hourly": "temperature_2m",
        "start_hour": "2026-07-11T12:00",
        "end_hour": "2026-07-11T15:00",
        "timezone": "UTC",
    }


@pytest.mark.asyncio
async def test_normalizer_happy_path_native_domain() -> None:
    transport = _CapturingTransport(_canned_hourly(hours=4, values=[18.5, 19.0, 19.5, 20.0]))
    provider = OpenMeteoProvider(
        transport=transport,
        clock=STOPPED,
        parameters=core_parameters(),
    )
    coverage = await provider.project(_selection(hours=4))
    assert isinstance(coverage, CoverageRecord)

    domain = coverage.domain
    assert domain.axis(AxisName.X).extent.lower == pytest.approx(13.419998)
    assert domain.axis(AxisName.Y).extent.lower == pytest.approx(52.52)
    assert domain.axis(AxisName.Z).extent.lower == pytest.approx(2.0)
    assert len(domain.axis(AxisName.T)) == 4
    assert domain.axis(AxisName.T).extent.lower == datetime(2026, 7, 11, 12, 0, tzinfo=UTC)
    assert domain.axis(AxisName.T).extent.upper == datetime(2026, 7, 11, 15, 0, tzinfo=UTC)

    data = coverage.ranges[AIR_TEMPERATURE]
    assert list(data.values) == [18.5, 19.0, 19.5, 20.0]
    assert data.present is None


def test_unit_mismatch_raises_runtime_failure() -> None:
    normalizer = OpenMeteoNormalizer(core_parameters())
    with pytest.raises(RuntimeFailure, match="unit"):
        normalizer.normalize(_canned_hourly(unit="°F"), _sample_provenance())


def test_malformed_payload_raises_runtime_failure() -> None:
    normalizer = OpenMeteoNormalizer(core_parameters())
    with pytest.raises(RuntimeFailure):
        normalizer.normalize({"latitude": 1.0}, _sample_provenance())
    ragged = _canned_hourly(hours=4)
    ragged["hourly"]["temperature_2m"] = [1.0, 2.0]
    with pytest.raises(RuntimeFailure, match="length"):
        normalizer.normalize(ragged, _sample_provenance())


@pytest.mark.asyncio
async def test_provenance_authored_from_cadence_and_clock() -> None:
    transport = _CapturingTransport(_canned_hourly(hours=2))
    provider = OpenMeteoProvider(
        transport=transport,
        clock=STOPPED,
        parameters=core_parameters(),
    )
    coverage = await provider.project(_selection(hours=2))
    assert isinstance(coverage.provenance, Uniform)
    prov = coverage.provenance.summary(AIR_TEMPERATURE)
    now = STOPPED.now()
    assert isinstance(prov.origin, AtomicOrigin)
    assert prov.origin.source == SourceKey("open-meteo", "best_match")
    assert prov.origin.issue_time == CADENCE.anchor(now)
    assert prov.fetched_at == now
    assert prov.expiration == CADENCE.expiration(now)


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
    respx.get(f"{BASE_URL}/v1/forecast").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
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
