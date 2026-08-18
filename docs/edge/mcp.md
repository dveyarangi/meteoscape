# Edge — MCP surface

- **Status:** Normative

The seam record for the MCP protocol surface: one tool, `forecast_hourly`, served by the FastMCP
app over the woven best-view profile. The tool's self-description in
[mcp_app.py](../../src/meteoscape/api/mcp_app.py) is a derivation of this record and must stay a
subset of it.

## Contract

**Request** — `forecast_hourly(latitude, longitude, parameters?, start?, end?)`:

- `latitude` ∈ [−90, 90], `longitude` ∈ [−180, 180]; out of range → `bad-request`.
- `start` / `end` — optional free window bounds, **ISO 8601 datetimes only**: offset-aware
  normalizes to UTC, naive reads as UTC; a bare date (or week date) → `bad-request` with the
  datetime fix in the message; unparsable → `bad-request`. The window is served as
  **`bounds ∩ the winner's live window`** on the winner's own lattice
  ([ADR-0002](../adr/0002-data-model.md)): the tick containing `start` is
  served, `end` is inclusive of its containing tick, and `start == end` yields exactly one tick.
  Omitted `start` begins at the tick containing now; omitted `end` runs to the profile's live
  reach end. A backwards window (raw instants, implicit `start = now`) → `bad-request`; a
  well-formed window with no overlap with the served range → `capability-mismatch` — admission's
  answer, never the edge's, which holds no reach authority. A window that *does* overlap the
  declared range but which the Holdings cannot meet — a rolling leaf asked below its first delivered
  tick — is admitted and reaches the same outcome from the serving seam instead
  ([ADR-0002: retention predicate](../adr/0002-data-model.md#the-two-predicates-admission-and-retention)).
  Out-of-range bounds yield the **servable part**; the response's `valid_time` shows the window
  actually served.
- `parameters` — optional list of product parameter names; default is the full served menu.
  The menu is *exposure ∩ woven capability*; today: `air_temperature`, `precipitation`,
  `relative_humidity`, `cloud_cover`, `wind_speed`, `wind_direction`. The wind components
  `wind_u` / `wind_v` are Calculator inputs, never requestable. Unknown, non-requestable, or
  profile-unserved names → `bad-request` (whole request, before resolution); an **explicitly
  empty list** → `bad-request` (`None` keeps meaning "all served"); an empty *served* menu →
  `capability-mismatch`.
- Vertical vantage is edge-authored near-surface (0–10 m aperture); the caller does not choose.

**Response** — one JSON object:

- `valid_time`: shared hourly lattice, ISO-8601 UTC `Z` strings; every parameter block's
  `values` aligns to it positionally.
- Per served parameter: `{unit, values, provenance: {source, exp}}` — `unit` is the canonical
  unit from [parameters.md](../parameters.md); `values` are floats or `null`; `provenance.source`
  names the winning producer, `exp` its freshness expiration.
- **Absent parameter block = unserved over this request** (no reason attached today —
  Concern #36, Roadmap 3). **`null` in `values` = served, nodata at that tick.** Callers must
  build on this distinction.

**Outcomes** — errors are `ToolError` texts with three stable category prefixes, per the
[error taxonomy](../architecture.md#failure-nodata-and-availability): `bad-request:` (caller
must change the input), `capability-mismatch:` (well-formed but unservable — raised only when
*nothing* is admitted), `runtime-failure:` (an upstream producer fault after every admitted
candidate has been tried; fails the whole request).

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
  gap is noted in the
  [error-taxonomy ticket](../tickets/01-0190-error-taxonomy-partial-success.md).
- A child's `runtime-failure` falls through to the next admitted candidate; the request fails
  whole only when every candidate has faulted or none of the rest admit (**compatible** — a
  request that used to fail may now succeed). No partial response survives exhaustion —
  *validated by:* `test_faulting_priority_0_falls_through_to_priority_1`,
  `test_all_candidates_fault_names_parameter_producers_and_last_fault`,
  `test_no_remaining_candidate_admits_is_exhaustion_not_omission` in
  [test_arbiter.py](../../tests/deterministic/nodes/test_arbiter.py), and
  `test_primary_429_falls_through_to_backstop` in
  [test_e2e_forecast.py](../../tests/deterministic/test_e2e_forecast.py).
- Per-parameter provenance (`source`, `exp`) is always present on served parameters —
  *validated by:* serializer tests in
  [test_mcp_app.py](../../tests/deterministic/api/test_mcp_app.py).
- The tool description narrates the served menu and the profile's reach as a **relative horizon**
  ("out to N ahead of the latest model run"), never absolute instants: the description is built
  once and frozen for the process lifetime, and a `RollingAxis` extent length is clock-invariant.
  Durations of at least one day are floored to whole days; shorter durations remain whole hours, so a
  run-anchored reach stays exact and Open-Meteo's current shelf-anchored declaration stays conservative
  against its independently moving run clock — *validated by:*
  [test_mcp_app.py](../../tests/deterministic/api/test_mcp_app.py)
  (`test_forecast_hourly_builds_selection_and_narrates`,
  `test_horizon_floors_non_exact_days_to_whole_days`,
  `test_horizon_narrates_sub_day_reach_in_hours`, the empty-menu skip) and the e2e
  default-window case ([test_e2e_forecast.py](../../tests/deterministic/test_e2e_forecast.py)).
- **The narrated horizon is an upper bound on the default ask's answer, not its span**:
  the horizon derives from the composed reach, while a spanning ask is answered by the **priority
  winner's own clipped horizon**, disclosed through `valid_time`
  ([ADR-0004](../adr/0004-producer-resolution-and-capability.md),
  [#29](../concerns.md#29-narrated-reach-what-a-profile-promises)). An ask **wholly past the
  primary's reach** does not fall through to the longer backstop — the retention flow refills from
  the primary and answers `capability-mismatch` — the unbuilt max-reach policy →
  [#49](../concerns.md#49-spanning-asks-serve-the-primary-max-reach-is-unbuilt-policy).
  *validated by:* `test_default_ask_with_twc_primary_answers_twc_horizon` (15-day narration, the
  answer's `valid_time` stopping at the primary's 240 ticks, backstop never called) and
  `test_ask_wholly_past_twc_is_capability_mismatch` (the error asserted, plus the redundant
  primary refill) in
  [test_e2e_forecast.py](../../tests/deterministic/test_e2e_forecast.py).
- A zero-overlap window is answered at admission — `capability-mismatch` with **no vendor
  call** — and out-of-range bounds reach the vendor as exactly the clipped lattice —
  *validated by:* [test_e2e_forecast.py](../../tests/deterministic/test_e2e_forecast.py)
  (`test_history_window_is_capability_mismatch_with_no_vendor_call`,
  `test_out_of_range_bounds_fetch_exactly_the_clipped_window`).
- A window overlapping the declaration but not the Holdings reaches the same
  `capability-mismatch` from the serving seam, with **no vendor call once warm** — a cold store
  still pays one first-touch fetch, which is retained and answers later asks — *validated by:*
  [test_reservoir.py](../../tests/deterministic/nodes/test_reservoir.py)
  (`test_wholly_in_gap_ask_is_capability_mismatch_without_refetch_when_warm`).
- A vendor delivering fewer ticks than declared is an honest shorter answer, disclosed through
  `valid_time` — never a fault ([edge/provider.md](./provider.md)) — *validated by:*
  [test_e2e_forecast.py](../../tests/deterministic/test_e2e_forecast.py)
  (`test_short_vendor_delivery_is_disclosed_not_failed`).
- **A repeat of the same request inside the freshness window returns the same values without an
  upstream trip, and never returns stale ones**: retention serves from the Store while
  `provenance.exp` is in the future and refetches once it passes, so `exp` is the caller's
  usable staleness bound rather than a hint. Callers may cache to it and poll no faster —
  *validated by:* [test_e2e_forecast.py](../../tests/deterministic/test_e2e_forecast.py)
  (`test_forecast_hourly_e2e_and_refetch`, `test_expired_holdings_refetch_and_never_serve_stale`).
- **An off-grid point is served from the enclosing store cell**, so the store step is the fidelity
  floor: two distinct requested points inside one cell receive identical values — *validated by:*
  [test_e2e_forecast.py](../../tests/deterministic/test_e2e_forecast.py)
  (`test_points_within_one_store_cell_share_one_vendor_call`).

## Concerns

- [#5 — Read-time homogenization fidelity](../concerns.md#5-read-time-homogenization-fidelity)
  — an off-grid value is reported at the requested point today, read back from the **enclosing**
  store cell with the **identity** Resampler (no interpolation). Fidelity at the requested point is
  bounded by the store step; the floor itself is an invariant above. Values change at this edge only
  when a Parameter-specific Resampler lands.
- [#48 — A tap cannot declare where its value sits relative to the tick](../concerns.md#48-a-tap-cannot-declare-where-its-value-sits-relative-to-the-tick)
  — Open-Meteo precipitation is currently labelled one hour late on this surface; values and units
  are unaffected.
- [#10 — Parameter conventions](../concerns.md#10-parameter-conventions) — wire units are fixed
  per parameter; the lossless-vs-degrading conversion quality signal surfaces here when the
  [unit-conversion catalogue](../tickets/01-0122-unit-conversion-edge.md) grows.
- [#15 — Coarser-grid resampling](../concerns.md#15-coarser-grid-resampling-and-aggregation-semantics)
  — a future caller-facing resolution knob; today this edge always serves hourly.
- [#29 — Narrated reach](../concerns.md#29-narrated-reach-what-a-profile-promises) — the
  narrated horizon is one number for the whole globe (a `min` fold over the served menu); the
  per-location truth is the deferred capabilities-introspection tool.
- [#30 — Response membership under degraded fallback](../concerns.md#30-response-membership-under-runtime-degraded-fallback)
  — fall-through is delivered; membership on exhaustion (omit vs fail-whole) stays here (Roadmap 3).
- [#36 — Unserved and uncomparable are indistinguishable](../concerns.md#36-unserved-and-uncomparable-are-indistinguishable)
  — the edge-local reading of silent omission: the caller cannot tell why a parameter is
  absent, and today neither can the engine (Roadmap 3).
- [#14 — Resolution trace](../concerns.md#14-resolution-trace-and-observability) — Phase 1's
  contract-neutral structured logs are assigned to [minimal resolution
  logging](../tickets/01-0195-minimal-resolution-logging.md); the richer trace sidecar remains
  deferred and would become a separate edge concern before changing this surface.

## Roadmap

1. **Delivered (compatible)** — a child's `runtime-failure` falls through to the next admitted
   candidate; the request fails whole only on exhaustion —
   [second-provider fallback](../tickets/done/01-0121-second-provider-fallback.md).
2. Per-parameter assembly — one response, different winning sources per parameter —
   [per-parameter selection](../tickets/01-0170-per-parameter-selection.md).
3. Absence reasons and partial success under fault —
   [error taxonomy and partial success](../tickets/01-0190-error-taxonomy-partial-success.md).
4. **Echo the answered coordinate.** `serialize_coverage` reads `coverage.domain` but emits only the
   T axis, so this surface drops the X/Y the answer is labelled at. The Coverage already carries them
   — this is a serialization gap of this surface alone, and it does not exist at the
   [embedding surface](./embedding.md), which hands the host the
   Coverage itself. The fix is **additive and compatible** (an echoed point beside `valid_time`);
   unticketed, and worth doing only when a caller needs to distinguish the point they asked for from
   the values they got. Distinct from *which* cell sourced the value — that is
   [#14](../concerns.md#14-resolution-trace-and-observability)'s, and explicitly **not** provenance
   ([ADR-0003](../adr/0003-provenance-and-origin.md): native fidelity is not a provenance field).
