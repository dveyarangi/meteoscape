# Edge — MCP surface

- **Status:** Normative

The seam record for the MCP protocol surface: one tool, `forecast_hourly`, served by the FastMCP
app over the woven best-view profile. Populated 2026-07-25 from the live surface
([m5](../tickets/done/01-0090-edge-records.md)); the tool's self-description in
[mcp_app.py](../../src/meteoscape/api/mcp_app.py) is a derivation of this record and must stay a
subset of it.

## Contract

**Request** — `forecast_hourly(latitude, longitude, parameters?, start?, end?)`:

- `latitude` ∈ [−90, 90], `longitude` ∈ [−180, 180]; out of range → `bad-request`.
- `start` / `end` are **reserved**: any value → `bad-request` until request shaping lands
  (Roadmap 1). The served window is the edge-authored default: **168 hourly ticks anchored at
  `floor(now, 1h)` UTC** (a 7-day Horizon).
- `parameters` — optional list of product parameter names; default is the full served menu.
  The menu is *exposure ∩ woven capability*; today: `air_temperature`, `precipitation`,
  `relative_humidity`, `cloud_cover`, `wind_speed`, `wind_direction`. The wind components
  `wind_u` / `wind_v` are Calculator inputs, never requestable. Unknown, non-requestable, or
  profile-unserved names → `bad-request` (whole request, before resolution).
- Vertical vantage is edge-authored near-surface (0–10 m aperture); the caller does not choose.

**Response** — one JSON object:

- `valid_time`: shared hourly lattice, ISO-8601 UTC `Z` strings; every parameter block's
  `values` aligns to it positionally.
- Per served parameter: `{unit, values, provenance: {source, exp}}` — `unit` is the canonical
  unit from [parameters.md](../parameters.md); `values` are floats or `null`; `provenance.source`
  names the winning producer, `exp` its freshness expiration.
- **Absent parameter block = unserved over this request** (no reason attached today —
  Concern #36, Roadmap 6). **`null` in `values` = served, nodata at that tick.** Callers must
  build on this distinction.

**Outcomes** — errors are `ToolError` texts with three stable category prefixes, per the
[error taxonomy](../architecture.md#failure-nodata-and-availability): `bad-request:` (caller
must change the input), `capability-mismatch:` (well-formed but unservable — raised only when
*nothing* is admitted), `runtime-failure:` (an upstream producer fault; fails the whole
request).

## Invariants

- Vendor nulls and nodata reach the wire as JSON `null` — never `NaN`, never fabricated values —
  *validated by:* [test_mcp_app.py](../../tests/deterministic/api/test_mcp_app.py)
  (`test_serialize_coverage_schema_and_nodata`),
  [test_open_meteo.py](../../tests/deterministic/nodes/providers/test_open_meteo.py)
  (`test_vendor_null_serializes_as_json_null`).
- Values are served in canonical units; vendor-native units are converted at the Provider edge
  (e.g. Open-Meteo `km/h → m/s` wind) — *validated by:*
  [test_e2e_forecast.py](../../tests/deterministic/test_e2e_forecast.py), live
  [parity check](../../tests/parity/test_open_meteo.py).
- `valid_time` is one regular hourly lattice in UTC; all parameter arrays align to it
  positionally — *validated by:* serializer tests in
  [test_mcp_app.py](../../tests/deterministic/api/test_mcp_app.py).
- `wind_direction` is `null` below the calm floor (direction is undefined in calm air,
  [parameters.md](../parameters.md)) — *validated by:*
  [test_wind_calculator.py](../../tests/deterministic/nodes/test_wind_calculator.py), parity
  calm-floor handling.
- A served-but-unadmitted parameter is omitted from the response; the request errors
  `capability-mismatch` only when nothing is admitted — *validated by:*
  [test_arbiter.py](../../tests/deterministic/nodes/test_arbiter.py)
  (`test_in_footprint_projects_once_with_admitted_params`,
  `test_beyond_footprint_raises_without_projecting`) — Arbiter-level; the wire-level assertion
  gap is noted in [009](../tickets/01-0190-error-taxonomy-partial-success.md).
- `runtime-failure` is whole-request: no partial response survives an upstream fault (fallback
  is Roadmap 4) — *validated by:* `test_tool_error_prefixes` in
  [test_mcp_app.py](../../tests/deterministic/api/test_mcp_app.py).
- Per-parameter provenance (`source`, `exp`) is always present on served parameters —
  *validated by:* serializer tests in
  [test_mcp_app.py](../../tests/deterministic/api/test_mcp_app.py).

## Concerns

- [#5 — Read-time homogenization fidelity](../concerns.md#5-read-time-homogenization-fidelity)
  — off-grid values are nearest-neighbor read-back today; fidelity at the requested point is
  bounded by this until 007 (Roadmap 3).
- [#10 — Parameter conventions](../concerns.md#10-parameter-conventions) — wire units are fixed
  per parameter; the lossless-vs-degrading conversion quality signal surfaces here when the
  catalogue grows (010).
- [#15 — Coarser-grid resampling](../concerns.md#15-coarser-grid-resampling-and-aggregation-semantics)
  — a future caller-facing resolution knob; today this edge always serves hourly.
- [#29 — Narrated reach](../concerns.md#29-narrated-reach-what-a-profile-promises) — what the
  profile promises ahead vs what a caller gets; the default window is edge-authored from the
  Horizon, and reach narration lands with 003c (Roadmap 1).
- [#30 — Response membership under degraded fallback](../concerns.md#30-response-membership-under-runtime-degraded-fallback)
  — membership semantics at this edge shift when fallback lands (Roadmap 4).
- [#36 — Unserved and uncomparable are indistinguishable](../concerns.md#36-unserved-and-uncomparable-are-indistinguishable)
  — the edge-local reading of silent omission: the caller cannot tell why a parameter is
  absent, and today neither can the engine (Roadmap 6).
- [#14 — Resolution trace](../concerns.md#14-resolution-trace-and-observability) — the
  roadmap-required resolution narration has no owning ticket; when it lands, it lands at this
  edge.

## Roadmap

1. Free `start`/`end` request windows — out-of-range asks yield the servable part, with reach
   narration — [003c](../tickets/01-0110-request-shaping.md)
   (on [m4](../tickets/done/01-0100-snapped-t-request-mode.md)).
2. Fresh reuse — repeat asks answered from retained data —
   [006](../tickets/01-0130-retentive-store-freshness.md).
3. Off-grid fidelity — homogenized values at the requested point, not nearest-neighbor —
   [007](../tickets/01-0140-off-grid-homogenization.md).
4. Provider fallback — upstream faults stop failing the whole request —
   [004](../tickets/01-0150-second-provider-fallback.md).
5. Per-parameter assembly — one response, different winning sources per parameter —
   [005](../tickets/01-0170-per-parameter-selection.md).
6. Absence reasons and partial success under fault —
   [009](../tickets/01-0190-error-taxonomy-partial-success.md).
