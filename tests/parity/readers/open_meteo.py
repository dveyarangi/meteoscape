"""Independent Open-Meteo reference reader for Provider parity checks.

Reads the public JSON forecast API directly. Does not import meteoscape — the official
FlatBuffers client was judged unsuitable (opaque failure evidence, extra deps); the JSON
API is itself the canonical documented interface for this producer.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from parity.comparison import ReferenceTimeline

BASE_URL = "https://api.open-meteo.com/v1/forecast"
HOURLY = (
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "cloud_cover",
    "wind_speed_10m",
    "wind_direction_10m",
)
EXPECTED_UNITS: Mapping[str, str] = {
    "temperature_2m": "°C",
    "relative_humidity_2m": "%",
    "precipitation": "mm",
    "cloud_cover": "%",
    "wind_speed_10m": "km/h",
    "wind_direction_10m": "°",
}
TO_PRODUCT: Mapping[str, str] = {
    "temperature_2m": "air_temperature",
    "relative_humidity_2m": "relative_humidity",
    "precipitation": "precipitation",
    "cloud_cover": "cloud_cover",
    "wind_speed_10m": "wind_speed",
    "wind_direction_10m": "wind_direction",
}


@dataclass(frozen=True)
class RawEvidence:
    url: str
    body: str


def _fmt_hour(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M")


def _parse_vendor_time(stamp: object) -> datetime:
    if not isinstance(stamp, str):
        raise ValueError(f"open-meteo hourly time is not a string: {stamp!r}")
    parsed = datetime.fromisoformat(stamp)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _optional_float(cell: object, name: str) -> float | None:
    if cell is None:
        return None
    if isinstance(cell, bool):
        raise ValueError(f"open-meteo value for {name} is not numeric")
    if isinstance(cell, (int, float)):
        return float(cell)
    raise ValueError(f"open-meteo value for {name} is not numeric")


def _to_canonical(name: str, value: float | None) -> float | None:
    if value is None:
        return None
    if name == "wind_speed_10m":
        return value / 3.6
    return value


def parse_reference(body: str) -> ReferenceTimeline:
    raw: Any = json.loads(body)
    units = raw["hourly_units"]
    hourly = raw["hourly"]
    for name, expected in EXPECTED_UNITS.items():
        reported = units.get(name)
        if reported != expected:
            raise ValueError(
                f"open-meteo unit drift for {name}: expected {expected!r}, got {reported!r}"
            )

    times_raw = hourly["time"]
    if not isinstance(times_raw, Sequence):
        raise ValueError("open-meteo hourly time array malformed")
    valid_time = tuple(_parse_vendor_time(t) for t in times_raw)
    n = len(valid_time)

    values: dict[str, tuple[float | None, ...]] = {}
    for vendor_name, product_name in TO_PRODUCT.items():
        series = hourly.get(vendor_name)
        if not isinstance(series, Sequence) or len(series) != n:
            raise ValueError(f"open-meteo hourly array malformed for {vendor_name}")
        values[product_name] = tuple(
            _to_canonical(vendor_name, _optional_float(cell, vendor_name)) for cell in series
        )
    return ReferenceTimeline(valid_time=valid_time, values=values)


def fetch_reference(
    latitude: float,
    longitude: float,
    start: datetime,
    end: datetime,
) -> tuple[ReferenceTimeline, RawEvidence]:
    params = {
        "latitude": format(latitude, ".15g"),
        "longitude": format(longitude, ".15g"),
        "hourly": ",".join(HOURLY),
        "start_hour": _fmt_hour(start),
        "end_hour": _fmt_hour(end),
        "timezone": "UTC",
    }
    with httpx.Client(timeout=60.0) as client:
        response = client.get(BASE_URL, params=params)
        response.raise_for_status()
    evidence = RawEvidence(url=str(response.url), body=response.text)
    return parse_reference(evidence.body), evidence
