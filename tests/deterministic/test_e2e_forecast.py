"""End-to-end `forecast_hourly` over woven Open-Meteo with mocked HTTP."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx
from fastmcp import Client
from fastmcp.exceptions import ToolError

from fakes import TWC_PRIMARY_OFFERINGS, pinned_settings, snapped_point_domain
from meteoscape.api.mcp_app import build_mcp_app
from meteoscape.clock import Clock, StoppedClock
from meteoscape.config import ArbiterPolicy, ProfileConfig
from meteoscape.manifold.cadence import RollingAxis
from meteoscape.manifold.core import Selection
from meteoscape.manifold.domain import AxisName, FootprintDomain, GridDomain, RegularAxis
from meteoscape.nodes.calculators import builtin as calculators
from meteoscape.nodes.providers import builtin as providers
from meteoscape.nodes.providers.open_meteo import BASE_URL, CADENCE
from meteoscape.nodes.providers.twc import BASE_URL as TWC_BASE_URL
from meteoscape.parameters import AIR_TEMPERATURE, WIND_DIRECTION, WIND_SPEED
from meteoscape.server import CALCULATORS, OFFERINGS, compose

_CLOCK = StoppedClock(datetime(2026, 7, 11, 12, 0, tzinfo=UTC))
_HOURS = 168


class _AdvancingClock:
    """Mutable clock: moving `instant` rolls every leaf's `RollingAxis` T — the liveness probe."""

    def __init__(self, instant: datetime) -> None:
        self.instant = instant

    def now(self) -> datetime:
        return self.instant


def _compose_default(clock: Clock, *, store_spatial_step: float | None = None):
    settings = (
        pinned_settings()
        if store_spatial_step is None
        else pinned_settings(store_spatial_step=store_spatial_step)
    )
    return compose(
        ProfileConfig(OFFERINGS, CALCULATORS, settings.root_store(), ArbiterPolicy()),
        providers.CATALOG,
        calculators.CATALOG,
        {},
        clock,
    )


