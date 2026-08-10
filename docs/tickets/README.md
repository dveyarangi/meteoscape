# Delivery status

**Last updated:** 2026-08-10

**Current stage:** [007 — off-grid homogenization](./done/01-0117-off-grid-homogenization.md) is
**delivered** (guard ticket: behaviour landed with 006; tests and records closed 2026-08-10).
Next is [TWC as the primary Provider](./01-0120-twc-provider.md).

**Re-cut 2026-08-10 (beeline align).** The queue was re-ordered against a stated product beeline:
*forecast correction from local stations, TWC as the **main** provider, persistent cache, embedded
Python, a REST surface, and provider quota monitoring.* What changed:

- **TWC becomes the primary**, not a spare — which pulls
  [fallback](./01-0121-second-provider-fallback.md), [unit conversion](./01-0122-unit-conversion-edge.md),
  and [config/secrets](./01-0123-config-secrets-degrade.md) up behind it (positions 0121–0123, was
  0150/0160/0180). A metered primary that can 429 makes fall-through load-bearing rather than
  resilience polish.
- **Four tickets minted**: the [vendor-call ledger](./02-0124-vendor-call-ledger.md) and its
  [budget governor](./02-0155-vendor-budget-governor.md) (two slices — meter first, authority
  second), the [persisting Store](./02-0145-persisting-store.md), and the
  [REST surface](./02-0165-rest-surface.md).
- **Demoted off the beeline**: [per-parameter selection](./01-0170-per-parameter-selection.md),
  [errors and partial success](./01-0190-error-taxonomy-partial-success.md),
  [minimal resolution logging](./01-0195-minimal-resolution-logging.md), and the
  [conventions sweep](./01-0200-artifact-conventions-sweep.md) — the v1 tail.
