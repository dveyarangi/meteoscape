# v1 delivery status

**Last updated:** 2026-07-16

**Current stage:** ticket 002b done; next up is 003a (`Capability.reach`) or 006 (retentive store).

This is the source of truth for **what is implemented, what is in progress, what is ready, and what
comes next** in the v1 build. The [product roadmap](../product-roadmap.md) owns product direction,
[v1 requirements](../v1-requirements.md) own the release contract, the
[architecture](../architecture.md) and [ADRs](../adr) own design decisions, and individual tickets own
implementation detail and acceptance criteria.

Dated [sessions](../sessions) and [completed tickets](./done) are historical records. They explain how
the project reached its current state; they do not override this page.

## Status vocabulary

- **Done** — acceptance criteria are complete; the ticket lives under [`done/`](./done).
- **In progress** — implementation work is active; completion and verification remain pending.
- **Ready** — dependencies are complete and implementation can start.
- **Partial** — some behavior landed earlier; the remaining acceptance criteria are still open.
- **Planned** — accepted work whose dependencies are not yet complete.
- **Blocked** — work cannot proceed for a reason other than an ordinary incomplete dependency. No
  active v1 ticket is presently blocked in this sense.

Dependencies describe ordering; a completed dependency does not make a ticket "blocked."

## Available today

