# Delivery status

**Last updated:** 2026-08-18

**Current stage:** [second-provider fallback](./done/01-0121-second-provider-fallback.md) is
delivered (2026-08-18) — a metered primary's fault no longer fails the request. Next is
[unit-conversion catalogue](./01-0122-unit-conversion-edge.md) if TWC's native units create the
spread its trigger waits for, else [config and graceful degrade](./01-0123-config-secrets-degrade.md),
which owns key-absent as the *degraded* mode.

**Re-cut 2026-08-10 (beeline align).** The queue was re-ordered against a stated product beeline:
*forecast correction from local stations, TWC as the **main** provider, persistent cache, embedded
Python, a REST surface, and provider quota monitoring.* What changed:

- **TWC becomes the primary**, not a spare — which pulls
  [fallback](./done/01-0121-second-provider-fallback.md), [unit conversion](./01-0122-unit-conversion-edge.md),
  and [config/secrets](./01-0123-config-secrets-degrade.md) up behind it (positions 0121–0123, was
  0150/0160/0180). A metered primary that can 429 makes fall-through load-bearing rather than
  resilience polish.
- **Four tickets minted**: the [vendor-call ledger](./01-0124-vendor-call-ledger.md) and its
  [budget governor](./01-0155-vendor-budget-governor.md) (two slices — meter first, authority
  second), the [persisting SQLite Store](./01-0145-persisting-store.md), and the
  [REST surface](./01-0165-rest-surface.md).
- **Demoted off the beeline**: [per-parameter selection](./02-0170-per-parameter-selection.md),
  [errors and partial success](./02-0190-error-taxonomy-partial-success.md),
  [minimal resolution logging](./02-0195-minimal-resolution-logging.md), and the
  [conventions sweep](./02-0200-artifact-conventions-sweep.md) — the former v1 tail.
- **Unchanged at the head**: 007 stays first. Stations are off-grid points, so the correction
  workstream reads through the same read-back — but it is not *blocked* on 007: pairing a forecast to
  a station's coordinates already answers at that point. What 007 adds is the seam the identity
  Resampler lives in.

**Release boundary corrected 2026-08-18.** The bee-line is v1, not work occurring ahead of the old
v1 tail. Its tickets therefore serve release 01; the four tickets above move to release 02. The
existing [v1 requirements](../v1-requirements.md) describe the predecessor scope and are no longer
the authority for open-ticket release membership while their replacement is aligned.

This is the source of truth for **what is implemented, what is in progress, what is ready, and what
comes next** — across all open releases, in one queue. The [product roadmap](../product-roadmap.md)
owns product direction, the release requirements own the release contract, the
[architecture](../architecture.md) and [ADRs](../adr) own design decisions, and individual tickets
own implementation detail and acceptance criteria.

Dated session records and [completed tickets](./done) are historical records. They explain how
the project reached its current state; they do not override this page.

## Status vocabulary

