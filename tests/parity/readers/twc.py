"""Independent TWC reference reader for Provider parity checks.

Reads the enterprise hourly endpoint directly. Does not import meteoscape.

Where the Open-Meteo reader can verify the vendor's declared units, this one cannot: TWC echoes no
unit map, so what the numbers mean rests entirely on the `units` value *asked for*. So this reader
asks for `units=m` and applies the km/h→m/s conversion itself. A leaf drifted to another unit system
would disagree with it by a factor of 3.6, and this is the only place that would surface.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from parity.comparison import ReferenceTimeline

BASE_URL = "https://api.weather.com"
TO_PRODUCT: Mapping[str, str] = {
    "temperature": "air_temperature",
    "relativeHumidity": "relative_humidity",
    "qpf": "precipitation",
    "cloudCover": "cloud_cover",
    "windSpeed": "wind_speed",
    "windDirection": "wind_direction",
}


@dataclass(frozen=True)
class RawEvidence:
    url: str
    body: str


def _parse_epoch(stamp: object) -> datetime:
    if isinstance(stamp, bool) or not isinstance(stamp, (int, float)):
        raise ValueError(f"twc validTimeUtc is not a UNIX epoch: {stamp!r}")
    return datetime.fromtimestamp(int(stamp), tz=UTC)


def _optional_float(cell: object, name: str) -> float | None:
    if cell is None:
        return None
    if isinstance(cell, bool):
        raise ValueError(f"twc value for {name} is not numeric")
    if isinstance(cell, (int, float)):
        return float(cell)
    raise ValueError(f"twc value for {name} is not numeric")


def _to_canonical(name: str, value: float | None) -> float | None:
    if value is None:
        return None
    if name == "windSpeed":
        return value / 3.6
    return value


def _series(raw: Mapping[str, Any], name: str, ticks: int) -> Sequence[Any]:
    values = raw.get(name)
    if not isinstance(values, Sequence) or isinstance(values, str) or len(values) != ticks:
        raise ValueError(f"twc series malformed for {name}")
    return values


def parse_reference(body: str) -> ReferenceTimeline:
    raw: Any = json.loads(body)
    stamps = raw["validTimeUtc"]
    if not isinstance(stamps, Sequence) or isinstance(stamps, str) or not stamps:
        raise ValueError("twc validTimeUtc array malformed")
    valid_time = tuple(_parse_epoch(stamp) for stamp in stamps)

    values: dict[str, tuple[float | None, ...]] = {}
    for vendor_name, product_name in TO_PRODUCT.items():
        values[product_name] = tuple(
            _to_canonical(vendor_name, _optional_float(cell, vendor_name))
            for cell in _series(raw, vendor_name, len(valid_time))
        )
    return ReferenceTimeline(valid_time=valid_time, values=values)


def fetch_reference(
    latitude: float,
    longitude: float,
    *,
    duration: str,
    api_key: str,
) -> tuple[ReferenceTimeline, RawEvidence]:
    """The whole series for one offering duration — this vendor accepts no window to narrow it by.

    The comparison matches ticks by timestamp, so a reference wider than the answer is harmless.
    """
    params = {
        "geocode": f"{format(latitude, '.15g')},{format(longitude, '.15g')}",
        "units": "m",
        "language": "en-US",
        "format": "json",
        "apiKey": api_key,
    }
    with httpx.Client(timeout=60.0) as client:
        response = client.get(
            f"{BASE_URL}/v3/wx/forecast/hourly/{duration}/enterprise", params=params
        )
        response.raise_for_status()
    evidence = RawEvidence(url=str(response.url), body=response.text)
    return parse_reference(evidence.body), evidence
