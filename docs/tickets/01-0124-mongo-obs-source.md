# Mongo obs source

- **Status:** Ready (split) — aligned 2026-08-21 against the live collector database; the
  [#45](../concerns.md#45-the-collector-schema-is-a-contract-meteoscape-depends-on-but-does-not-own)
  mitigations and the observation-source semantics are resolved inline below. This ticket is the
  decision record and the union of criteria; delivery is the
  [scatter substrate](./done/01-0124.0010-scatter-substrate.md),
  [collector transport and decode](./01-0124.0020-collector-transport-and-decode.md), and
  [station observation serving](./01-0124.0030-station-observation-serving.md) slices — with
  [one timeline algebra, two geometries](./done/01-0114-timeline-shape-generalization.md) carved out
  ahead of them, since the producer joins a family rather than forking one. The align's impact trace also
  found the dominance fold refuses obs+forecast composition over a shared parameter — that work is
  deliberately outside, at
  [obs+forecast reach composition](./01-0137-obs-forecast-reach-composition.md).
- **Depends on:** [config and secrets](./done/01-0123-config-secrets-degrade.md) (the connection
  string uses the generic `SecretSlot` mechanism),
  [composition lifetime](./done/01-0116-composition-lifetime.md) (somewhere to hold and release the
  connection this source keeps between requests)
- **Blocks:** [Mongo forecast-run archive source](./01-0134-forecast-run-archive-source.md) (shares
  the transport and registry), [correction calculator](./01-0140-correction-calculator.md).
- **Outcome:** Hourly station observations from the operator's Collector database served through
  the projection algebra as a read-only private source, with per-parameter provenance naming the
  observation origin.

## Parent

The release-01 bee-line makes local-station validation part of v1
([delivery status](./README.md)). Its durable product context is the
[local-station validation and bias-correction roadmap](../product-roadmap.md#priority-candidate-after-v1-local-station-validation-and-bias-correction)
and concern [#45](../concerns.md#45-the-collector-schema-is-a-contract-meteoscape-depends-on-but-does-not-own).

## What to build

The first private source ([glossary → Collector](../glossary.md)): a leaf projecting the operator's
collector MongoDB **read-only** — the first non-HTTP transport, so the acquire/decode seam split
inside "provider" happens here, not by pre-design. It maps the collector's two observation schemas
(the regional station-network documents carrying `raw` and `method`; legacy `ibm_hod`) onto
canonical parameters, reads the `stations` registry for capability, and serves past-facing windows:
the declared T upper rides the clock, and the served overlap ends at the newest retained
observation, not at a forecast horizon.

This source lands through the existing internal composition path and is tested through `Gateway`.
It exposes no supported imports and declares no pilot composition root; the
[embedding surface](./01-0125-supported-python-embedding.md) follows with this source's lifecycle,
construction, and failure evidence in hand.

**Resolved (2026-08-21 align): the source wires storeless.** Neither of the store's policy guards
applies — the collector DB is the operator's own, unmetered, and already persistent, so a `Store` in
front of it would mirror a local dataset uselessly
([#37](../concerns.md#37-storeless-materialized-producers-and-read-back-homogenization), widened
2026-08-19 for exactly this shape: storeless is profile policy, not a materialization corollary).
Consequence, delivered by the [scatter substrate](./done/01-0124.0010-scatter-substrate.md): the
`store is None ⇔ materialized` biconditional is gone — store presence is profile policy, and
`wire_source` reads it as *storeless*, never as *materialized*. The mirror-waste refusal (a store
on a materialized offering) **stays an error**, its loosening owned by #37's own trigger; the
metered-uncached refusal waits on a fact to read — **metered is a provider property**
(2026-08-21 review), so `ProviderManifest.metered` is minted at the
[ledger](./01-0130-vendor-call-ledger.md) and the refusal returns there, the substrate leaving a
TODO-marked gap in the binder.

**Resolved (2026-08-21 align): identity and provenance.** The impl id is **`collector-obs`** (the
glossary's *Collector* role, not a commercial name), one v1 offering **`stations`** — so
`SourceKey` = `collector-obs:stations`, and the connection string reads at
`METEOSCAPE_COLLECTOR_OBS_URI` per [0123](./done/01-0123-config-secrets-degrade.md). There are no
per-station `SourceKey`s. The station is named in-band through
[ADR-0003](../adr/0003-provenance-and-origin.md)'s **origin-identity** amendment (minted at this
align): `AtomicOrigin` gains optional `authority` / `process` / `unit`, and for this source
authority = the network (`agrometeo` / `ibm_hod`), process = the method, **unit = the station's
name or the network's own station id** — the instance's meaningful identity in the authority's
namespace, never the coordinate-derived registry key (useless: the requester already holds the
coordinates). **Identity reaches the requester before any request** through the amendment's
declaration side: `Capability.origins(parameter)` publishes (sub-domain, origin) pairs — each
station's coordinates together with its identity — which is the request-forming discovery channel.
The declaration reads the registry snapshot; the served stamp is authored at fetch (authority and
process from the documents themselves, unit from the addressing record) and normally equals its
declaration — divergence is visible evidence. Observation planes are run-free with `expiration`
effectively ∞ — already ADR-0003's word; this source is its first implementer.

~~**Resolved (2026-08-21 align): shape reuse, per the architecture's own rule** ("a new producer of a
known shape adds a Probe; a new geometry adds a wrapper"): a **sibling wrapper** beside
`TimelineProvider` owns the scatter footprint, past-facing timing, and observation provenance.~~
**Superseded 2026-08-22 (serving plan): a family member, not a sibling.** Measuring the sibling
found ~160 of `TimelineProvider`'s ~243 lines identical for a station producer, so the algebra
became a family base and the rolling behaviour `RollingTimeline`
([one timeline algebra](./done/01-0114-timeline-shape-generalization.md)); the observation producer
joins that family, answering only what differs. The `TimelineProbe` protocol (measured
transport-neutral) and the `TapTable`/interpret machinery are still reused verbatim, with the Mongo
probe implementing `retrieve()` against the held client.

New semantics this shape introduces (decided at this ticket's align, not before):

- ~~**Past-facing capability and freshness** — what `expiration` means for an observation (it does
  not age like a model run), and how collection recency (`state.last_observation_time`) narrates.~~
  **Resolved (2026-08-21 align): observations do not expire.** The entire archive is in reach —
  T is declared **per parameter as one window**, `[archive floor, clock.now()]`; each station's
  true span is answered at serve time as the overlap (the live data staggers: source types end at
  different times, one registered station holds nothing — per-site windows are deliberately *not*
  declared; no mechanism carries them and scale forbids per-site scans).
  Provenance stamps a named never-expires sentinel, which composes through ADR-0003's
  min-over-parents blend so a corrected value's freshness follows its forecast parent for free.
  Recency narration is per source type: the `state` doc where it reports (`agrometeo`), per-collection
  `max(time)` where it does not (`ibm_hod`).
- ~~**Station-located geometry** — observations exist at *their* stations, not at the request's
  point; how a request point resolves against the registry (exact station key vs the off-grid
  homogenization path) is this align's to decide.~~
  **Resolved (2026-08-21 align): exact-station admission, no epsilon.** A request point is served
  only when it coincides with a registered station; anywhere else declines as capability and falls
  through to a forecast producer. The reach is a new domain form, **`ScatterDomain`** — a plain
  `Domain` (not `EnumerableDomain`; conformance waits for the first scatter-shaped Coverage and its
  sampler widening) holding **paired X/Y points** matched jointly, plus T/Z axes. Geometry only —
  no `Site` type, no labels in the domain: station identity is provenance's, and discovery rides
  [ADR-0003](../adr/0003-provenance-and-origin.md)'s declared provenance —
  `Capability.origins(parameter)` pairs each station's coordinates with its origin before any
  request; edge narration renders that when a surface serves observations. Per-parameter site sets differ in
  production (agrometeo carries no precipitation; ibm_hod no dewpoint), so reaches stay in
  `GranularCapability`. Correction later narrows to stations automatically —
  `DerivedCapability.serves` requires all inputs servable — and spatial widening is a
  homogenization layer above it ([#37](../concerns.md#37-storeless-materialized-producers-and-read-back-homogenization)
  stays dormant). The MCP edge's `_t_extent` fold raises on non-separable reaches — the RFC decides
  extent-projection vs fold widening.
- **The schema contract** — #45's mitigations become concrete here: pinned integration fixtures
  sampled from real documents are the contract test; the collector owns the schema, this source
  adapts. **Measured against the live database (2026-08-21 align)**, correcting #45's sketch:
  collections are **per-station** with coordinates in the collection name (`obs_<lat>_<lon>`);
  the `stations` registry carries `id` (`"lat_lon"`), `name`, `elevation`, `active`, `managed`,
  and `observation.source`; the two schemas share one collection layout discriminated by the
  per-document `source` field (`agrometeo`: `raw` + `method` + `observed_at` + parsed fields;
  `ibm_hod`: flat) and the split crosses regions. Times are naive-UTC BSON datetimes, hourly
  snapped. **Units arrive canonical** (`temp2m_c`→degC, `rh2m`→percent, `wvel_ms`→m/s,
  `wdir_deg`→degree, `rain1h_mm`→mm) — no unit spread, so
  [0129](./01-0129-unit-conversion-edge.md)'s trigger does not fire. Wind arrives as
  speed+direction and decodes to `wind_u`/`wind_v` through the existing joint-tap machinery.
  Tick-convention fact for [#48](../concerns.md#48-a-tap-cannot-declare-where-its-value-sits-relative-to-the-tick):
  agrometeo's `time: HH:00` document carries a reading measured ~HH:30 (`observed_at`), floor-labelled
  — a bias-relevant 30-minute offset against hour-labelled forecast instants. `temp_dew_c` is
  offered but has no canonical parameter; adding one is [parameters.md](../parameters.md)'s
  decision, out of scope here. Still open from #45: the ownership statement's home and whether a
  collector-side schema version marker is cheap.
- ~~**Connection lifetime** — a Mongo client is a pool held across requests, not the per-call client
  every HTTP producer builds today. This align decides the seam;
  [composition lifetime](./done/01-0116-composition-lifetime.md) builds it first and owns its criteria, so
  the shape is chosen here rather than invented inside this source's implementation.~~
  **Resolved (2026-08-21 align): the seam fits, and its first holder holds two resource kinds.**
  The pooled `AsyncMongoClient` is held by the source's transport tier and surfaced through the
  structural `Closeable` facet (PyMongo's async `close()` behind a trivial `aclose`; nothing imports
  from `nodes/`), constructed sync in `compose()`, released LIFO through `Gateway.aclose()`.
  The capability's station points and per-station parameters load from a startup registry read and are
  **periodically re-read** (interval an offering setting), so a station added to the collector
  appears without restart. The re-read runs **on the serving path**: a request served by this
  source past the interval re-reads the registry first — no background execution context exists or
  is invented; an idle source stays stale until used, accepted. Feasibility is bounded by the
  grouping seam: **one offering hosts one bounded station group**
  ([#50](../concerns.md#50-observation-network-scale-station-grouping-and-discovery)); v1 declares
  a single offering over the collector's current network.
  Admission needs no I/O because the declared domain
  itself answers it — per-parameter `ScatterDomain`s whose T upper **rides the clock**
  (`[archive_start, clock.now()]`, the past-facing mirror of `RollingAxis`); serve-time reads the
  actual documents and returns the true overlap, and an ask the overlap leaves empty fails as
  `capability-mismatch`, never empty. **Holes are nodata (2026-08-21 align):** a missing hour inside
  the served overlap, or a null field inside a document, serves as nodata on the hourly lattice
  (the [nodata-mask](./done/01-0030.0020-provider-nodata-mask.md) precedent) — observations are
  never padded or interpolated; only an empty overlap declines. Declared-vs-actual accuracy
  pressure stays owned by
  [#29](../concerns.md#29-narrated-reach-what-a-profile-promises); the collector's incomplete span
  bookkeeping by [#45](../concerns.md#45-the-collector-schema-is-a-contract-meteoscape-depends-on-but-does-not-own).

**Out of scope:** the forecast collections
([forecast-run archive source](./01-0134-forecast-run-archive-source.md)); any live station
*endpoint* — permanently embedder-plug-in territory per #45 and
[#26](../concerns.md#26-provider--calculator-plugin-scaffolding); any write path to the collector
database.

## Acceptance criteria

The end-state union — each behavior box lives in exactly one child:

- [x] The [scatter substrate](./done/01-0124.0010-scatter-substrate.md) lands (declared contracts,
      fake-tested) — 2026-08-21.
- [ ] [Collector transport and decode](./01-0124.0020-collector-transport-and-decode.md) lands (the
      held connection and the pinned schema).
- [ ] [Station observation serving](./01-0124.0030-station-observation-serving.md) lands (the
      producer end to end in a composition of its own).
- [x] The align's resolutions (obs freshness semantics, station-located geometry resolution, #45
      mitigations) are recorded in their durable homes before implementation starts —
      2026-08-21, this ticket plus [ADR-0003](../adr/0003-provenance-and-origin.md),
      [#29](../concerns.md#29-narrated-reach-what-a-profile-promises)/[#45](../concerns.md#45-the-collector-schema-is-a-contract-meteoscape-depends-on-but-does-not-own)/[#50](../concerns.md#50-observation-network-scale-station-grouping-and-discovery),
      and the [glossary](../glossary.md).

## Parent scope addressed

- Roadmap "Priority candidate after v1": *project the operator's Collector database (station
  registry + hourly observations) as an observation source.*