**Done**, **In progress**, **Ready**, **Partial**, **Planned**, **Blocked** — defined in
[TICKET-FORMAT.md § Status](../../.agents/skills/to-tickets/TICKET-FORMAT.md#status).

No active ticket is presently **Blocked**: everything unstarted is waiting on an ordinary incomplete
dependency, which is ordering, not blockage.

## Available today

| Capability | Status | Current behavior |
|---|---|---|
| MCP `forecast_hourly` | Available | Registered and callable: latitude/longitude, optional parameter subset, and free `start`/`end` windows; omitted bounds default to now → the profile's live reach. |
| Python embedding surface | Planned | No supported facade yet; internal composition is deliberately not public API. The [embedding ticket](./01-0125-supported-python-embedding.md)'s own align selects the contract. |
| Open-Meteo forecast | Available | Fetches all six provider-served canonical parameters. |
| Parameter selection | Partial | Accepts optional subsets of the six exposed product parameters. |
| Provenance and freshness metadata | Available | Returned parameters include source and expiration metadata. |
| Error surface | Partial | Stable error categories exist; per-parameter partial-failure reasons remain. |
| Resolution logging/trace | Planned | [Minimal structured logging](./02-0195-minimal-resolution-logging.md) moved behind v1 with the former tail; the richer trace sidecar and metrics remain deferred at [concern #14](../concerns.md#14-resolution-trace-and-observability). |
| Canonical v1 parameter set | Done | Six provider-served parameters and two derived wind views; nodata serializes as JSON `null`. Known Open-Meteo precipitation hour-label error → [#48](../concerns.md#48-a-tap-cannot-declare-where-its-value-sits-relative-to-the-tick). |
| Derived wind | Done | `wind_speed` and `wind_direction` are derived from `wind_u` and `wind_v`; direction is nodata below the calm floor ([parameters](../parameters.md)). |
| Free request windows | Available | `start`/`end` ISO datetimes served as `bounds ∩ the live window`; day-anchored Open-Meteo shelf; out-of-range bounds yield the servable part; reach narrated floored to whole days. |
| Second provider and fallback | Available | **TWC is the configured primary** ([TWC provider](./done/01-0120-twc-provider.md)) with Open-Meteo the backstop; a spanning ask serves the primary's clipped shape → [#49](../concerns.md#49-spanning-asks-serve-the-primary-max-reach-is-unbuilt-policy). A child's `runtime-failure` falls through wholesale to the next admitted producer; exhaustion still fails the whole request → [second-provider fallback](./done/01-0121-second-provider-fallback.md). |
| Per-parameter multi-source assembly | Planned | Single-provider multi-node assembly works; multi-provider routing remains. |
| Retentive cache/freshness | Available | In-memory `MemoryStore` in both positions; fresh repeats serve with no vendor call; cold mixed requests issue one fetch. Process-lifetime only. A declared live window is an estimate — rolling retention is horizon-satisfied, static by containment ([live-window edge tolerance](./done/01-0119-live-window-edge-tolerance.md)). |
| Persistent retention | Planned | Retention dies with the process. Rung 2 of the substrate ladder — survives restart, shared across processes — is [ticketed](./01-0145-persisting-store.md); rung 3 (bulk/analytical) stays at [#44](../concerns.md#44-dedicated-live-archive-store-for-throughput). |
| Vendor-call metering and budget | Planned | No count of outbound vendor calls exists. The [ledger](./01-0124-vendor-call-ledger.md) meters at the Source seam (not the Gateway, which can only see requests); the [governor](./01-0155-vendor-budget-governor.md) later gives it authority to refuse. |
| REST / HTTP surface | Planned | Local stdio MCP only. [Ticketed](./01-0165-rest-surface.md) as the operator deployment shape and part of the v1 bee-line. |
| Off-grid homogenization | Available | An off-grid point is answered **at the requested point**, read back from the **enclosing** store cell with the **identity** Resampler. Guarded by Reservoir and e2e tests; the MCP edge states the fidelity floor (one cell ⇒ identical values). |
| Configured keyed-provider startup | Available | Key-present composes TWC as the primary; key-absent degrades to Open-Meteo alone. Vendor-named `Settings` fields remain acknowledged v1 plumbing → [config/secrets](./01-0123-config-secrets-degrade.md), which owns the generic form. |

## Delivery map

One queue, in the order the work is done — this table is the canonical order. The **#** column is
the ticket's position ([Ticket numbering](#ticket-numbering)); the `Kind` column marks maintenance
work `Maint`. What those columns mean is
[TICKET-FORMAT.md § The queue](../../.agents/skills/to-tickets/TICKET-FORMAT.md#the-queue).

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
| 0117 | [Off-grid homogenization](./done/01-0117-off-grid-homogenization.md) | — | Done | retentive store | Off-grid points are reported at the requested point using the enclosing store cell's value. |
| 0118 | [Sample-level allowance](./done/01-0118-sample-level-allowance.md) | — | Done | — | Two producers declaring the same parameter at nearby sample levels compose into one profile; outside the declared allowance still fails the build. Position 0118 uses the remaining slot before 0119; the four-digit gap was exhausted. |
| 0119 | [Live-window edge tolerance](./done/01-0119-live-window-edge-tolerance.md) | — | Done | reservoir retention pipeline, off-grid homogenization | A leaf whose declared live window exceeds its delivered series serves the overlap and avoids repeated gap refetches; static axes stay exact. |
| 0120 | [TWC provider — as primary](./done/01-0120-twc-provider.md) | — | Done | snapped request mode, provider parity checks, sample-level allowance | TWC is the primary producer, with offering-specific horizons, keyed startup, and a live parity check. Spanning asks serve its clipped shape → [#49](../concerns.md#49-spanning-asks-serve-the-primary-max-reach-is-unbuilt-policy). |
| 0127 | [Doc-corpus integrity gate](./done/01-0127-docs-integrity-gate.md) | Maint | Done | — | CI fails when a live document's relative link or heading anchor stops resolving, when any tracked file carries a BOM, control character, or listed invisible codepoint, when a code comment's doc pointer (concern, ADR, or `.md` path) no longer resolves, or when the queue and the ticket folders disagree; historical records stay exempt from link gating. *Row sits where the work happens; 0121–0126 left no free integer, so the position is the nearest free slot.* |
| 0128 | [Mechanical record moves](./done/01-0128-mechanical-record-moves.md) | Maint | Done | doc-corpus integrity gate | Closing a ticket or RFC into `done/` and archiving a session into `history/` are performed by one mechanical mover that re-depths the moved record's links and rewrites every inbound reference, leaving nothing link-shaped to hand-edit; the integrity gate verifies each move. |
| 0121 | [Second-provider fallback](./done/01-0121-second-provider-fallback.md) | — | Done | TWC provider | Wholesale priority fallback across two producers: a child's `runtime-failure` re-enters selection, skipping who faulted; exhaustion still fails the whole request. |
| 0122 | [Unit-conversion catalogue](./01-0122-unit-conversion-edge.md) | — | Planned | core canonical parameters | Shared verified native-to-canonical conversion edges. |
| 0123 | [Config and graceful degrade](./01-0123-config-secrets-degrade.md) | — | Partial | TWC provider | Complete key-present/key-absent provider construction behavior. |
| 0124 | [Vendor-call ledger (meter)](./01-0124-vendor-call-ledger.md) | — | Planned (own align precedes) | TWC provider, config and graceful degrade | An operator can answer how many vendor calls a deployment spent, against which vendor, and over what period, with no effect on request results. |
| 0125 | [Supported Python embedding surface](./01-0125-supported-python-embedding.md) | — | Planned (own align precedes) | — | A supported Python package boundary resolves the same v1 forecast product as MCP without a protocol server and exposes expected failures through public API. |
| 0126 | [Tick-convention declaration](./01-0126-tick-convention-declaration.md) | — | Planned (own align precedes) | TWC provider (the second convention) | A tap declares where its value sits relative to the tick, and Open-Meteo precipitation stops being labelled an hour late. |
| 0130 | [Mongo obs source](./01-0130-mongo-obs-source.md) | — | Planned (own align precedes) | embedding surface (its consumer's construction path); config and graceful degrade (its connection string is a secret) | Hourly station observations from the operator's Collector database are served through the projection algebra as a read-only private source, with per-parameter provenance. |
| 0134 | [Mongo forecast-run archive source](./01-0134-forecast-run-archive-source.md) | — | Planned (own align precedes) | Mongo obs source (shares transport + registry) | Archived forecast runs are served as distinct per-provider origins with run identity in provenance, without deciding cross-run combination. |
| 0140 | [Correction calculator](./01-0140-correction-calculator.md) | — | Planned (own align precedes) | Mongo obs source, Mongo forecast-run archive source | Per-source, per-parameter bias over paired forecast/observation history; correction remains gated on measured bias proving stable. |
| 0145 | [Persisting SQLite Store](./01-0145-persisting-store.md) | — | Planned (own align precedes) | retentive store | Retained Holdings survive process restart and are shared across concurrent processes on one deployment, behind the existing `Store` face. |
| 0155 | [Vendor budget governor](./01-0155-vendor-budget-governor.md) | — | Planned (own align precedes) | vendor-call ledger, second-provider fallback | A configured vendor budget stops spending past its limit; the request falls through to the backstop rather than failing. |
| 0165 | [REST surface](./01-0165-rest-surface.md) | — | Planned (own align + Edge record precede) | embedding surface (by decision, not mechanically) | Meteoscape is reachable over HTTP with the same weather semantics as MCP and the embedding surface. |
| 02-0170 | [Per-parameter selection](./02-0170-per-parameter-selection.md) | — | Planned | second-provider fallback | One response assembled from different winning providers by parameter. |
| 02-0190 | [Errors and partial success](./02-0190-error-taxonomy-partial-success.md) | — | Partial | provider nodata mask, request shaping, second-provider fallback | Per-parameter absence reasons and capable-but-faulting partial results. |
| 02-0195 | [Minimal resolution logging](./02-0195-minimal-resolution-logging.md) | — | Planned (own align precedes) | retentive store, second-provider fallback, per-parameter selection, errors and partial success | Operators can inspect structured producer-choice, fall-through, and Store hit/refill evidence without changing the weather data product. |
| 02-0200 | [Artifact conventions sweep](./02-0200-artifact-conventions-sweep.md) | Maint | Planned (own align precedes) | edge records | Canonical artifact-conventions registry: full doc roster classified (normative vs descriptive, granularity, lifecycle), skills slimmed to reference it. |

## Ticket numbering

Filenames are `RR-NNNN-slug.md` — release, position, name. The scheme itself (anatomy, position
stepping and insertion, subticket depth, citation by slug, what completion does to a number) is
owned by [TICKET-FORMAT.md § Numbering](../../.agents/skills/to-tickets/TICKET-FORMAT.md#numbering).
This section records only how it landed here.

- **Adopted 2026-08-02**, replacing the flat `NNN` scheme with its `002b`/`003a` letter suffixes and
  `m` maintenance prefix. All existing tickets were renumbered. The old ids are listed under
  [Legacy ids](#legacy-ids); documents written before that date cite them, and are left as written.
- **One global line across releases, 2026-08-08.** Before that date positions were read
  release-locally; the [delivery map](#delivery-map) has been the single cross-release order since.
- **RFCs took the owning ticket's basename, 2026-08-11**, retiring the independent
  `NNNN-YYYYMMDD-name` serial. The sixteen RFCs in [`rfc/done`](../rfc/done) predate it and keep
  their names; documents citing an RFC by number are left as written.
- **Release 01 is v1; the bee-line defines its boundary (2026-08-18).** The archive sources,
  correction work, persistent Store, embedded/REST deployment, and vendor-spend controls therefore
  carry `01`. Release 02 receives the former v1 tail: per-parameter selection, error/partial-success
  completion, minimal resolution logging, and the artifact-conventions sweep.

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
| 004 | [second-provider fallback](./done/01-0121-second-provider-fallback.md) |
| 005 | [per-parameter selection](./02-0170-per-parameter-selection.md) |
| 006 | [retentive store](./done/01-0115-retentive-store-freshness.md) |
| 007 | [off-grid homogenization](./done/01-0117-off-grid-homogenization.md) |
| 008 | [config and graceful degrade](./01-0123-config-secrets-degrade.md) |
| 009 | [errors and partial success](./02-0190-error-taxonomy-partial-success.md) |
| 010 | [unit-conversion catalogue](./01-0122-unit-conversion-edge.md) |
| 011 | [TWC provider](./done/01-0120-twc-provider.md) — Visual Crossing 2026-08-02 → 2026-08-08, TWC before and after |
| m1 | [type contract hygiene](./done/01-0050-type-contract-hygiene.md) |
| m2 | [dissolve node-`Countable`](./done/01-0070-dissolve-node-countable.md) |
| m3 | [provider parity checks](./done/01-0080-provider-parity-checks.md) |
| m4 | [snapped request mode](./done/01-0100-snapped-t-request-mode.md) |
| m5 | [edge records](./done/01-0090-edge-records.md) |
| m6 | [artifact conventions sweep](./02-0200-artifact-conventions-sweep.md) |

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
    logging](./02-0195-minimal-resolution-logging.md); the artifact-conventions maintenance sweep
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
2. **0119 → 011 → 004 → 010 → 008, in that order, because TWC is primary.** Selection flips with two
   integers; what follows is the cost of depending on a metered vendor. *(0119 inserted 2026-08-11:
   TWC's stage 0 capture showed its series starting at the next whole hour, which makes the refill
   gate unsatisfiable — the cache would never hit and every request would buy a call. That has to be
   true before a metered vendor goes on the default path.)* Fall-through (004) makes a
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

### The 2026-08-18 release-boundary correction

The sequence above remains useful, but its final boundary does not: **the bee-line itself is v1**.
The work named in steps 1–5 serves release 01. Step 6 is no longer a v1 tail; its four tickets move
to release 02. Ticket positions remain unchanged because position is global across releases.

## Decisions still owned by tickets

- [Supported Python embedding surface](./01-0125-supported-python-embedding.md): its own align selects
  the facade/lifecycle, public failure contract, request ergonomics, and `0.x` compatibility policy
  still open at concerns #39/#40; this queue pass deliberately selects none of them.
- [Minimal resolution logging](./02-0195-minimal-resolution-logging.md): its own align selects the
  event granularity, correlation, and sensitive-field policy; the structured trace sidecar and wider
  metrics surface remain deferred at concern #14.
- [m2](./done/01-0070-dissolve-node-countable.md): where a storeless materialized producer's read-back
  homogenization lives, and whether `EnumerableCapability` remains the "already materialized"
  discriminator → [#37](../concerns.md#37-storeless-materialized-producers-and-read-back-homogenization).
- [005](./02-0170-per-parameter-selection.md): choose the single-provider parameter used to demonstrate
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
- [010](./01-0122-unit-conversion-edge.md): build the shared conversion catalogue when a vendor exposes
  the first real multi-vendor spread. TWC reuses Open-Meteo's inline `km/h → m/s` edge, so the trigger
  remains unmet.
- [Vendor-call ledger](./01-0124-vendor-call-ledger.md): its own align selects what an entry is (one
  HTTP request vs one `Provider.project`), attribution granularity, the accounting period and where
  it is kept, the read-out channel, and whether failed calls count.
- [Persisting Store](./01-0145-persisting-store.md): its own align selects the **substrate** and the
  **key shape** — today's `_HoldingKey` carries X/Y as *indices into a lattice held elsewhere*, which
  is safe only while rows and lattice live and die together. Deliberately not chosen at the
  2026-08-10 align.
- [Vendor budget governor](./01-0155-vendor-budget-governor.md): its own align selects budget
  expression, headroom policy, caller visibility, and what exhaustion means with **no backstop**
  available — refuse, or serve past `expiration`? The second would change the MCP edge's staleness
  promise.
- [REST surface](./01-0165-rest-surface.md): its own align selects the resource model, the
  failure→status-code mapping (which may reopen #39's rendering, settled first at 0125), the
  Gateway's non-null caller policy, and serialization format.

## Maintenance rule

Update this page and the affected ticket header when delivery state changes. Other documentation may
say that a feature is **required by v1**, **deferred from v1**, or part of an accepted design, but should
link here instead of restating whether that feature is implemented or next.