def _compose_both(clock: Clock):
    settings = pinned_settings()
    return compose(
        ProfileConfig(TWC_PRIMARY_OFFERINGS, CALCULATORS, settings.root_store(), ArbiterPolicy()),
        providers.CATALOG,
        calculators.CATALOG,
        {"twc": "test-key"},
        clock,
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


def _canned_twc(
    *,
    hours: int = 240,
    start: datetime = datetime(2026, 7, 11, 12, 0, tzinfo=UTC),
) -> dict:
    epochs = [int((start + timedelta(hours=i)).timestamp()) for i in range(hours)]
    return {
        "validTimeUtc": epochs,
        "temperature": [18.0] * hours,
        "relativeHumidity": [50] * hours,
        "qpf": [0.0] * hours,
        "cloudCover": [40] * hours,
        "windSpeed": [36] * hours,
        "windDirection": [90] * hours,
    }


@pytest.mark.asyncio
@respx.mock
async def test_forecast_hourly_e2e_and_refetch() -> None:
    route = respx.get(url__startswith=f"{BASE_URL}/v1/forecast").mock(
        return_value=httpx.Response(200, json=_canned_forecast())
    )
    gateway = _compose_default(_CLOCK)
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

    # Retention: one vendor trip warms the whole offering; the repeat serves from store.
    assert route.call_count == 1

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
async def test_points_within_one_store_cell_share_one_vendor_call() -> None:
    """Two off-grid points in one root cell share one vendor trip and one value series.

    A coarse root step (0.5 deg) makes the fidelity floor observable: both asks fall in
    `[13.0, 13.5)` by `[52.5, 53.0)`, so the vendor is asked once, at the cell tick. This surface
    serializes no coordinate (`serialize_coverage` emits `valid_time` and the parameter blocks
    only), so the identical value series *is* the caller-visible evidence - the fidelity-floor
    invariant on the MCP edge record. Compose once: a second empty store would hide the claim.
    """
    route = respx.get(url__startswith=f"{BASE_URL}/v1/forecast").mock(
        return_value=httpx.Response(200, json=_canned_forecast())
    )
    gateway = _compose_default(_CLOCK, store_spatial_step=0.5)
    app = build_mcp_app(gateway, _CLOCK)
    window = {
        "parameters": ["air_temperature"],
        "start": "2026-07-11T12:00",
        "end": "2026-07-18T11:00",
    }
    async with Client(app) as client:
        first = await client.call_tool(
            "forecast_hourly",
            {"latitude": 52.52, "longitude": 13.41, **window},
        )
        second = await client.call_tool(
            "forecast_hourly",
            {"latitude": 52.52, "longitude": 13.44, **window},
        )

    assert route.call_count == 1
    asked = dict(route.calls[0].request.url.params)
    assert float(asked["longitude"]) == pytest.approx(13.0, abs=1e-9)
    assert float(asked["latitude"]) == pytest.approx(52.5, abs=1e-9)
    assert first.data["air_temperature"]["values"] == second.data["air_temperature"]["values"]


@pytest.mark.asyncio
@respx.mock
async def test_expired_holdings_refetch_and_never_serve_stale() -> None:
    """Past cadence expiration the Arbiter path refills — retention only bounds memory.

    Open-Meteo's run at stopped noon expires at 13:00; advancing the shared clock past that
    forces a second vendor trip. The store may still hold the Holding (14-day retention), but the
    Reservoir gate refuses to serve it stale.
    """
    clock = _AdvancingClock(datetime(2026, 7, 11, 12, 0, tzinfo=UTC))
    route = respx.get(url__startswith=f"{BASE_URL}/v1/forecast").mock(
        return_value=httpx.Response(200, json=_canned_forecast())
    )
    gateway = _compose_default(clock)
    app = build_mcp_app(gateway, clock)
    request = {
        "latitude": 52.52,
        "longitude": 13.41,
        "parameters": ["air_temperature"],
        "start": "2026-07-11T12:00",
        "end": "2026-07-18T11:00",
    }
    async with Client(app) as client:
        await client.call_tool("forecast_hourly", request)
        assert route.call_count == 1
        clock.instant = datetime(2026, 7, 11, 14, 0, tzinfo=UTC)
        await client.call_tool("forecast_hourly", request)
    assert route.call_count == 2


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

    # Under retention the refill asks ANY on T — one vendor trip for the whole live window;
    # the served answer still crops to the grounded mid-hour bounds.
    assert route.call_count == 1
    asked = dict(route.calls[0].request.url.params)
    assert asked["start_hour"] == "2026-07-11T00:00"
    assert asked["end_hour"] == "2026-07-26T23:00"

    assert isinstance(coverage.domain, GridDomain)
    valid_time = coverage.domain.axis(AxisName.T)
    assert valid_time == RegularAxis(
        AxisName.T, datetime(2026, 7, 11, 14, tzinfo=UTC), timedelta(hours=1), 4, True
    )
    assert coverage.ranges[AIR_TEMPERATURE].values == pytest.approx([18.2, 18.3, 18.4, 18.0])
    assert coverage.ranges[WIND_SPEED].values == pytest.approx([1.0] * 4)


@pytest.mark.asyncio
@respx.mock
async def test_snapped_mixed_request_shares_one_vendor_geometry() -> None:
    """A shared Source's natural fetch unit gives both winners one delivered T geometry.

    One trip warms every parameter, so both winners ground onto the same delivered lattice.
    """
    route = respx.get(url__startswith=f"{BASE_URL}/v1/forecast").mock(
        return_value=httpx.Response(200, json=_canned_forecast(hours=168))
    )
    gateway = _compose_default(_CLOCK)

    coverage = await gateway.resolve(
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
    assert route.call_count == 1
    assert AIR_TEMPERATURE in coverage.ranges
    assert WIND_SPEED in coverage.ranges


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

    A 168-asked/100-delivered pair with direct parameters only — one winner, one fetch — so the
    shorter delivery exercises disclosure instead of tripping the closed-projection check (whose
    own guard lives at the fold: `test_winner_domains_that_differ_fail_the_whole_request`). The
    response's `valid_time` is the disclosure: it shows the 100-tick window actually served.
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
    """The public root exposes the leaf's own live Domain as its reach."""
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


@pytest.mark.asyncio
@respx.mock
async def test_default_ask_with_twc_primary_answers_twc_horizon() -> None:
    """Composed narration stays the longer reach; the answer is the primary's clipped window."""
    twc = respx.get(url__startswith=f"{TWC_BASE_URL}/v3/wx/forecast/hourly/").mock(
        return_value=httpx.Response(200, json=_canned_twc())
    )
    om = respx.get(url__startswith=f"{BASE_URL}/v1/forecast").mock(
        return_value=httpx.Response(200, json=_canned_forecast(hours=372))
    )
    gateway = _compose_both(_CLOCK)
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
    assert twc.call_count == 1
    assert om.call_count == 0
    assert payload["valid_time"][0] == "2026-07-11T12:00:00Z"
    assert payload["valid_time"][-1] == "2026-07-21T11:00:00Z"
    assert len(payload["valid_time"]) == 240
    assert payload["air_temperature"]["provenance"]["source"] == "twc:hourly_10day"


@pytest.mark.asyncio
@respx.mock
async def test_ask_wholly_past_twc_is_capability_mismatch() -> None:
    """A tail past the primary does not fall through to Open-Meteo through the root store."""
    twc = respx.get(url__startswith=f"{TWC_BASE_URL}/v3/wx/forecast/hourly/").mock(
        return_value=httpx.Response(200, json=_canned_twc())
    )
    om = respx.get(url__startswith=f"{BASE_URL}/v1/forecast").mock(
        return_value=httpx.Response(200, json=_canned_forecast(hours=372))
    )
    gateway = _compose_both(_CLOCK)
    app = build_mcp_app(gateway, _CLOCK)

    async with Client(app) as client:
        with pytest.raises(ToolError, match=r"^capability-mismatch:"):
            await client.call_tool(
                "forecast_hourly",
                {
                    "latitude": 52.52,
                    "longitude": 13.41,
                    "start": "2026-07-22T00:00",
                    "end": "2026-07-22T12:00",
                },
            )
    assert om.call_count == 0
    assert twc.call_count >= 1


@pytest.mark.asyncio
@respx.mock
async def test_primary_429_falls_through_to_backstop() -> None:
    """A metered primary's 429 is a RuntimeFailure; the request survives on Open-Meteo."""
    respx.get(url__startswith=f"{TWC_BASE_URL}/v3/wx/forecast/hourly/").mock(
        return_value=httpx.Response(429, json={"ok": False})
    )
    respx.get(url__startswith=f"{BASE_URL}/v1/forecast").mock(
        return_value=httpx.Response(200, json=_canned_forecast())
    )
    gateway = _compose_both(_CLOCK)
    app = build_mcp_app(gateway, _CLOCK)
    exp = CADENCE.expiration(_CLOCK.now()).strftime("%Y-%m-%dT%H:%M:%SZ")

    async with Client(app) as client:
        result = await client.call_tool(
            "forecast_hourly",
            {
                "latitude": 52.52,
                "longitude": 13.41,
                "start": "2026-07-11T12:00",
                "end": "2026-07-18T11:00",
            },
        )

    payload = result.data
    served = {name: block for name, block in payload.items() if name != "valid_time"}
    assert served
    for block in served.values():
        assert block["provenance"]["source"] == "open-meteo:best_match"
        assert block["provenance"]["exp"] == exp
