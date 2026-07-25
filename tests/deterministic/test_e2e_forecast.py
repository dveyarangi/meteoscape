"""End-to-end `forecast_hourly` over woven Open-Meteo with mocked HTTP."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx
from fastmcp import Client

from meteoscape.api.mcp_app import build_mcp_app
from meteoscape.clock import StoppedClock
from meteoscape.config import Settings
from meteoscape.manifold.cadence import RollingAxis
from meteoscape.manifold.domain import AxisName, FootprintDomain
from meteoscape.nodes.providers.open_meteo import BASE_URL, CADENCE
from meteoscape.nodes.store import StoreFactory
from meteoscape.parameters import AIR_TEMPERATURE, WIND_DIRECTION, WIND_SPEED
from meteoscape.server import CALCULATOR_CATALOG, PROVIDER_CATALOG, compose

_CLOCK = StoppedClock(datetime(2026, 7, 11, 12, 0, tzinfo=UTC))
_HOURS = 168


class _AdvancingClock:
    """Mutable clock: moving `instant` rolls every leaf's `RollingAxis` T — the liveness probe."""

    def __init__(self, instant: datetime) -> None:
        self.instant = instant

    def now(self) -> datetime:
        return self.instant


def _compose_default(clock: _AdvancingClock):
    settings = Settings()
    return compose(
        settings.profile(),
        PROVIDER_CATALOG,
        CALCULATOR_CATALOG,
        settings.secrets(),
        clock,
        StoreFactory(),
    )


def _canned_forecast(*, hours: int = _HOURS) -> dict:
    start = datetime(2026, 7, 11, 12, 0, tzinfo=UTC)
    times = [(start + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(hours)]
    return {
        "latitude": 52.52,
        "longitude": 13.419998,
        "hourly_units": {
            "time": "iso8601",
            "temperature_2m": "°C",
            "relative_humidity_2m": "%",
            "wind_speed_10m": "km/h",
            "wind_direction_10m": "°",
            "precipitation": "mm",
            "cloud_cover": "%",
        },
        "hourly": {
            "time": times,
            "temperature_2m": [18.0 + (i % 5) * 0.1 for i in range(hours)],
            "relative_humidity_2m": [50.0] * hours,
            "wind_speed_10m": [3.6] * hours,
            "wind_direction_10m": [0.0] * hours,
            "precipitation": [0.0] * hours,
            "cloud_cover": [40.0] * hours,
        },
    }


@pytest.mark.asyncio
@respx.mock
async def test_forecast_hourly_e2e_and_refetch() -> None:
    route = respx.get(url__startswith=f"{BASE_URL}/v1/forecast").mock(
        return_value=httpx.Response(200, json=_canned_forecast())
    )
    settings = Settings()
    gateway = compose(
        settings.profile(),
        PROVIDER_CATALOG,
        CALCULATOR_CATALOG,
        settings.secrets(),
        _CLOCK,
        StoreFactory(),
    )
    app = build_mcp_app(gateway, _CLOCK, settings.default_horizon)

    async with Client(app) as client:
        first = await client.call_tool(
            "forecast_hourly",
            {"latitude": 52.52, "longitude": 13.41},
        )
        second = await client.call_tool(
            "forecast_hourly",
            {"latitude": 52.52, "longitude": 13.41},
        )

    # StubStore has no retention: each request performs one source fetch plus one wind u/v fetch.
    # A retentive Store will make the second request reuse both.
    assert route.call_count == 4

    payload = first.data
    assert len(payload["valid_time"]) == _HOURS
    assert payload["valid_time"][0] == "2026-07-11T12:00:00Z"
    assert payload["valid_time"][-1] == "2026-07-18T11:00:00Z"

    block = payload["air_temperature"]
    assert block["unit"] == "degC"
    assert len(block["values"]) == _HOURS
    assert block["values"][0] == pytest.approx(18.0)
    assert None not in block["values"]

    assert "precipitation" in payload
    assert "relative_humidity" in payload
    assert "cloud_cover" in payload
    assert "wind_speed" in payload
    assert "wind_direction" in payload
    assert "wind_u" not in payload
    assert "wind_v" not in payload

    now = _CLOCK.now()
    assert block["provenance"] == {
        "source": "open-meteo:best_match",
        "exp": CADENCE.expiration(now).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    wind = payload["wind_speed"]
    assert wind["unit"] == "m/s"
    assert wind["values"][0] == pytest.approx(1.0)  # 3.6 km/h → 1 m/s
    assert wind["provenance"] == {
        "source": "open-meteo:best_match",
        "exp": CADENCE.expiration(now).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    assert payload["wind_direction"]["unit"] == "degree"
    assert payload["wind_direction"]["values"][0] == pytest.approx(0.0)
    assert payload["wind_direction"]["provenance"] == wind["provenance"]

    assert second.data["air_temperature"]["values"] == first.data["air_temperature"]["values"]


def test_root_reach_is_the_live_leaf_domain_for_a_direct_parameter() -> None:
    """The reach the ticket exists for: readable off the public root, the leaf's own live Domain."""
    clock = _AdvancingClock(datetime(2026, 7, 11, 12, 0, tzinfo=UTC))
    capability = _compose_default(clock).best_view.capability
    reach = capability.reach(AIR_TEMPERATURE)
    assert capability.reach(AIR_TEMPERATURE) is reach  # composed once, not rebuilt per read
    assert isinstance(reach, FootprintDomain)
    assert reach.axis(AxisName.X).extent.lower == pytest.approx(-180.0)
    assert reach.axis(AxisName.X).extent.upper == pytest.approx(180.0)
    assert reach.axis(AxisName.Y).extent.lower == pytest.approx(-90.0)
    assert isinstance(reach.axis(AxisName.T), RollingAxis)
    before = reach.axis(AxisName.T).extent.upper
    clock.instant = clock.instant + timedelta(days=1)
    assert reach.axis(AxisName.T).extent.upper == before + timedelta(days=1)


def test_root_reach_resolves_a_derived_parameter_through_the_calculator() -> None:
    """Derived reach off the root exercises DerivedCapability → scoped Arbiter → top Arbiter →
    Reservoir forwarding in one path; co-produced outputs share the one contained-in-all domain."""
    clock = _AdvancingClock(datetime(2026, 7, 11, 12, 0, tzinfo=UTC))
    capability = _compose_default(clock).best_view.capability
    speed = capability.reach(WIND_SPEED)
    assert speed is capability.reach(WIND_DIRECTION)  # one derived reach for both outputs
    assert isinstance(speed, FootprintDomain)
    assert speed.axis(AxisName.X).extent.lower == pytest.approx(-180.0)
    assert speed.axis(AxisName.X).extent.upper == pytest.approx(180.0)
    assert isinstance(speed.axis(AxisName.T), RollingAxis)
    before = speed.axis(AxisName.T).extent.upper
    clock.instant = clock.instant + timedelta(days=1)
    assert speed.axis(AxisName.T).extent.upper == before + timedelta(days=1)
