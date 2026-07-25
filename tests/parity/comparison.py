"""Shared Provider parity comparison engine — MCP payload vs independent reference timeline.

Imports nothing from `meteoscape` so reference readers that depend on these types stay
import-guard clean.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_ARTIFACTS_ROOT = Path(__file__).resolve().parent / "_artifacts"
_SUMMARY_FIRST_N = 10
_REDACTION = "***"


@dataclass(frozen=True)
class Exact:
    """Lossless pass-through: any difference is a finding."""


@dataclass(frozen=True)
class Absolute:
    """|a - b| <= tol in the canonical unit."""

    tol: float


@dataclass(frozen=True)
class Circular:
    """Circular distance on degrees: min(|a-b| % 360, 360 - that) <= tol_deg."""

    tol_deg: float


Rule = Exact | Absolute | Circular


@dataclass(frozen=True)
class CalmRule:
    speed_parameter: str
    direction_parameter: str
    floor: float


@dataclass(frozen=True)
class ParitySpec:
    rules: Mapping[str, Rule]
    calm: CalmRule | None


@dataclass(frozen=True)
class ReferenceTimeline:
    valid_time: Sequence[datetime]
    values: Mapping[str, Sequence[float | None]]


@dataclass(frozen=True)
class Mismatch:
    parameter: str
    valid_time: datetime
    reference: float | None
    meteoscape: float | None
    difference: float | None  # None ⇔ nodata-position or calm-expectation mismatch
    # Calm violation: reference is None (expected null), not the vendor direction.


@dataclass(frozen=True)
class ParityReport:
    mismatches: Sequence[Mismatch]
    # compared: (tick x parameter) value-or-nodata judgments; excludes calm skips + missing ticks.
    compared: int
    skipped_calm: int

    @property
    def ok(self) -> bool:
        return not self.mismatches


def _circular_distance(a: float, b: float) -> float:
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


def _parse_payload_tick(raw: str) -> datetime:
    return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(UTC)


def _payload_series(payload: Mapping[str, Any], name: str) -> Sequence[Any]:
    block = payload.get(name)
    if block is None:
        raise ValueError(f"parity payload missing parameter block {name!r}")
    values = block["values"]
    return values


def _rule_difference(rule: Rule, reference: float, meteoscape: float) -> float | None:
    """Return difference if outside tolerance; None if within."""
    match rule:
        case Exact():
            if reference == meteoscape:
                return None
            return reference - meteoscape
        case Absolute(tol=tol):
            diff = reference - meteoscape
            if abs(diff) <= tol:
                return None
            return diff
        case Circular(tol_deg=tol_deg):
            dist = _circular_distance(reference, meteoscape)
            if dist <= tol_deg:
                return None
            return dist


def compare(
    payload: Mapping[str, Any],
    reference: ReferenceTimeline,
    spec: ParitySpec,
) -> ParityReport:
    payload_ticks = [_parse_payload_tick(t) for t in payload["valid_time"]]
    ref_index = {t: i for i, t in enumerate(reference.valid_time)}

    # Fail fast on missing blocks before emitting per-tick noise.
    series_by_param = {name: _payload_series(payload, name) for name in spec.rules}

    mismatches: list[Mismatch] = []
    compared = 0
    skipped_calm = 0
    calm = spec.calm

    for tick_i, tick in enumerate(payload_ticks):
        ref_i = ref_index.get(tick)
        if ref_i is None:
            for name in spec.rules:
                mismatches.append(
                    Mismatch(
                        parameter=name,
                        valid_time=tick,
                        reference=None,
                        meteoscape=None,
                        difference=None,
                    )
                )
            continue

        for name, rule in spec.rules.items():
            meteoscape_raw = series_by_param[name][tick_i]
            meteoscape = None if meteoscape_raw is None else float(meteoscape_raw)
            reference_vals = reference.values[name]
            ref_val = reference_vals[ref_i]

            if (
                calm is not None
                and name == calm.direction_parameter
                and (speed := reference.values[calm.speed_parameter][ref_i]) is not None
                and speed <= calm.floor
            ):
                skipped_calm += 1
                if meteoscape is not None:
                    mismatches.append(
                        Mismatch(
                            parameter=name,
                            valid_time=tick,
                            reference=None,
                            meteoscape=meteoscape,
                            difference=None,
                        )
                    )
                continue

            if ref_val is None and meteoscape is None:
                compared += 1
                continue
            if ref_val is None or meteoscape is None:
                compared += 1
                mismatches.append(
                    Mismatch(
                        parameter=name,
                        valid_time=tick,
                        reference=ref_val,
                        meteoscape=meteoscape,
                        difference=None,
                    )
                )
                continue

            compared += 1
            diff = _rule_difference(rule, ref_val, meteoscape)
            if diff is not None:
                mismatches.append(
                    Mismatch(
                        parameter=name,
                        valid_time=tick,
                        reference=ref_val,
                        meteoscape=meteoscape,
                        difference=diff,
                    )
                )

    return ParityReport(
        mismatches=tuple(mismatches),
        compared=compared,
        skipped_calm=skipped_calm,
    )


def scrub_secrets(text: str, secrets: Mapping[str, str]) -> str:
    for value in secrets.values():
        if value:
            text = text.replace(value, _REDACTION)
    return text


def _serialize_artifact(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, default=_json_default, indent=2, sort_keys=True)


def _json_default(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    if isinstance(obj, Path):
        return str(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def write_evidence(
    provider_id: str,
    artifacts: Mapping[str, Any],
    secrets: Mapping[str, str],
) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    dest = _ARTIFACTS_ROOT / f"{stamp}-{provider_id}"
    dest.mkdir(parents=True, exist_ok=True)
    names = (
        "meteoscape_request",
        "meteoscape_payload",
        "reference_request",
        "reference_response",
        "diff",
    )
    for name in names:
        body = scrub_secrets(_serialize_artifact(artifacts[name]), secrets)
        (dest / f"{name}.json").write_text(body, encoding="utf-8")
    return dest


def format_summary(
    provider_id: str,
    request_desc: str,
    report: ParityReport,
    evidence_path: Path | None,
    *,
    secrets: Mapping[str, str] | None = None,
) -> str:
    secrets = secrets or {}
    request_desc = scrub_secrets(request_desc, secrets)
    lines = [
        f"parity failure: provider={provider_id}",
        f"request: {request_desc}",
        f"compared={report.compared} skipped_calm={report.skipped_calm} "
        f"mismatches={len(report.mismatches)}",
    ]
    by_param: dict[str, list[Mismatch]] = {}
    for mismatch in report.mismatches:
        by_param.setdefault(mismatch.parameter, []).append(mismatch)
    for parameter, rows in sorted(by_param.items()):
        lines.append(f"{parameter}: {len(rows)} mismatch(es)")
        for mismatch in rows[:_SUMMARY_FIRST_N]:
            lines.append(
                f"  {mismatch.valid_time.strftime('%Y-%m-%dT%H:%M:%SZ')} "
                f"ref={mismatch.reference} meteoscape={mismatch.meteoscape} "
                f"diff={mismatch.difference}"
            )
    if evidence_path is not None:
        lines.append(f"evidence: {evidence_path}")
    return "\n".join(lines)