| Capability | Status | Current behavior |
|---|---|---|
| MCP `forecast_hourly` | Partial | Registered and callable with latitude/longitude; the default window is fixed and `start`/`end` are rejected. |
| Open-Meteo forecast | Available | Fetches and normalizes the six provider-served canonical parameters (`air_temperature`, `relative_humidity`, `precipitation`, `cloud_cover`, `wind_u`, `wind_v`). |
| Parameter selection | Partial | An optional subset is accepted within the woven capability ∩ edge exposure; requestable surface is the six product params (four direct + derived wind speed/direction). |
| Provenance and freshness metadata | Available | Atomic source/run provenance and `expiration` are authored; the compact MCP response exposes source and expiration. |
| Error surface | Partial | Stable `bad-request`, `capability-mismatch`, and `runtime-failure` prefixes exist; per-parameter partial-failure reasons remain. |
| Resolution logging/trace | Unassigned | The Phase 1 product roadmap calls for minimal resolution logging, but no v1 acceptance criterion or active ticket owns it yet. |
| Canonical v1 parameter set | Done | Six provider-served canonical parameters, native Z carriage, convert-on-ingest, and the edge exposure table (ticket 002); nodata rides the `present` mask and serializes as JSON `null` (ticket 002c). One contract slot stays **unbuilt**: the Z axis's `vertical_reference`, which v1 does not need because every declaration is `above_ground` (no owner; required before any second-frame parameter — see v1-requirements deferrals). |
| Derived wind | Done | Multi-output Calculator serves `wind_speed` / `wind_direction` from `wind_u` / `wind_v` with provider-origin propagation (ticket 002b). The node validates output **keys** but not range/domain **alignment**; the v1 kernel is pointwise and cannot violate it, so enforcement is deferred to whichever ticket first opens the hole — a windowing kernel or Store read-back (concern #31). |
| Free request windows | Planned | Existing parameter input and validation are partial ticket 003b delivery; real `start`/`end` shaping remains, on top of 003a's `Capability.reach`. Alias / exact-Z addressing is **not** v1 — a recorded contract seam awaiting its product driver (roadmap Phase 4). |
| Second provider and fallback | Planned | TWC/provider fallback behavior is ticket 004; the current provider catalogue contains only Open-Meteo. |
| Per-parameter multi-source assembly | Planned | Top Arbiter already assembles disjoint single-parameter winners (002b); multi-provider capability routing is ticket 005. |
| Retentive cache/freshness | Planned | Stores are non-retentive placeholders; retention and refill semantics are ticket 006. The Provider currently flattens native records onto the request domain at fetch (`_assemble`) — correct under a fully-enumerable ask, but it destroys native Z, so 006 changes the *ask* to carry `ANY` axes. |
| Off-grid homogenization | Planned | The v1 nearest-neighbor read-back path is ticket 007. |
| Configured TWC startup | Partial | Typed settings and the key-absent Open-Meteo path exist; key-present TWC composition waits on tickets 004 and 008. |

## Delivery map

| Ticket | Status | Depends on | Outcome |
|---|---|---|---|
| [000 — Project bootstrap](./done/000-project-bootstrap.md) | Done | — | Package, contracts, and initial module seams. |
| [001 — Walking skeleton](./done/001-walking-skeleton.md) | Done | 000 | One real Open-Meteo temperature request through MCP. |
| [002 — Core canonical parameters](./done/002-core-5-parameters.md) | Done | 001 (done) | Six provider-served canonical parameters, native Z carriage (single `above_ground` frame; no `vertical_reference` slot), and the edge exposure table. |
| [002b — Derived wind](./done/002b-derived-wind-calculator.md) | Done | 002 (done) | Requestable wind speed/direction (multi-output Calculator) with propagated provider provenance; first multi-node Coverage assembly. Node well-formedness validation is **partial** — output keys are checked, range/domain alignment is not (unenforced by design while every kernel is pointwise → concern #31). |
| [002c — Provider nodata mask](./002c-provider-nodata-mask.md) | Done | 002 (done) | Vendor null → `present[i] = False` → JSON `null`, replacing the NaN substitution that violated the Coverage contract. Presence moved behind `ParameterData` behaviour (`of` / `is_present` / `take`); the `pointwise` decode combinator owns the presence rule. Alignment validation deliberately **not** included → concern #31. |
| [003a — `Capability.reach`](./003a-capability-reach.md) | Ready | 002, 002b | Per-parameter reach `Domain` with per-axis composite folds; per-axis `Interval` union/intersection. |
| [003b — Request shaping](./003b-request-shaping.md) | Partial | 003a | Free `start`/`end` windows, plus reach-based narration and default windows at the edge. |
| [004 — Second provider fallback](./004-second-provider-fallback.md) | Planned | 002, 003b | TWC leaf and wholesale priority fallback. |
| [005 — Per-parameter selection](./005-per-parameter-selection.md) | Planned | 004 | One response assembled from different winning providers by parameter. |
| [006 — Retentive store](./006-retentive-store-freshness.md) | Planned | 002 | Fresh reuse, partial refill, and single-origin whole-window replacement; `quantize` with `ANY` axes so native geometry survives one fetch, retiring the eager provider-side flatten. |
| [007 — Off-grid homogenization](./007-off-grid-homogenization.md) | Planned | 006 | Nearest-neighbor read-back onto the requested point. |
| [008 — Config and graceful degrade](./008-config-secrets-degrade.md) | Partial | 004 | Complete key-present/key-absent provider construction behavior. |
| [009 — Errors and partial success](./009-error-taxonomy-partial-success.md) | Partial | 002c, 003b, 004 | Per-parameter absence reasons and capable-but-faulting partial results. |
| [010 — Unit conversion catalogue](./010-unit-conversion-edge.md) | Planned | 002; triggered by 004 | Shared verified native-to-canonical conversion edges. |

## Recommended execution order

1. ~~**002c**~~ — **landed**: the live contract violation (vendor nulls reaching the wire as `NaN`) is
   closed, and 009's nodata semantics are unblocked.
2. Run **003a** (self-contained algebra work, no surface change), or **006** as an independent
   follow-on.
3. Complete **003b** on top of 003a.
4. Complete **007** after 006.
5. Build **004**, introducing **010** when the second provider creates the real unit-spread case.
6. Close the v1 multi-provider surface with **005**, **008**, and **009**.

This ordering clears the known contract violation, then prioritizes real retention and request
shaping, then provider fallback and per-parameter resolution.

## Decisions still owned by tickets

- Delivery planning: either assign Phase 1 resolution logging to a v1 ticket/acceptance criterion or
  move it to the operational-substrate phase.
- [005](./005-per-parameter-selection.md): choose the single-provider parameter used to demonstrate
  capability-based routing.
- [006](./006-retentive-store-freshness.md): settle the private store-lattice representation.
- [010](./010-unit-conversion-edge.md): build the shared conversion catalogue when ticket 004 exposes
  the first real multi-vendor spread.

## Maintenance rule

Update this page and the affected ticket header when delivery state changes. Other documentation may
say that a feature is **required by v1**, **deferred from v1**, or part of an accepted design, but should
link here instead of restating whether that feature is implemented or next.
