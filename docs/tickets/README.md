# v1 delivery status

**Last updated:** 2026-08-04

**Current stage:** 003a, m1, 003b, m2, m3, m5, and m4 have landed — reach lives on `Capability`
([ADR-0007](../adr/0007-capability-carries-its-domain.md)), `Countable` is a result-only facet, a
materialized provider wires storeless
([ADR-0006](../adr/0006-materialization-granularity-and-store-shape.md)), the live parity harness
runs under `tests/parity/` beside the deterministic suite under `tests/deterministic/`
([RFC 0007](../rfc/done/0007-20260725-m3-provider-parity-checks.md) — the Open-Meteo reference check
passed its acceptance run on 2026-07-25, so 011's second Provider is no longer gated on it), and
per-surface [Edge records](../edge) carry each product edge's contract, invariants, and staged
roadmap.

**[m4 — Snapped request mode](./done/01-0100-snapped-t-request-mode.md) landed 2026-08-04**: the
Snapped-T mode resolves through one verb (`ground`) over one abstract axis operation (`clip`), and the
leaf split into a `TimelineProvider` shape owning all algebra and an injected `TimelineProbe` owning
the vendor face, with the Probe seam guarded by an import-direction test
([edge/provider.md](../edge/provider.md), now Normative with no pending markers). The mode is
product-invisible until 003c consumes it. **003c (request shaping) is now Ready**; 006 (retentive
store) is an independent follow-on with its assumed storeless/private-lattice shape already in place.

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
| Derived wind | Done | `wind_speed` and `wind_direction` are derived from `wind_u` and `wind_v`; direction is nodata below the calm floor ([parameters](../parameters.md)). |
| Free request windows | Planned | Parameter subsets work; `start`/`end` shaping and reach-based defaults remain. |
| Second provider and fallback | Planned | Only Open-Meteo is configured. |
| Per-parameter multi-source assembly | Planned | Single-provider multi-node assembly works; multi-provider routing remains. |
| Retentive cache/freshness | Planned | Stores are non-retentive placeholders. |
| Off-grid homogenization | Planned | Nearest-neighbor read-back remains. |
| Configured keyed-provider startup | Partial | Typed settings and key-absent startup work; key-present composition remains. Second provider is **Visual Crossing** (chosen 2026-08-02, replacing TWC). |

## Delivery map

One queue, in the order the work is done. The **#** column is the ticket's position — see
[Ticket numbering](#ticket-numbering). Maintenance work keeps the build honest but delivers no
product capability, so it is marked `Maint` and appears in no capability table; it still holds a
queue position, because it still has to be done in order.

| # | Ticket | Kind | Status | Depends on | Outcome |
|---|---|---|---|---|---|
| 0010 | [Project bootstrap](./done/01-0010-project-bootstrap.md) | — | Done | — | Package, contracts, and initial module seams. |
| 0020 | [Walking skeleton](./done/01-0020-walking-skeleton.md) | — | Done | project bootstrap | One real Open-Meteo temperature request through MCP. |
| 0030 | [Core canonical parameters](./done/01-0030-core-5-parameters.md) | — | Done | walking skeleton | Canonical provider parameters and edge exposure. |
| 0030.0010 | [Derived wind](./done/01-0030.0010-derived-wind-calculator.md) | — | Done | core canonical parameters | Requestable derived wind and multi-node response assembly. |
| 0030.0020 | [Provider nodata mask](./done/01-0030.0020-provider-nodata-mask.md) | — | Done | core canonical parameters | Vendor nulls preserved as nodata and JSON `null`. |
| 0040 | [Profile reach](./done/01-0040-profile-reach.md) | — | Done | core canonical parameters, derived wind | Build-time profile reach. Resolver only; capability domain relocates it onto `Capability`. |
| 0050 | [Type contract hygiene](./done/01-0050-type-contract-hygiene.md) | Maint | Done | profile reach | `pyright` clean across `src` and `tests`; no design contract weakened to get there. |
| 0060 | [Capability carries its domain](./done/01-0060-capability-domain.md) | — | Done | profile reach, type contract hygiene | `Capability.reach(parameter)`; reach is the root capability's domain; the standalone resolver is gone. |
| 0070 | [Dissolve node-`Countable`](./done/01-0070-dissolve-node-countable.md) | Maint | Done | capability domain | `Countable` is a result-only facet per ADR-0006; the `Store` lattice stays private; materialized providers wire storeless. Retentive store's assumed shape is in place. |
| 0080 | [Provider parity checks](./done/01-0080-provider-parity-checks.md) | Maint | Done | core canonical parameters, derived wind | Opt-in live single-Provider parity harness (`uv run pytest tests/parity`) and the Open-Meteo reference check; wind calm floor. Every new Provider ships its own check. |
| 0090 | [Edge records and the `/edge` skill](./done/01-0090-edge-records.md) | Maint | Done | — | Per-surface Edge records (the architecture ↔ user-design seam documents) with an `/edge` skill; edge awareness wired into `/align` (challenge rule, `EDGE-FORMAT.md`) and `/sync-arch`; the MCP record populated and Normative. |
| 0100 | [Snapped request mode (T instantiation)](./done/01-0100-snapped-t-request-mode.md) | Maint | Done | capability domain, provider parity checks | The reserved Snapped mode as one bounds-only axis member, enabled on T: intersective admission, resolution serves `bounds ∩ live window` on the winner's own lattice. Landed with the `TimelineProvider` / `TimelineProbe` split. |
| 0110 | [Request shaping](./01-0110-request-shaping.md) | — | Ready | snapped request mode, profile reach, capability domain | Free `start`/`end` windows (datetimes only) riding the Snapped-T mode, plus reach narration; an omitted `end` defaults to the profile's live reach end. |
| 0120 | [Visual Crossing provider](./01-0120-visual-crossing-provider.md) | — | Ready | snapped request mode, provider parity checks | Visual Crossing `TimelineProbe` (same shape as the primary, so no wrapper), first shipped `SecretSlot`, its parity check, and the TWC sweep out of `config.py` / `test_config.py`. Split from second-provider fallback on 2026-08-02. |
| 0130 | [Retentive store](./01-0130-retentive-store-freshness.md) | — | Planned | core canonical parameters | Fresh reuse, partial refill, and replacement semantics. |
| 0140 | [Off-grid homogenization](./01-0140-off-grid-homogenization.md) | — | Planned | retentive store | Nearest-neighbor read-back onto the requested point. |
| 0150 | [Second-provider fallback](./01-0150-second-provider-fallback.md) | — | Planned | core canonical parameters, request shaping, Visual Crossing provider | Wholesale priority fallback across two producers — Arbiter behaviour only, mocked transports, no live network. |
| 0160 | [Unit-conversion catalogue](./01-0160-unit-conversion-edge.md) | — | Planned | core canonical parameters; triggered by Visual Crossing provider | Shared verified native-to-canonical conversion edges. |
| 0170 | [Per-parameter selection](./01-0170-per-parameter-selection.md) | — | Planned | second-provider fallback | One response assembled from different winning providers by parameter. |
| 0180 | [Config and graceful degrade](./01-0180-config-secrets-degrade.md) | — | Partial | Visual Crossing provider | Complete key-present/key-absent provider construction behavior. |
| 0190 | [Errors and partial success](./01-0190-error-taxonomy-partial-success.md) | — | Partial | provider nodata mask, request shaping, second-provider fallback | Per-parameter absence reasons and capable-but-faulting partial results. |
| 0200 | [Artifact conventions sweep](./01-0200-artifact-conventions-sweep.md) | Maint | Planned (own align precedes) | edge records | Canonical artifact-conventions registry: full doc roster classified (normative vs descriptive, granularity, lifecycle), skills slimmed to reference it. |

## Ticket numbering

A ticket's filename is `RR-NNNN-slug.md` — release, position, name:

```
docs/tickets/01-0130-retentive-store-freshness.md
              │  │    └── slug — what the ticket is. Never changes. Cite tickets by this.
              │  └─────── position in the queue. Changes when priority changes.
              └────────── release (01 = v1). Bounds the sequence so numbers stay short.
```

- **Positions step by 10** — `0010`, `0020`, `0030`.
- **To insert between two tickets, split the difference**: between `0010` and `0020` is `0015`;
  between `0010` and `0015` is `0012`; then `00105`. This never runs out and never renumbers
  anything else.
- **A subticket appends a level**: `0130.0010`, `0130.0010.0010`. Depth is unbounded.
- **Depth means "is a child of", nothing else.** A ticket merely *filed after* `0130` takes a
  sibling slot (`0135`), not `0130.0010`. That keeps the nesting worth reading.
- **Cite tickets by slug, never by number** — "retentive store", not "0130". The number moves when
  priority moves; the slug does not. A number is a position, not a name.
- **Maintenance is a `Kind`, not a prefix.** It carries a queue position like everything else, so
  the next thing to do is always at the top of the folder.
- **Completed tickets keep their number** and move to [`done/`](./done), where the position is
  inert history.

Adopted 2026-08-02, replacing the flat `NNN` scheme with its `002b`/`003a` letter suffixes and `m`
maintenance prefix. The old ids are listed under [Legacy ids](#legacy-ids); documents written before
that date cite them, and are left as written.

### Legacy ids

| Legacy | Now |
|---|---|
| 000 | [project bootstrap](./done/01-0010-project-bootstrap.md) |
| 001 | [walking skeleton](./done/01-0020-walking-skeleton.md) |
| 002 | [core canonical parameters](./done/01-0030-core-5-parameters.md) |
| 002b | [derived wind](./done/01-0030.0010-derived-wind-calculator.md) |
| 002c | [provider nodata mask](./done/01-0030.0020-provider-nodata-mask.md) |
| 003 | split in 2026-07-16 into profile reach + request shaping; never existed after |
| 003a | [profile reach](./done/01-0040-profile-reach.md) |
| 003b | [capability carries its domain](./done/01-0060-capability-domain.md) — **but before 2026-07-21 this id meant request shaping** |
| 003c | [request shaping](./01-0110-request-shaping.md) |
| 004 | [second-provider fallback](./01-0150-second-provider-fallback.md) |
| 005 | [per-parameter selection](./01-0170-per-parameter-selection.md) |
| 006 | [retentive store](./01-0130-retentive-store-freshness.md) |
| 007 | [off-grid homogenization](./01-0140-off-grid-homogenization.md) |
| 008 | [config and graceful degrade](./01-0180-config-secrets-degrade.md) |
| 009 | [errors and partial success](./01-0190-error-taxonomy-partial-success.md) |
| 010 | [unit-conversion catalogue](./01-0160-unit-conversion-edge.md) |
| 011 | [Visual Crossing provider](./01-0120-visual-crossing-provider.md) |
| m1 | [type contract hygiene](./done/01-0050-type-contract-hygiene.md) |
| m2 | [dissolve node-`Countable`](./done/01-0070-dissolve-node-countable.md) |
| m3 | [provider parity checks](./done/01-0080-provider-parity-checks.md) |
| m4 | [snapped request mode](./done/01-0100-snapped-t-request-mode.md) |
| m5 | [edge records](./done/01-0090-edge-records.md) |
| m6 | [artifact conventions sweep](./01-0200-artifact-conventions-sweep.md) |

## Recommended execution order

The **order** is the `#` column of the [delivery map](#delivery-map) — that table is canonical, and
the folder listing mirrors it. This section keeps only the *reasoning* behind that ordering, and
uses legacy ids because it predates the 2026-08-02 renumbering.

1. ~~**002c**~~ — **landed**: the live contract violation (vendor nulls reaching the wire as `NaN`) is
   closed, and 009's nodata semantics are unblocked.
2. ~~**003a**~~ — **landed**: build-time profile reach, no surface or request-path change.
3. ~~**m1**~~ — **landed**: `pyright` green across `src` and `tests`, CI unblocked.
4. ~~**003b**~~ — **landed**: reach moved onto `Capability` per [ADR-0007](../adr/0007-capability-carries-its-domain.md); the standalone resolver is gone.
5. ~~**m3**~~ — **landed**: the parity harness is live and the Open-Meteo reference check passed its
   acceptance run; every new Provider contribution, beginning with 011, ships its own parity check.
6. ~~**m4**~~ — **landed**: the Snapped-T mode and the shape/vendor split, at their proper layer.
   Next: **003c** on top of it, or **006** as an independent follow-on —
   ~~m2~~ has **landed**, so the storeless/private-lattice shape 006 assumes is in place.
7. Complete **007** after 006.
8. Ship **011** (the Visual Crossing Probe — the first test of m4's shape/vendor split), introducing
   **010** when its unit spread creates the real case; then **004** for the fallback behaviour that
   second producer enables.
9. Close the v1 multi-provider surface with **005**, **008**, and **009**.

This ordering clears the known contract violation, establishes independent Provider conformance,
then prioritizes real retention and request shaping before provider fallback and per-parameter
resolution.

## Decisions still owned by tickets

- Delivery planning: either assign Phase 1 resolution logging to a v1 ticket/acceptance criterion or
  move it to the operational-substrate phase.
- [m2](./done/01-0070-dissolve-node-countable.md): where a storeless materialized producer's read-back
  homogenization lives, and whether `EnumerableCapability` remains the "already materialized"
  discriminator → [#37](../concerns.md#37-storeless-materialized-producers-and-read-back-homogenization).
- [005](./01-0170-per-parameter-selection.md): choose the single-provider parameter used to demonstrate
  capability-based routing.
- [006](./01-0130-retentive-store-freshness.md): settle the private store-lattice representation.
- [m3](./done/01-0080-provider-parity-checks.md) (done): *building* scheduled and changed-provider
  automation remains deliberate follow-on work, recorded in the ticket's follow-on section. What
  **enforces** parity coverage and **routes** its selection is now
  [#41](../concerns.md#41-parity-evidence-is-unenforced-and-unrouted), which also owns the retry-once
  policy's missing failure signal.
- [010](./01-0160-unit-conversion-edge.md): build the shared conversion catalogue when ticket 011 exposes
  the first real multi-vendor spread.

## Maintenance rule

Update this page and the affected ticket header when delivery state changes. Other documentation may
say that a feature is **required by v1**, **deferred from v1**, or part of an accepted design, but should
link here instead of restating whether that feature is implemented or next.