- **Unchanged at the head**: 007 stays first. Stations are off-grid points, so the correction
  workstream reads through the same read-back — but it is not *blocked* on 007: pairing a forecast to
  a station's coordinates already answers at that point. What 007 adds is the seam the identity
  Resampler lives in.

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
| Second provider and fallback | Planned | Only Open-Meteo is configured. **TWC becomes the primary** and Open-Meteo the backstop (2026-08-10); fall-through on fault does not exist yet — a `runtime-failure` fails the whole request. |
| Per-parameter multi-source assembly | Planned | Single-provider multi-node assembly works; multi-provider routing remains. |
| Retentive cache/freshness | Available | In-memory `MemoryStore` in both positions; fresh repeats serve with no vendor call; cold mixed requests issue one fetch. Process-lifetime only. |
| Persistent retention | Planned | Retention dies with the process. Rung 2 of the substrate ladder — survives restart, shared across processes — is [ticketed](./02-0145-persisting-store.md); rung 3 (bulk/analytical) stays at [#44](../concerns.md#44-dedicated-live-archive-store-for-throughput). |
| Vendor-call metering and budget | Planned | No count of outbound vendor calls exists. The [ledger](./02-0124-vendor-call-ledger.md) meters at the Source seam (not the Gateway, which can only see requests); the [governor](./02-0155-vendor-budget-governor.md) later gives it authority to refuse. |
| REST / HTTP surface | Planned | Local stdio MCP only. [Ticketed](./02-0165-rest-surface.md) as the operator deployment shape; does not amend v1, which defers HTTP transport by name. |
| Off-grid homogenization | Available | An off-grid point is answered **at the requested point**, read back from the **enclosing** store cell with the **identity** Resampler. Guarded by Reservoir and e2e tests; the MCP edge states the fidelity floor (one cell ⇒ identical values). |
| Configured keyed-provider startup | Partial | Typed settings and key-absent startup work; key-present composition remains. The keyed provider is **TWC** (reverted 2026-08-08 — the 2026-08-02 Visual Crossing swap rested on TWC access being unverified, which no longer holds), and as of 2026-08-10 it is the **primary**, so key-absent is the degraded mode rather than the normal one. |

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
| 0113 | [Per-parameter materialized capability](./done/01-0113-per-parameter-materialized-capability.md) | Maint | Done | — | `GranularCapability` is the own-geometry form for independently shaped parameters; Providers, multi-domain carriers, and stores advertise through it. Geometry's identity/prose cleanup remains [#46](../concerns.md#46-composition-failure-attribution-is-paid-inside-geometry), triggered by a regional provider or curvilinear domain. |
| 0115 | [Retentive store](./done/01-0115-retentive-store-freshness.md) | — | Done (split) | core canonical parameters | Decision record and union of criteria; delivered by the four subtickets below. |
| 0115.0010 | [`ANY` as the boundless snapped member](./done/01-0115.0010-any-boundless-member.md) | — | Done | core canonical parameters | Boundless snapped member, `ground`'s open arm, shared `clip` tolerance. No behavior change. |
| 0115.0020 | [Multi-domain carrier and timeline rework](./done/01-0115.0020-multidomain-carrier-timeline.md) | — | Done | `ANY` boundless member, per-parameter materialized capability | `CoverageSet` minted; `clip` takes optional bounds; `agreed_geometry` licenses open-axis difference under a request-derived licence; both eager folds retired; natural fetch unit. |
| 0115.0030 | [Retentive Store (`MemoryStore`)](./done/01-0115.0030-timeline-store.md) | — | Done | multi-domain carrier | `quantize` + the unit-granular, clockless `MemoryStore` holdings leaf; wired inert until slice 4. |
| 0115.0040 | [Reservoir retention pipeline](./done/01-0115.0040-reservoir-retention-pipeline.md) | — | Done | retentive store leaf | Retention live in both positions; serve-vs-refetch gate as `Reservoir` policy; mixed-request divergence dissolves; e2e re-fetch assertion flips. |
| 0117 | [Off-grid homogenization](./done/01-0117-off-grid-homogenization.md) | — | Done | retentive store | Read-back completes a storing `Reservoir`: point-exact reporting, enclosing-cell selection. Guard ticket ([RFC 0016](../rfc/0016-20260810-off-grid-homogenization.md)): tests, records, stale `TODO` removed; no `src` logic changes. |
| 0120 | [TWC provider — as primary](./01-0120-twc-provider.md) | — | Ready | snapped request mode, provider parity checks | TWC `TimelineProbe` (same shape, so no wrapper), first shipped `SecretSlot`, its parity check, **and the priority flip putting it ahead of Open-Meteo** (2026-08-10). The parity check becomes load-bearing; key-absent becomes the degraded mode. |
| 0121 | [Second-provider fallback](./01-0121-second-provider-fallback.md) | — | Planned | TWC provider | Wholesale priority fallback — **TWC primary → Open-Meteo backstop**. Arbiter behaviour only, mocked transports, no live network. Load-bearing as of 2026-08-10: a metered primary's 429 is a `runtime-failure`, which today fails the whole request. Was 0150. |
| 0122 | [Unit-conversion catalogue](./01-0122-unit-conversion-edge.md) | — | Planned | core canonical parameters; triggered by TWC provider | Shared verified native-to-canonical conversion edges. Likely bites immediately now that TWC's native units are on the default path. Was 0160. |
| 0123 | [Config and graceful degrade](./01-0123-config-secrets-degrade.md) | — | Partial | TWC provider | Complete key-present/key-absent provider construction. Heavier as of 2026-08-10: key-absent is now the *degraded* mode, and this is the secret path the Mongo sources and the ledger both ride. Was 0180. |
| 02-0124 | [Vendor-call ledger (meter)](./02-0124-vendor-call-ledger.md) | — | Planned (own align precedes) | TWC provider, config and graceful degrade | Injected per-deployment ledger counting **outbound vendor calls** by `SourceKey` — the Source-seam meter, not the Gateway's caller meter. Observes only; no behavioural change. |
| 0125 | [Supported Python embedding surface](./01-0125-supported-python-embedding.md) | — | Planned (own align precedes) | — (former v1-tail gates dissolved 2026-08-08; stale list removed 2026-08-10) | Supported headless package boundary with public failures; ships early under live-equivalence — capability grows as later tickets land. Embedding is the deployment's first consumption shape; REST follows. |
| 02-0130 | [Mongo obs source](./02-0130-mongo-obs-source.md) | — | Planned (own align precedes) | embedding surface (its consumer's construction path); config and graceful degrade (its connection string is a secret) | First private source: read-only projection over the operator's collector MongoDB — station registry + hourly observations; first non-HTTP transport; past-facing capability; settles [#45](../concerns.md#45-the-collector-schema-is-a-contract-meteoscape-depends-on-but-does-not-own)'s mitigations. |
| 02-0134 | [Mongo forecast-run archive source](./02-0134-forecast-run-archive-source.md) | — | Planned (own align precedes) | Mongo obs source (shares transport + registry) | Run-keyed (`base_time`) forecast archive over the collector's common schema; per-provider origins (`ibm`, `tomorrow`, `visualcrossing`) — likely first exercise of manifest `expand`; cross-run semantics stay at [#9](../concerns.md#9-cross-run-combination). |
| 02-0140 | [Correction calculator](./02-0140-correction-calculator.md) | — | Planned (own align precedes) | Mongo obs source, Mongo forecast-run archive source | First cross-source, cross-time calculator: per-source, per-parameter bias report over paired forecast/obs history; correction only after bias proves stable. |
| 02-0145 | [Persisting Store](./02-0145-persisting-store.md) | — | Planned (own align precedes) | retentive store | Rung 2 of the substrate ladder: retained Holdings survive restart and are shared across processes, behind the unchanged `Store` face. Both positions persist. Substrate and key shape are the ticket's align. |
| 02-0155 | [Vendor budget governor](./02-0155-vendor-budget-governor.md) | — | Planned (own align precedes) | vendor-call ledger, second-provider fallback | The ledger gains authority to refuse: budget spent ⇒ `runtime-failure` with no HTTP call ⇒ fall-through serves from the backstop. Quota never moves `Capability`. |
| 02-0165 | [REST surface](./02-0165-rest-surface.md) | — | Planned (own align + Edge record precede) | embedding surface (by decision, not mechanically) | The operator's deployment shape: HTTP over the same `Gateway` seam MCP uses. Makes the Gateway's caller-policy seam non-null — where **caller** quota lives. Does not amend v1; release-02 surface work. |
| 0170 | [Per-parameter selection](./01-0170-per-parameter-selection.md) | — | Planned | second-provider fallback | One response assembled from different winning providers by parameter. Off the beeline (2026-08-10). |
| 0190 | [Errors and partial success](./01-0190-error-taxonomy-partial-success.md) | — | Partial | provider nodata mask, request shaping, second-provider fallback | Per-parameter absence reasons and capable-but-faulting partial results. |
| 0195 | [Minimal resolution logging](./01-0195-minimal-resolution-logging.md) | — | Planned (own align precedes) | retentive store, second-provider fallback, per-parameter selection, errors and partial success | Structured producer-selection, fall-through, and Store hit/refill evidence; no data-product change. Stays in the tail (it needs 0170/0190); the [ledger](./02-0124-vendor-call-ledger.md) ships the smallest honest spend read-out it needs, and 0195 later absorbs rather than duplicates it. |
| 0200 | [Artifact conventions sweep](./01-0200-artifact-conventions-sweep.md) | Maint | Planned (own align precedes) | edge records | Canonical artifact-conventions registry: full doc roster classified (normative vs descriptive, granularity, lifecycle), skills slimmed to reference it. |

## Ticket numbering

A ticket's filename is `RR-NNNN-slug.md` — release, position, name:

```
docs/tickets/done/01-0115-retentive-store-freshness.md
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
| 004 | [second-provider fallback](./01-0121-second-provider-fallback.md) |
| 005 | [per-parameter selection](./01-0170-per-parameter-selection.md) |
| 006 | [retentive store](./done/01-0115-retentive-store-freshness.md) |
| 007 | [off-grid homogenization](./done/01-0117-off-grid-homogenization.md) |
| 008 | [config and graceful degrade](./01-0123-config-secrets-degrade.md) |
| 009 | [errors and partial success](./01-0190-error-taxonomy-partial-success.md) |
| 010 | [unit-conversion catalogue](./01-0122-unit-conversion-edge.md) |
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

### The 2026-08-10 beeline re-cut

Steps 9–13 above are superseded from 011 onward, and kept as written for the reasoning that led
there. The stated beeline — correction from local stations, **TWC as main provider**, persistent
cache, embedded Python, a REST surface, provider quota monitoring — reorders what follows 007:

1. **007 stays first.** A station is an off-grid point, so the correction workstream's
   forecast-at-a-station pairing rides this read-back — though it does not block on it (the point-exact
   half already landed with 006). No new Provider lands between the two halves of the retention path,
   as before.
2. **011 → 004 → 010 → 008, in that order, because TWC is primary.** Selection flips with two
   integers; what follows is the cost of depending on a metered vendor. Fall-through (004) makes a
   429 survivable, unit conversion (010) bites once TWC's native units are on the default path, and
   config (008) owns key-absent as the *degraded* mode.
3. **The ledger's meter slice**, behind 008's injection path. Watch the real spend before
   throttling it — the same discipline the roadmap applies to bias correction ("correct only after
   the bias proves stable"). The governor slice waits until after the product work.
4. **The embedding surface**, then the **correction workstream** (`02-0130` → `02-0134` →
   `02-0140`) — the product goal, and the reason for the beeline.
5. **Persisting Store, then the budget governor, then REST.** Persistence sits here rather than
   earlier because MCP stdio fast-use *should* stay transient and low-retention (rung 1), and the
   deployment is a long-running process that keeps its cache hot anyway — so persistence buys
   restart and redeploy survival, not per-session survival. It stays ahead of REST because a
   long-running HTTP service wants it more.
6. **The v1 tail** — per-parameter selection, errors and partial success, minimal resolution
   logging, conventions sweep — closes behind the beeline.

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
- [006](./done/01-0115-retentive-store-freshness.md): align completed 2026-08-08 — refill scope (ask
  narrow, answer natural, store absorbs), the partial-warm edge (covers-or-refetch-whole), `ANY` as
  the boundless snapped member, and the #22/#23 deferrals are all
  recorded in the ticket; narrow-answering providers moved to
  [#43](../concerns.md#43-narrow-answering-providers-re-open-mixed-request-run-divergence) (decided
  at 011). The fold/carrier **naming checkpoint closed** at
  [0115.0020](./done/01-0115.0020-multidomain-carrier-timeline.md) — `agreed_geometry` and
  `CoverageSet`, and the align's group-returning fold was **rejected** there: the differing
  resolutions had no reader, so the fold keeps its single return and the carrier is built from the
  records. Still ticket-owned: `assimilate`'s concrete shapes (revisited at
  [0115.0030](./done/01-0115.0030-timeline-store.md)).
- [m3](./done/01-0080-provider-parity-checks.md) (done): *building* scheduled and changed-provider
  automation remains deliberate follow-on work, recorded in the ticket's follow-on section. What
  **enforces** parity coverage and **routes** its selection is now
  [#41](../concerns.md#41-parity-evidence-is-unenforced-and-unrouted), which also owns the retry-once
  policy's missing failure signal.
- [010](./01-0122-unit-conversion-edge.md): build the shared conversion catalogue when ticket 011 exposes
  the first real multi-vendor spread — now likely at 011 itself, since TWC's native units land on the
  default path.
- [Vendor-call ledger](./02-0124-vendor-call-ledger.md): its own align selects what an entry is (one
  HTTP request vs one `Provider.project`), attribution granularity, the accounting period and where
  it is kept, the read-out channel, and whether failed calls count.
- [Persisting Store](./02-0145-persisting-store.md): its own align selects the **substrate** and the
  **key shape** — today's `_HoldingKey` carries X/Y as *indices into a lattice held elsewhere*, which
  is safe only while rows and lattice live and die together. Deliberately not chosen at the
  2026-08-10 align.
- [Vendor budget governor](./02-0155-vendor-budget-governor.md): its own align selects budget
  expression, headroom policy, caller visibility, and what exhaustion means with **no backstop**
  available — refuse, or serve past `expiration`? The second would change the MCP edge's staleness
  promise.
- [REST surface](./02-0165-rest-surface.md): its own align selects the resource model, the
  failure→status-code mapping (which may reopen #39's rendering, settled first at 0125), the
  Gateway's non-null caller policy, and serialization format.

## Maintenance rule

Update this page and the affected ticket header when delivery state changes. Other documentation may
say that a feature is **required by v1**, **deferred from v1**, or part of an accepted design, but should
link here instead of restating whether that feature is implemented or next.
