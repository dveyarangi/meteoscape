"""End-to-end `forecast_hourly` over woven Open-Meteo with mocked HTTP."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx
from fastmcp import Client
from fastmcp.exceptions import ToolError

from fakes import snapped_point_domain
from meteoscape.api.mcp_app import build_mcp_app
from meteoscape.clock import Clock, StoppedClock
from meteoscape.config import Settings
from meteoscape.errors import RuntimeFailure
from meteoscape.manifold.cadence import RollingAxis
from meteoscape.manifold.core import Selection
from meteoscape.manifold.domain import AxisName, FootprintDomain, GridDomain, RegularAxis
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


def _compose_default(clock: Clock):
    settings = Settings()
    return compose(
        settings.profile(),
        PROVIDER_CATALOG,
        CALCULATOR_CATALOG,
        settings.secrets(),
        clock,
        StoreFactory(),
    )


def _canned_forecast(
    *,
    hours: int = _HOURS,
    start: datetime = datetime(2026, 7, 11, 12, 0, tzinfo=UTC),
) -> dict:
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
    app = build_mcp_app(gateway, _CLOCK)

    # The explicit window is exactly the 168 canned ticks (inclusive `end` = the last canned
    # tick), so the valid_time pins below survive the reach-end default verbatim.
    request = {
        "latitude": 52.52,
        "longitude": 13.41,
        "start": "2026-07-11T12:00",
        "end": "2026-07-18T11:00",
    }
    async with Client(app) as client:
        first = await client.call_tool("forecast_hourly", request)
        second = await client.call_tool("forecast_hourly", request)

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


@pytest.mark.asyncio
@respx.mock
async def test_forecast_hourly_default_window_is_the_full_reach() -> None:
    """Omitted bounds run from stopped noon to the day-anchored shelf end.

    The shelf has 384 hourly ticks; the 12 before noon are outside the default request.
    """
    respx.get(url__startswith=f"{BASE_URL}/v1/forecast").mock(
        return_value=httpx.Response(200, json=_canned_forecast(hours=372))
    )
    gateway = _compose_default(_CLOCK)
    app = build_mcp_app(gateway, _CLOCK)

    tool = await app.get_tool("forecast_hourly")
    assert tool is not None
    assert "out to 15 days ahead of the latest model run" in (tool.description or "")

    async with Client(app) as client:
        result = await client.call_tool(
            "forecast_hourly",
            {"latitude": 52.52, "longitude": 13.41},
        )

    payload = result.data
    assert len(payload["valid_time"]) == 372
    assert payload["valid_time"][0] == "2026-07-11T12:00:00Z"
    assert payload["valid_time"][-1] == "2026-07-26T23:00:00Z"


@pytest.mark.asyncio
@respx.mock
async def test_snapped_selection_resolves_through_the_woven_profile() -> None:
    """The mode end to end: bounds in, the leaf's lattice out.

    Mixed direct and derived parameters on purpose — that is **two** winners and two independent
    vendor fetches, so the answer geometry both assemble onto is the thing under test, not just the
    single-winner path. Enters at the Gateway: the geometry contract pinned here is the engine's,
    independent of the MCP edge's authoring.
    """
    route = respx.get(url__startswith=f"{BASE_URL}/v1/forecast").mock(
        return_value=httpx.Response(200, json=_canned_forecast())
    )
    gateway = _compose_default(_CLOCK)

    coverage = await gateway.resolve(
        Selection(
            domain=snapped_point_domain(
                start=datetime(2026, 7, 11, 14, 30, tzinfo=UTC),
                end=datetime(2026, 7, 11, 17, 10, tzinfo=UTC),
                lon=13.41,
                lat=52.52,
            ),
            parameters=frozenset({AIR_TEMPERATURE, WIND_SPEED}),
        )
    )

    # Mid-hour bounds floor onto the leaf's own ticks before the vendor is asked anything.
    assert route.call_count == 2
    asked = dict(route.calls[0].request.url.params)
    assert asked["start_hour"] == "2026-07-11T14:00"
    assert asked["end_hour"] == "2026-07-11T17:00"

    assert isinstance(coverage.domain, GridDomain)
    valid_time = coverage.domain.axis(AxisName.T)
    assert valid_time == RegularAxis(
        AxisName.T, datetime(2026, 7, 11, 14, tzinfo=UTC), timedelta(hours=1), 4, True
    )
    assert coverage.ranges[AIR_TEMPERATURE].values == pytest.approx([18.2, 18.3, 18.4, 18.0])
    assert coverage.ranges[WIND_SPEED].values == pytest.approx([1.0] * 4)


@pytest.mark.asyncio
@respx.mock
async def test_snapped_winner_domains_that_diverge_fail_the_whole_request() -> None:
    """The divergence a snapped request makes reachable — deliberately unhandled, so pinned loud.

    Each winner derives its T from its **own** fetch, so a vendor answering the two calls of one
    request with different reaches leaves two answers on two geometries. No fold reconciles them:
    the Arbiter's closed-projection check fails the request whole. Bounds run past the shorter
    response on purpose — bounds inside both would ground identically and hide it.
    """
    respx.get(url__startswith=f"{BASE_URL}/v1/forecast").mock(
        side_effect=[
            httpx.Response(200, json=_canned_forecast(hours=168)),
            httpx.Response(200, json=_canned_forecast(hours=100)),
        ]
    )
    gateway = _compose_default(_CLOCK)

    with pytest.raises(RuntimeFailure, match="closed-projection invariant broken"):
        await gateway.resolve(
            Selection(
                domain=snapped_point_domain(
                    start=datetime(2026, 7, 11, 14, 30, tzinfo=UTC),
                    end=datetime(2026, 7, 18, 11, 10, tzinfo=UTC),
                    lon=13.41,
                    lat=52.52,
                ),
                parameters=frozenset({AIR_TEMPERATURE, WIND_SPEED}),
            )
        )


@pytest.mark.asyncio
@respx.mock
async def test_history_window_is_capability_mismatch_with_no_vendor_call() -> None:
    """A well-formed window wholly before the live window: admission answers, nothing is fetched.

    The edge never rejects on reach's word — the mismatch is intersective admission's (m4), so
    the proof it happened at admission is that the vendor was never asked.
    """
    route = respx.get(url__startswith=f"{BASE_URL}/v1/forecast").mock(
        return_value=httpx.Response(200, json=_canned_forecast())
    )
    gateway = _compose_default(_CLOCK)
    app = build_mcp_app(gateway, _CLOCK)

    async with Client(app) as client:
        with pytest.raises(ToolError, match=r"^capability-mismatch:"):
            await client.call_tool(
                "forecast_hourly",
                {
                    "latitude": 52.52,
                    "longitude": 13.41,
                    "start": "2025-07-11T12:00",
                    "end": "2025-07-18T11:00",
                },
            )
    assert route.call_count == 0


@pytest.mark.asyncio
@respx.mock
async def test_out_of_range_bounds_fetch_exactly_the_clipped_window() -> None:
    """An early `start` and an over-horizon `end` reach the vendor as the clipped lattice.

    The winner grounds `bounds ∩ its live window` on its own grid and asks for exactly that —
    `[today00, today00+383h]` under the stopped noon clock. Direct parameter only (one winner,
    one fetch), so the captured query is the whole vendor conversation.
    """
    midnight = datetime(2026, 7, 11, 0, tzinfo=UTC)
    route = respx.get(url__startswith=f"{BASE_URL}/v1/forecast").mock(
        return_value=httpx.Response(200, json=_canned_forecast(hours=408, start=midnight))
    )
    gateway = _compose_default(_CLOCK)
    app = build_mcp_app(gateway, _CLOCK)

    async with Client(app) as client:
        await client.call_tool(
            "forecast_hourly",
            {
                "latitude": 52.52,
                "longitude": 13.41,
                "parameters": ["air_temperature"],
                "start": "2026-07-01T00:00",
                "end": "2026-09-01T00:00",
            },
        )

    assert route.call_count == 1
    asked = dict(route.calls[0].request.url.params)
    assert asked["start_hour"] == "2026-07-11T00:00"
    assert asked["end_hour"] == "2026-07-26T23:00"


@pytest.mark.asyncio
@respx.mock
async def test_short_vendor_delivery_is_disclosed_not_failed() -> None:
    """A vendor answering fewer ticks than declared is an honest shorter answer, not a fault.

    The same 168-asked/100-delivered pair as the divergence pin above, but direct parameters
    only — one winner, one fetch — so the shorter delivery exercises disclosure instead of
    tripping the closed-projection check. The response's `valid_time` is the disclosure: it shows
    the 100-tick window actually served.
    """
    respx.get(url__startswith=f"{BASE_URL}/v1/forecast").mock(
        return_value=httpx.Response(200, json=_canned_forecast(hours=100))
    )
    gateway = _compose_default(_CLOCK)
    app = build_mcp_app(gateway, _CLOCK)

    async with Client(app) as client:
        result = await client.call_tool(
            "forecast_hourly",
            {
                "latitude": 52.52,
                "longitude": 13.41,
                "parameters": ["air_temperature"],
                "start": "2026-07-11T12:00",
                "end": "2026-07-18T11:00",
            },
        )

    payload = result.data
    assert len(payload["valid_time"]) == 100
    assert payload["valid_time"][0] == "2026-07-11T12:00:00Z"
    assert payload["valid_time"][-1] == "2026-07-15T15:00:00Z"


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
