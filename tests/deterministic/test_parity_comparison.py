"""Deterministic coverage of the parity comparison engine (no network)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from parity.comparison import (
    Absolute,
    CalmRule,
    Circular,
    Exact,
    Mismatch,
    ParitySpec,
    ReferenceTimeline,
    compare,
    format_summary,
    write_evidence,
)

_T0 = datetime(2026, 7, 11, 12, 0, tzinfo=UTC)
_T1 = datetime(2026, 7, 11, 13, 0, tzinfo=UTC)


def _payload(valid_times: list[str], **series: list[float | None]) -> dict[str, object]:
    out: dict[str, object] = {"valid_time": valid_times}
    for name, values in series.items():
        out[name] = {"unit": "x", "values": values, "provenance": {}}
    return out


def _ref(ticks: list[datetime], **series: list[float | None]) -> ReferenceTimeline:
    return ReferenceTimeline(valid_time=ticks, values=series)


def test_exact_match_is_ok() -> None:
    payload = _payload(["2026-07-11T12:00:00Z"], air_temperature=[1.0])
    reference = _ref([_T0], air_temperature=[1.0])
    report = compare(payload, reference, ParitySpec(rules={"air_temperature": Exact()}, calm=None))
    assert report.ok
    assert report.compared == 1
    assert report.mismatches == ()


def test_exact_mismatch_reports_difference() -> None:
    payload = _payload(["2026-07-11T12:00:00Z"], air_temperature=[1.0])
    reference = _ref([_T0], air_temperature=[2.0])
    report = compare(payload, reference, ParitySpec(rules={"air_temperature": Exact()}, calm=None))
    assert not report.ok
    assert report.mismatches == (
        Mismatch(
            parameter="air_temperature",
            valid_time=_T0,
            reference=2.0,
            meteoscape=1.0,
            difference=1.0,
        ),
    )


def test_absolute_within_and_over_tolerance() -> None:
    spec = ParitySpec(rules={"wind_speed": Absolute(tol=1e-6)}, calm=None)
    ticks = ["2026-07-11T12:00:00Z", "2026-07-11T13:00:00Z"]
    payload = _payload(ticks, wind_speed=[1.0, 1.0])
    reference = _ref([_T0, _T1], wind_speed=[1.0 + 1e-7, 1.0 + 1e-5])
    report = compare(payload, reference, spec)
    assert len(report.mismatches) == 1
    assert report.mismatches[0].valid_time == _T1
    assert report.mismatches[0].difference == pytest.approx(1e-5)


def test_circular_wraparound_within_tol() -> None:
    payload = _payload(["2026-07-11T12:00:00Z"], wind_direction=[0.0000005])
    reference = _ref([_T0], wind_direction=[359.9999995])
    report = compare(
        payload,
        reference,
        ParitySpec(rules={"wind_direction": Circular(tol_deg=1e-6)}, calm=None),
    )
    assert report.ok


def test_nodata_mismatch_each_direction_and_both_pass() -> None:
    spec = ParitySpec(rules={"precipitation": Exact()}, calm=None)
    ticks = ["2026-07-11T12:00:00Z", "2026-07-11T13:00:00Z"]
    # tick0: ref None, payload 1.0 — mismatch; tick1: both None — pass
    payload = _payload(ticks, precipitation=[1.0, None])
    reference = _ref([_T0, _T1], precipitation=[None, None])
    report = compare(payload, reference, spec)
    assert report.mismatches == (
        Mismatch(
            parameter="precipitation",
            valid_time=_T0,
            reference=None,
            meteoscape=1.0,
            difference=None,
        ),
    )
    # opposite direction
    report2 = compare(
        _payload(["2026-07-11T12:00:00Z"], precipitation=[None]),
        _ref([_T0], precipitation=[1.0]),
        spec,
    )
    assert report2.mismatches[0].reference == 1.0
    assert report2.mismatches[0].meteoscape is None
    assert report2.mismatches[0].difference is None


def test_calm_carve_out_expects_null_and_counts_skip() -> None:
    spec = ParitySpec(
        rules={
            "wind_speed": Exact(),
            "wind_direction": Circular(tol_deg=1e-6),
        },
        calm=CalmRule("wind_speed", "wind_direction", floor=1e-9),
    )
    payload = _payload(
        ["2026-07-11T12:00:00Z"],
        wind_speed=[0.0],
        wind_direction=[None],
    )
    reference = _ref([_T0], wind_speed=[0.0], wind_direction=[180.0])
    report = compare(payload, reference, spec)
    assert report.ok
    assert report.skipped_calm == 1

    bad = compare(
        _payload(
            ["2026-07-11T12:00:00Z"],
            wind_speed=[0.0],
            wind_direction=[180.0],
        ),
        reference,
        spec,
    )
    assert not bad.ok
    assert bad.skipped_calm == 1
    assert bad.mismatches[0].parameter == "wind_direction"
    assert bad.mismatches[0].meteoscape == 180.0
    assert bad.mismatches[0].reference is None


def test_missing_payload_tick_fails_for_each_parameter() -> None:
    payload = _payload(["2026-07-11T12:00:00Z"], air_temperature=[1.0], cloud_cover=[2.0])
    # reference has only T1 — payload tick T0 is missing
    reference = _ref([_T1], air_temperature=[1.0], cloud_cover=[2.0])
    report = compare(
        payload,
        reference,
        ParitySpec(rules={"air_temperature": Exact(), "cloud_cover": Exact()}, calm=None),
    )
    assert not report.ok
    assert {m.parameter for m in report.mismatches} == {"air_temperature", "cloud_cover"}
    assert all(
        m.reference is None and m.meteoscape is None and m.difference is None
        for m in report.mismatches
    )


def test_missing_payload_parameter_block_raises() -> None:
    payload = _payload(["2026-07-11T12:00:00Z"])  # no air_temperature block
    reference = _ref([_T0], air_temperature=[1.0])
    with pytest.raises(ValueError, match="air_temperature"):
        compare(
            payload,
            reference,
            ParitySpec(rules={"air_temperature": Exact()}, calm=None),
        )


def test_write_evidence_bundle_and_secret_scrub(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import parity.comparison as comparison

    monkeypatch.setattr(comparison, "_ARTIFACTS_ROOT", tmp_path)
    path = write_evidence(
        "open-meteo",
        {
            "meteoscape_request": {"url": "https://x/?key=sekrit-token"},
            "meteoscape_payload": {"ok": True},
            "reference_request": {"url": "https://y/?key=sekrit-token"},
            "reference_response": '{"key":"sekrit-token"}',
            "diff": {"mismatches": []},
        },
        {"api_key": "sekrit-token"},
    )
    assert path.parent == tmp_path
    assert path.name.endswith("-open-meteo")
    for name in (
        "meteoscape_request.json",
        "meteoscape_payload.json",
        "reference_request.json",
        "reference_response.json",
        "diff.json",
    ):
        text = (path / name).read_text(encoding="utf-8")
        assert "sekrit-token" not in text
    assert "***" in (path / "meteoscape_request.json").read_text(encoding="utf-8")
    assert "***" in (path / "reference_response.json").read_text(encoding="utf-8")


def test_format_summary_fields_and_scrub() -> None:
    report = compare(
        _payload(["2026-07-11T12:00:00Z"], air_temperature=[1.0]),
        _ref([_T0], air_temperature=[2.0]),
        ParitySpec(rules={"air_temperature": Exact()}, calm=None),
    )
    text = format_summary(
        "open-meteo",
        "Berlin key=sekrit-token",
        report,
        Path("tests/parity/_artifacts/stamp-open-meteo"),
        secrets={"k": "sekrit-token"},
    )
    assert "open-meteo" in text
    assert "sekrit-token" not in text
    assert "***" in text
    assert "air_temperature" in text
    assert "2026-07-11T12:00:00" in text
    assert "stamp-open-meteo" in text
