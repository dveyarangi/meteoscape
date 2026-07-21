# v1 delivery status

**Last updated:** 2026-07-21

**Current stage:** 003a and m1 have landed. Next is 003b, which moves reach onto `Capability`
([ADR-0007](../adr/0007-capability-carries-its-domain.md)) and reshapes 003a's resolver, then 003c
(request shaping); 006 (retentive store) is an independent follow-on.

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
| Open-Meteo forecast | Available | Fetches all six provider-served canonical parameters. |
| Parameter selection | Partial | Accepts optional subsets of the six exposed product parameters. |
| Provenance and freshness metadata | Available | Returned parameters include source and expiration metadata. |
| Error surface | Partial | Stable error categories exist; per-parameter partial-failure reasons remain. |
| Resolution logging/trace | Unassigned | Required by the product roadmap but not owned by active work. |
| Canonical v1 parameter set | Done | Six provider-served parameters and two derived wind views; nodata serializes as JSON `null`. |
| Derived wind | Done | `wind_speed` and `wind_direction` are derived from `wind_u` and `wind_v`. |
| Free request windows | Planned | Parameter subsets work; `start`/`end` shaping and reach-based defaults remain. |
| Second provider and fallback | Planned | Only Open-Meteo is configured. |
| Per-parameter multi-source assembly | Planned | Single-provider multi-node assembly works; multi-provider routing remains. |
| Retentive cache/freshness | Planned | Stores are non-retentive placeholders. |
| Off-grid homogenization | Planned | Nearest-neighbor read-back remains. |
| Configured TWC startup | Partial | Typed settings and key-absent startup work; key-present composition remains. |

## Delivery map

| Ticket | Status | Depends on | Outcome |
|---|---|---|---|
| [000 — Project bootstrap](./done/000-project-bootstrap.md) | Done | — | Package, contracts, and initial module seams. |
| [001 — Walking skeleton](./done/001-walking-skeleton.md) | Done | 000 | One real Open-Meteo temperature request through MCP. |
| [002 — Core canonical parameters](./done/002-core-5-parameters.md) | Done | 001 (done) | Canonical provider parameters and edge exposure. |
| [002b — Derived wind](./done/002b-derived-wind-calculator.md) | Done | 002 (done) | Requestable derived wind and multi-node response assembly. |
| [002c — Provider nodata mask](./done/002c-provider-nodata-mask.md) | Done | 002 (done) | Vendor nulls preserved as nodata and JSON `null`. |
| [003a — Profile reach](./done/003a-profile-reach.md) | Done | 002, 002b | Build-time profile reach. Resolver only; 003b relocates it onto `Capability`. |
| [003b — Capability carries its domain](./003b-capability-domain.md) | Ready | 003a (landed), m1 | `Capability.reach(parameter)`; reach becomes the root capability's domain; the standalone resolver goes. |
| [003c — Request shaping](./003c-request-shaping.md) | Partial | 003a, 003b | Free `start`/`end` windows, plus reach-based narration and default windows at the edge. Formerly numbered 003b. |
| [004 — Second provider fallback](./004-second-provider-fallback.md) | Planned | 002, 003c | TWC leaf and wholesale priority fallback. |
| [005 — Per-parameter selection](./005-per-parameter-selection.md) | Planned | 004 | One response assembled from different winning providers by parameter. |
| [006 — Retentive store](./006-retentive-store-freshness.md) | Planned | 002 | Fresh reuse, partial refill, and replacement semantics. |
| [007 — Off-grid homogenization](./007-off-grid-homogenization.md) | Planned | 006 | Nearest-neighbor read-back onto the requested point. |
| [008 — Config and graceful degrade](./008-config-secrets-degrade.md) | Partial | 004 | Complete key-present/key-absent provider construction behavior. |
| [009 — Errors and partial success](./009-error-taxonomy-partial-success.md) | Partial | 002c, 003c, 004 | Per-parameter absence reasons and capable-but-faulting partial results. |
| [010 — Unit conversion catalogue](./010-unit-conversion-edge.md) | Planned | 002; triggered by 004 | Shared verified native-to-canonical conversion edges. |

## Maintenance

Work that keeps the build honest but delivers no product capability, so it carries no number in the
delivery sequence above and appears in no capability table.

| Ticket | Status | Depends on | Outcome |
|---|---|---|---|
| [m1 — Type contract hygiene](./done/m1-type-contract-hygiene.md) | Done | 003a (landed) | `pyright` clean across `src` and `tests`; no design contract weakened to get there. |
| [m2 — Dissolve node-`Countable`](./m2-dissolve-node-countable.md) | Planned | 003b | `Countable` becomes a result-only facet per ADR-0006; the `Store` lattice stays private; materialized providers wire storeless. Soft-blocks 006. |

## Recommended execution order

1. ~~**002c**~~ — **landed**: the live contract violation (vendor nulls reaching the wire as `NaN`) is
   closed, and 009's nodata semantics are unblocked.
2. ~~**003a**~~ — **landed**: build-time profile reach, no surface or request-path change.
3. ~~**m1**~~ — **landed**: `pyright` green across `src` and `tests`, CI unblocked.
4. Run **003b** — moves reach onto `Capability` per [ADR-0007](../adr/0007-capability-carries-its-domain.md), before 003c writes a consumer against the old shape.
5. Complete **003c** on top of 003b, or **006** as an independent follow-on — running **m2** first,
   since 006 assumes the storeless/private-lattice shape m2 delivers.
6. Complete **007** after 006.
7. Build **004**, introducing **010** when the second provider creates the real unit-spread case.
8. Close the v1 multi-provider surface with **005**, **008**, and **009**.

This ordering clears the known contract violation, then prioritizes real retention and request
shaping, then provider fallback and per-parameter resolution.

## Decisions still owned by tickets

- Delivery planning: either assign Phase 1 resolution logging to a v1 ticket/acceptance criterion or
  move it to the operational-substrate phase.
- [003b](./003b-capability-domain.md): none — all five placement questions were resolved in the 0016
  align session (recorded inline in the ticket); implementation can start.
- [m2](./m2-dissolve-node-countable.md): where a storeless materialized producer's read-back
  homogenization lives, and whether `EnumerableCapability` remains the "already materialized"
  discriminator → [#37](../concerns.md#37-storeless-materialized-producers-and-read-back-homogenization).
- [005](./005-per-parameter-selection.md): choose the single-provider parameter used to demonstrate
  capability-based routing.
- [006](./006-retentive-store-freshness.md): settle the private store-lattice representation.
- [010](./010-unit-conversion-edge.md): build the shared conversion catalogue when ticket 004 exposes
  the first real multi-vendor spread.

## Maintenance rule

Update this page and the affected ticket header when delivery state changes. Other documentation may
say that a feature is **required by v1**, **deferred from v1**, or part of an accepted design, but should
link here instead of restating whether that feature is implemented or next.
