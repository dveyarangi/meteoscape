"""Open-Meteo reference reader — parse_reference is deterministic; fetch is live-only."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from parity.readers.open_meteo import parse_reference

_CANNED = {
    "latitude": 52.52,
    "longitude": 13.41,
    "hourly_units": {
        "time": "iso8601",
        "temperature_2m": "°C",
        "relative_humidity_2m": "%",
        "precipitation": "mm",
        "cloud_cover": "%",
        "wind_speed_10m": "km/h",
        "wind_direction_10m": "°",
    },
    "hourly": {
        "time": ["2026-07-11T12:00", "2026-07-11T13:00"],
        "temperature_2m": [18.0, None],
        "relative_humidity_2m": [50.0, 55.0],
        "precipitation": [0.0, 0.1],
        "cloud_cover": [40.0, 41.0],
        "wind_speed_10m": [3.6, 7.2],
        "wind_direction_10m": [0.0, 90.0],
    },
}


def test_parse_reference_maps_converts_and_aware_times() -> None:
    timeline = parse_reference(json.dumps(_CANNED))
    assert timeline.valid_time == (
        datetime(2026, 7, 11, 12, 0, tzinfo=UTC),
        datetime(2026, 7, 11, 13, 0, tzinfo=UTC),
    )
    assert set(timeline.values) == {
        "air_temperature",
        "relative_humidity",
        "precipitation",
        "cloud_cover",
        "wind_speed",
        "wind_direction",
    }
    assert timeline.values["air_temperature"] == (18.0, None)
    assert timeline.values["wind_speed"] == pytest.approx((1.0, 2.0))
    assert timeline.values["wind_direction"] == (0.0, 90.0)
    assert all(t.tzinfo is not None for t in timeline.valid_time)


def test_parse_reference_unit_drift_names_field() -> None:
    bad = json.loads(json.dumps(_CANNED))
    bad["hourly_units"]["wind_speed_10m"] = "m/s"
    with pytest.raises(ValueError, match="wind_speed_10m"):
        parse_reference(json.dumps(bad))
