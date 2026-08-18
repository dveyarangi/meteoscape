"""TWC reference reader — parse_reference is deterministic; fetch is live-only."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from parity.readers.twc import parse_reference

_FIXTURE = (
    Path(__file__).parent / "nodes" / "providers" / "fixtures" / "twc_hourly_10day.json"
).read_text(encoding="utf-8")

_CANNED = {
    "validTimeUtc": [int(datetime(2026, 7, 11, 12, tzinfo=UTC).timestamp())],
    "temperature": [18.0],
    "relativeHumidity": [50],
    "qpf": [0.1],
    "cloudCover": [40],
    "windSpeed": [36],
    "windDirection": [90],
}


def test_parse_reference_maps_converts_and_aware_times() -> None:
    timeline = parse_reference(json.dumps(_CANNED))
    assert timeline.valid_time == (datetime(2026, 7, 11, 12, tzinfo=UTC),)
    assert set(timeline.values) == {
        "air_temperature",
        "relative_humidity",
        "precipitation",
        "cloud_cover",
        "wind_speed",
        "wind_direction",
    }
    assert timeline.values["air_temperature"] == (18.0,)
    # The same 36 km/h -> 10 m/s the leaf's own test pins: agreement here is what makes a drifted
    # `units` request visible, since the vendor never says which system it answered in.
    assert timeline.values["wind_speed"] == pytest.approx((10.0,))
    assert timeline.values["wind_direction"] == (90.0,)


def test_parse_reference_reads_the_captured_envelope() -> None:
    timeline = parse_reference(_FIXTURE)
    assert timeline.valid_time == (
        datetime(2026, 8, 11, 12, tzinfo=UTC),
        datetime(2026, 8, 11, 13, tzinfo=UTC),
        datetime(2026, 8, 11, 14, tzinfo=UTC),
        datetime(2026, 8, 11, 15, tzinfo=UTC),
    )
    assert timeline.values["air_temperature"] == (2.6, 4.9, 6.6, 7.6)
    assert timeline.values["wind_speed"] == pytest.approx((2.5, 11 / 3.6, 14 / 3.6, 12 / 3.6))
    assert all(t.tzinfo is not None for t in timeline.valid_time)


def test_parse_reference_carries_nodata_positions() -> None:
    canned = json.loads(json.dumps(_CANNED))
    canned["temperature"] = [None]
    assert parse_reference(json.dumps(canned)).values["air_temperature"] == (None,)


def test_parse_reference_ragged_series_names_the_field() -> None:
    canned = json.loads(json.dumps(_CANNED))
    canned["cloudCover"] = [40, 41]
    with pytest.raises(ValueError, match="cloudCover"):
        parse_reference(json.dumps(canned))


def test_parse_reference_rejects_a_non_epoch_axis() -> None:
    canned = json.loads(json.dumps(_CANNED))
    canned["validTimeUtc"] = ["2026-07-11T12:00:00Z"]
    with pytest.raises(ValueError, match="validTimeUtc"):
        parse_reference(json.dumps(canned))
