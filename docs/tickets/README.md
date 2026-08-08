# Delivery status

**Last updated:** 2026-08-08

**Current stage:** [006 — retentive store](./01-0115-retentive-store-freshness.md) slice 1,
[`ANY` as the boundless snapped member](./done/01-0115.0010-any-boundless-member.md), has landed.
Next is slice 2, the
[multi-domain carrier and timeline rework](./01-0115.0020-multidomain-carrier-timeline.md); then
slices 3–4, [007 — off-grid homogenization](./01-0117-off-grid-homogenization.md), and only then
another Provider.

This is the source of truth for **what is implemented, what is in progress, what is ready, and what
comes next** — across all open releases, in one queue. The [product roadmap](../product-roadmap.md) owns product direction,
[v1 requirements](../v1-requirements.md) own the release contract, the
[architecture](../architecture.md) and [ADRs](../adr) own design decisions, and individual tickets own
implementation detail and acceptance criteria.

Dated session records and [completed tickets](./done) are historical records. They explain how
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
| MCP `forecast_hourly` | Available | Registered and callable: latitude/longitude, optional parameter subset, and free `start`/`end` windows; omitted bounds default to now → the profile's live reach. |
| Python embedding surface | Planned | No supported facade yet; internal composition is deliberately not public API. The [embedding ticket](./01-0125-supported-python-embedding.md)'s own align selects the contract. |
| Open-Meteo forecast | Available | Fetches all six provider-served canonical parameters. |
| Parameter selection | Partial | Accepts optional subsets of the six exposed product parameters. |
| Provenance and freshness metadata | Available | Returned parameters include source and expiration metadata. |
| Error surface | Partial | Stable error categories exist; per-parameter partial-failure reasons remain. |
| Resolution logging/trace | Planned | [Minimal structured logging](./01-0195-minimal-resolution-logging.md) is assigned for Phase 1; the richer trace sidecar and metrics remain deferred at [concern #14](../concerns.md#14-resolution-trace-and-observability). |
| Canonical v1 parameter set | Done | Six provider-served parameters and two derived wind views; nodata serializes as JSON `null`. |
| Derived wind | Done | `wind_speed` and `wind_direction` are derived from `wind_u` and `wind_v`; direction is nodata below the calm floor ([parameters](../parameters.md)). |
| Free request windows | Available | `start`/`end` ISO datetimes served as `bounds ∩ the live window`; day-anchored Open-Meteo shelf; out-of-range bounds yield the servable part; reach narrated floored to whole days. |
| Second provider and fallback | Planned | Only Open-Meteo is configured. |
| Per-parameter multi-source assembly | Planned | Single-provider multi-node assembly works; multi-provider routing remains. |
| Retentive cache/freshness | Planned | Stores are non-retentive placeholders. |
| Off-grid homogenization | Planned | Nearest-neighbor read-back remains. |
| Configured keyed-provider startup | Partial | Typed settings and key-absent startup work; key-present composition remains. Second provider is **TWC** (reverted 2026-08-08 — the 2026-08-02 Visual Crossing swap rested on TWC access being unverified, which no longer holds). |

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
| 0110 | [Request shaping](./done/01-0110-request-shaping.md) | — | Done | snapped request mode, profile reach, capability domain | Free `start`/`end` windows (datetimes only) riding the Snapped-T mode, plus reach narration; an omitted `end` defaults to the profile's live reach end. |
| 0112 | [Day-anchored availability window](./done/01-0112-day-anchored-availability-window.md) | — | Done | request shaping | `CadenceDef.window_quantum`: the availability window anchors to the vendor's calendar quantum; Open-Meteo declares its probed day-quantized truth; the 003c parity probe passes at any hour. |
| 0115 | [Retentive store](./01-0115-retentive-store-freshness.md) | — | Ready (split) | core canonical parameters | Decision record and union of criteria; delivered by the four subtickets below (align completed 2026-08-08). |
| 0115.0010 | [`ANY` as the boundless snapped member](./done/01-0115.0010-any-boundless-member.md) | — | Done | core canonical parameters | Boundless snapped member, `ground`'s open arm, shared `clip` tolerance. No behavior change. |
| 0115.0020 | [Multi-domain carrier and timeline rework](./01-0115.0020-multidomain-carrier-timeline.md) | — | Ready | `ANY` boundless member | Carrier minted; `agreed_geometries` returns a group; both eager folds retired; natural fetch unit. No behavior change. |
| 0115.0030 | [Retentive timeline Store](./01-0115.0030-timeline-store.md) | — | Planned | multi-domain carrier | `quantize` + unit-granular store with covers-or-refetch-whole; unit-tested, unwired. |
| 0115.0040 | [Reservoir retention pipeline](./01-0115.0040-reservoir-retention-pipeline.md) | — | Planned | retentive timeline store | Retention live in both positions; mixed-request divergence dissolves; e2e re-fetch assertion flips. |
| 0117 | [Off-grid homogenization](./01-0117-off-grid-homogenization.md) | — | Planned | retentive store | Nearest-neighbor read-back completes a storing `Reservoir`: values retained on its private lattice are reported at the exact requested point. |
| 0120 | [TWC provider](./01-0120-twc-provider.md) | — | Ready | snapped request mode, provider parity checks | TWC `TimelineProbe` (same shape as the primary, so no wrapper), first shipped `SecretSlot`, its parity check. Split from second-provider fallback on 2026-08-02; reverted to TWC from Visual Crossing on 2026-08-08. |
| 0125 | [Supported Python embedding surface](./01-0125-supported-python-embedding.md) | — | Planned (own align precedes) | — (former v1-tail gates dissolved 2026-08-08; see ticket) | Supported headless package boundary with public failures; ships early under live-equivalence — capability grows as later tickets land. |
| 02-0130 | [Mongo obs source](./02-0130-mongo-obs-source.md) | — | Planned (own align precedes) | embedding surface (its consumer's construction path) | First private source: read-only projection over the operator's collector MongoDB — station registry + hourly observations; first non-HTTP transport; past-facing capability; settles [#45](../concerns.md#45-the-collector-schema-is-a-contract-meteoscape-depends-on-but-does-not-own)'s mitigations. |
| 02-0134 | [Mongo forecast-run archive source](./02-0134-forecast-run-archive-source.md) | — | Planned (own align precedes) | Mongo obs source (shares transport + registry) | Run-keyed (`base_time`) forecast archive over the collector's common schema; per-provider origins (`ibm`, `tomorrow`, `visualcrossing`) — likely first exercise of manifest `expand`; cross-run semantics stay at [#9](../concerns.md#9-cross-run-combination). |
| 02-0140 | [Correction calculator](./02-0140-correction-calculator.md) | — | Planned (own align precedes) | Mongo obs source, Mongo forecast-run archive source | First cross-source, cross-time calculator: per-source, per-parameter bias report over paired forecast/obs history; correction only after bias proves stable. |
| 0150 | [Second-provider fallback](./01-0150-second-provider-fallback.md) | — | Planned | core canonical parameters, request shaping, TWC provider | Wholesale priority fallback across two producers — Arbiter behaviour only, mocked transports, no live network. |
| 0160 | [Unit-conversion catalogue](./01-0160-unit-conversion-edge.md) | — | Planned | core canonical parameters; triggered by TWC provider | Shared verified native-to-canonical conversion edges. |
| 0170 | [Per-parameter selection](./01-0170-per-parameter-selection.md) | — | Planned | second-provider fallback | One response assembled from different winning providers by parameter. |
| 0180 | [Config and graceful degrade](./01-0180-config-secrets-degrade.md) | — | Partial | TWC provider | Complete key-present/key-absent provider construction behavior. |
| 0190 | [Errors and partial success](./01-0190-error-taxonomy-partial-success.md) | — | Partial | provider nodata mask, request shaping, second-provider fallback | Per-parameter absence reasons and capable-but-faulting partial results. |
| 0195 | [Minimal resolution logging](./01-0195-minimal-resolution-logging.md) | — | Planned (own align precedes) | retentive store, second-provider fallback, per-parameter selection, errors and partial success | Structured producer-selection, fall-through, and Store hit/refill evidence; no data-product change. |
| 0200 | [Artifact conventions sweep](./01-0200-artifact-conventions-sweep.md) | Maint | Planned (own align precedes) | edge records | Canonical artifact-conventions registry: full doc roster classified (normative vs descriptive, granularity, lifecycle), skills slimmed to reference it. |

## Ticket numbering

A ticket's filename is `RR-NNNN-slug.md` — release, position, name:

```
docs/tickets/01-0115-retentive-store-freshness.md
              │  │    └── slug — what the ticket is. Never changes. Cite tickets by this.
              │  └─────── position in the queue — global across releases. Changes when priority changes.
              └────────── release (01 = v1). Names the contract the ticket serves.
```

- **A release is a contract-closure milestone, not a chronological gate.** Execution interleaves
  across open releases in one queue (the delivery map's order); a release closes when its contract's
  criteria are all met, regardless of what landed around it — release-02 tickets may land before v1
  closes. Release 02 (the shape-diversity workstream: archive source, correction calculators, new
  source shapes) opened at the 2026-08-08 align; its requirements doc is deliberately deferred until
  its first shapes land and teach us what the contract should say.
- **Positions are one global line across releases** (2026-08-08). A ticket's position orders it
  against *every* open ticket, not only its own release's — `02-0130` executes between `01-0120` and
  `01-0150`. The release prefix names the contract; the folder therefore groups by release and is
  ordered only within one, and the delivery map is the cross-release order.
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
| 003c | [request shaping](./done/01-0110-request-shaping.md) |
| 004 | [second-provider fallback](./01-0150-second-provider-fallback.md) |
| 005 | [per-parameter selection](./01-0170-per-parameter-selection.md) |
| 006 | [retentive store](./01-0115-retentive-store-freshness.md) |
| 007 | [off-grid homogenization](./01-0117-off-grid-homogenization.md) |
| 008 | [config and graceful degrade](./01-0180-config-secrets-degrade.md) |
| 009 | [errors and partial success](./01-0190-error-taxonomy-partial-success.md) |
| 010 | [unit-conversion catalogue](./01-0160-unit-conversion-edge.md) |
| 011 | [TWC provider](./01-0120-twc-provider.md) — Visual Crossing 2026-08-02 → 2026-08-08, TWC before and after |
| m1 | [type contract hygiene](./done/01-0050-type-contract-hygiene.md) |
| m2 | [dissolve node-`Countable`](./done/01-0070-dissolve-node-countable.md) |
| m3 | [provider parity checks](./done/01-0080-provider-parity-checks.md) |
| m4 | [snapped request mode](./done/01-0100-snapped-t-request-mode.md) |
| m5 | [edge records](./done/01-0090-edge-records.md) |
| m6 | [artifact conventions sweep](./01-0200-artifact-conventions-sweep.md) |

## Recommended execution order

The **order** is the `#` column of the [delivery map](#delivery-map) — that table is canonical; the
folder listing mirrors it within each release. This section keeps only the *reasoning* behind that ordering, and
uses legacy ids because it predates the 2026-08-02 renumbering.

1. ~~**002c**~~ — **landed**: the live contract violation (vendor nulls reaching the wire as `NaN`) is
   closed, and 009's nodata semantics are unblocked.
2. ~~**003a**~~ — **landed**: build-time profile reach, no surface or request-path change.
3. ~~**m1**~~ — **landed**: `pyright` green across `src` and `tests`, CI unblocked.
4. ~~**003b**~~ — **landed**: reach moved onto `Capability` per [ADR-0007](../adr/0007-capability-carries-its-domain.md); the standalone resolver is gone.
5. ~~**m3**~~ — **landed**: the parity harness is live and the Open-Meteo reference check passed its
   acceptance run; every new Provider contribution, beginning with 011, ships its own parity check.
6. ~~**m4**~~ — **landed**: the Snapped-T mode and the shape/vendor split, at their proper layer.
   ~~**003c**~~ — **landed** on top of it: free windows at the edge, reach narration,
   `default_horizon` gone.
7. **Day-anchored availability before everything else** — repair the live provider declaration that
   currently makes the full-reach default time-of-day-dependent.
8. **006, then 007** — retention collapses the mixed-request double fetch; off-grid homogenization
   immediately completes the storing `Reservoir` by sampling its private lattice back onto the exact
   requested point. No new Provider lands between those two halves of the retention path.
9. Ship **011** (the TWC Probe — the first test of m4's shape/vendor split), introducing
   **010** when its unit spread creates the real case.
10. *(2026-08-08 align, reordered)* The [supported Python embedding
    surface](./01-0125-supported-python-embedding.md) **moves up** — the first real embedder arrives
    with the release-02 work, so the facade ships early under the live-equivalence rule and no
    longer waits for the v1 tail.
11. **Release 02 head**: the Mongo obs source (`02-0130`), the forecast-run archive source
    (`02-0134`), then the correction calculator (`02-0140`) — the shape-diversity work the
    2026-08-08 align pulled forward, split by shape (obs vs run archive); tickets minted after
    that align.
12. Close the v1 contract with **004**, **005**, **008**, **009**, and [minimal resolution
    logging](./01-0195-minimal-resolution-logging.md); the artifact-conventions maintenance sweep
    remains last.
13. Release 02 resumes one-shape-per-milestone: the provider plugin seam
    ([#26](../concerns.md#26-provider--calculator-plugin-scaffolding) — live station endpoints are
    embedder-authored plug-ins, not in-tree providers), local grid file, FTP transport.

This ordering clears the known contract violation, establishes independent Provider conformance,
then prioritizes real retention and request shaping before provider fallback and per-parameter
resolution.

## Decisions still owned by tickets

- [Supported Python embedding surface](./01-0125-supported-python-embedding.md): its own align selects
  the facade/lifecycle, public failure contract, request ergonomics, and `0.x` compatibility policy
  still open at concerns #39/#40; this queue pass deliberately selects none of them.
- [Minimal resolution logging](./01-0195-minimal-resolution-logging.md): its own align selects the
  event granularity, correlation, and sensitive-field policy; the structured trace sidecar and wider
  metrics surface remain deferred at concern #14.
- [m2](./done/01-0070-dissolve-node-countable.md): where a storeless materialized producer's read-back
  homogenization lives, and whether `EnumerableCapability` remains the "already materialized"
  discriminator → [#37](../concerns.md#37-storeless-materialized-producers-and-read-back-homogenization).
- [005](./01-0170-per-parameter-selection.md): choose the single-provider parameter used to demonstrate
  capability-based routing.
- [006](./01-0115-retentive-store-freshness.md): align completed 2026-08-08 — refill scope (ask
  narrow, answer natural, store absorbs), the partial-warm edge (covers-or-refetch-whole), `ANY` as
  the boundless snapped member, the group-returning fold, and the #22/#23 deferrals are all
  recorded in the ticket; narrow-answering providers moved to
  [#43](../concerns.md#43-narrow-answering-providers-re-open-mixed-request-run-divergence) (decided
  at 011). Still ticket-owned: the fold/carrier **naming checkpoint** (fires at
  [0115.0020](./01-0115.0020-multidomain-carrier-timeline.md)) and `assimilate`'s concrete shapes
  (revisited at [0115.0030](./01-0115.0030-timeline-store.md)).
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
