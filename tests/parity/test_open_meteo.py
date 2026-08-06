"""Live Open-Meteo Provider parity check — opt-in via `uv run pytest tests/parity`."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from fastmcp import Client

from meteoscape.api.mcp_app import build_mcp_app
from meteoscape.clock import Metronome
from meteoscape.config import Settings
from meteoscape.nodes.calculators.wind import CALM_SPEED_FLOOR
from meteoscape.nodes.store import StoreFactory
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
from parity.readers.open_meteo import RawEvidence, fetch_reference

_LAT = 52.52
_LON = 13.41
_REQUEST = {"latitude": _LAT, "longitude": _LON}
ATTEMPTS = 2

SPEC = ParitySpec(
    rules={
        "air_temperature": Exact(),
        "relative_humidity": Exact(),
        "precipitation": Exact(),
        "cloud_cover": Exact(),
        "wind_speed": Absolute(tol=1e-6),
        "wind_direction": Circular(tol_deg=1e-6),
    },
    calm=CalmRule("wind_speed", "wind_direction", CALM_SPEED_FLOOR),
)


def _window(valid_times: list[str]) -> tuple[datetime, datetime]:
    start = datetime.fromisoformat(valid_times[0].replace("Z", "+00:00")).astimezone(UTC)
    end = datetime.fromisoformat(valid_times[-1].replace("Z", "+00:00")).astimezone(UTC)
    return start, end


async def _forecast_payload(settings: Settings) -> dict[str, Any]:
    clock = Metronome()
    gateway = compose(
        settings.profile(),
        PROVIDER_CATALOG,
        CALCULATOR_CATALOG,
        settings.secrets(),
        clock,
        StoreFactory(),
    )
    app = build_mcp_app(gateway, clock)
    async with Client(app) as client:
        result = await client.call_tool("forecast_hourly", _REQUEST)
    payload = result.data
    assert isinstance(payload, dict)
    return payload


@pytest.mark.asyncio
async def test_open_meteo_parity() -> None:
    settings = Settings(open_meteo_enabled=True, twc_api_key=None)
    request_desc = f"forecast_hourly lat={_LAT} lon={_LON} default window UTC"
    payload: dict[str, Any] | None = None
    raw: RawEvidence | None = None
    report = None
    for _ in range(ATTEMPTS):
        payload = await _forecast_payload(settings)
        start, end = _window(payload["valid_time"])
        reference, raw = fetch_reference(_LAT, _LON, start, end)
        report = compare(payload, reference, SPEC)
        if report.ok:
            return

    assert payload is not None and raw is not None and report is not None
    evidence = write_evidence(
        "open-meteo",
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
            "open-meteo",
            request_desc,
            report,
            evidence,
            secrets=settings.secrets(),
        )
    )
