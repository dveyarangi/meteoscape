"""Live TWC Provider parity check — opt-in via `uv run pytest tests/parity`, and key-gated.

Open-Meteo needs no key, so this is the first parity check that can be unrunnable. It skips with the
variable named rather than failing: an absent key means the operator cannot run it, not that the
producer disagrees.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastmcp import Client

from meteoscape.api.mcp_app import build_mcp_app
from meteoscape.clock import Metronome
from meteoscape.config import Settings
from meteoscape.nodes.calculators.wind import CALM_SPEED_FLOOR
from meteoscape.server import CALCULATOR_CATALOG, PROVIDER_CATALOG, compose
from parity.comparison import (
    Absolute,
    CalmRule,
    Circular,
    Exact,
    ParitySpec,
    compare,
    format_summary,
    write_evidence,
)
from parity.readers.twc import RawEvidence, fetch_reference

_LAT = 52.52
_LON = 13.41
_REQUEST = {"latitude": _LAT, "longitude": _LON}
_DURATION = "10day"
"""The vendor path segment behind `hourly_10day`, the manifest's default offering — restated here
rather than imported, since a reference reader sharing the leaf's mapping would verify nothing."""
ATTEMPTS = 2

SPEC = ParitySpec(
    rules={
        # Four of six arrive as the vendor's own documented Decimal/Integer values, so both sides
        # read identical numbers. Wind alone round-trips through u/v trigonometry and the km/h
        # conversion, which the reference reader performs independently.
        "air_temperature": Exact(),
        "relative_humidity": Exact(),
        "precipitation": Exact(),
        "cloud_cover": Exact(),
        "wind_speed": Absolute(tol=1e-6),
        "wind_direction": Circular(tol_deg=1e-6),
    },
    calm=CalmRule("wind_speed", "wind_direction", CALM_SPEED_FLOOR),
)


def _keyed_settings(cli_key: str | None) -> Settings:
    """TWC as the only producer, so the payload under comparison can be nobody else's."""
    settings = (
        Settings(open_meteo_enabled=False, twc_api_key=cli_key)
        if cli_key
        else Settings(open_meteo_enabled=False)
    )
    if "twc_api_key" not in settings.secrets():
        pytest.skip(
            "TWC parity needs a key: pass --twc-api-key or set METEOSCAPE_TWC_API_KEY; neither is present"
        )
    return settings


async def _forecast_payload(settings: Settings) -> dict[str, Any]:
    clock = Metronome()
    gateway = compose(
        settings.profile(),
        PROVIDER_CATALOG,
        CALCULATOR_CATALOG,
        settings.secrets(),
        clock,
    )
    app = build_mcp_app(gateway, clock)
    async with Client(app) as client:
        result = await client.call_tool("forecast_hourly", _REQUEST)
    payload = result.data
    assert isinstance(payload, dict)
    return payload


@pytest.mark.asyncio
async def test_twc_parity(request: pytest.FixtureRequest) -> None:
    settings = _keyed_settings(request.config.getoption("--twc-api-key"))
    api_key = settings.secrets()["twc_api_key"]
    request_desc = f"forecast_hourly lat={_LAT} lon={_LON} default window UTC"
    payload: dict[str, Any] | None = None
    raw: RawEvidence | None = None
    report = None
    for _ in range(ATTEMPTS):
        payload = await _forecast_payload(settings)
        reference, raw = fetch_reference(_LAT, _LON, duration=_DURATION, api_key=api_key)
        report = compare(payload, reference, SPEC)
        if report.ok:
            return

    assert payload is not None and raw is not None and report is not None
    # The key travels in the reference URL's query string, so every artifact goes through the scrub.
    evidence = write_evidence(
        "twc",
        {
            "meteoscape_request": {"tool": "forecast_hourly", **_REQUEST},
            "meteoscape_payload": payload,
            "reference_request": {"url": raw.url},
            "reference_response": raw.body,
            "diff": report,
        },
        settings.secrets(),
    )
    pytest.fail(
        format_summary(
            "twc",
            request_desc,
            report,
            evidence,
            secrets=settings.secrets(),
        )
    )
