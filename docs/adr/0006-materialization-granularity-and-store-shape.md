---
status: accepted
---

# Materialization granularity & store shape

How a Provider's fetch becomes records, how those records are retained, and which geometry survives
where. This fixes the contract for any provider/store shape, including Z carriage through the data
plane. The capability/matching half is
[ADR-0004](./0004-producer-resolution-and-capability.md); the data model is
[ADR-0002](./0002-data-model.md).

## Decision

- **Materialization is grouped by native Domain.** A Provider emits **native records** —
  one co-domained `Coverage` per **set of parameters sharing a native Domain**. The grouping is
  **emergent from the Tap declarations and axis-agnostic**: Open-Meteo's scalar column partitions
  along Z (`{air_temperature, relative_humidity}` @ 2 m · `{wind_u, wind_v}` @ 10 m ·
  `{precipitation}` @ 0 m · `{cloud_cover}` @ `[0,TOA]`); a multi-cadence vendor partitions along T;
  a grid vendor whose parameters share one geometry degenerates to a single record — the flat case is
  the *lucky special case*, never the rule. This applies the existing "parameters that cannot share a
  Domain are separate Coverages" rule at the leaf and makes it load-bearing: a native record's Domain
  is **true native geometry**, so the per-parameter vertical facts survive materialization and
  persistence without an out-of-band tap-table lookup.

- **Questions are consumer-shaped; materializations are producer-shaped.** `project` receives **one
  Selection** (one Domain + a parameter set) — the caller never pre-partitions, because only the
  producer knows its native layout. The partition is a property of the **answer**. Co-domain is an
  invariant of the **exchange record** (one `Coverage`), never of a store or of a fetch.

- **The partition reaches the store because the question asks `ANY`.** A Source asks its
  Provider **once** — asking per parameter group would multiply vendor fetches for data one call
  returns — with `ANY` on the axes its Holding spans wholly. By shape-correspondence
  ([ADR-0001](./0001-manifold-algebra-and-composition.md)) that answer is legitimately
  **multi-domain**: temperature at 2 m beside wind at 10 m. This is what preserves native geometry
  through the boundary; a fully-enumerable question would force a flattened answer and destroy the
  native cells before the store could key Holdings by them. The **store** slices that answer per
  parameter, because only it holds both
  halves of each Holding `Selection` — `X/Y`+`T` from its private lattice, the native cell from the
  answer. `assimilate` therefore consumes **the answer** and samples the Holdings it retains, rather
  than being handed one pre-sliced record by a caller that would have to know the store's lattice.

- **The store is Holding-granular, never co-domained.** A `Store` holds **per-parameter Holdings**
  (`(parameter, per-axis cells, window)`); `assimilate` consumes the producer's answer and samples it
  into Holdings, replacing each atomically. Its lattices are **per axis** (and, where native cadences differ,
  per parameter family) and **private** — consumed by `quantize`, the holdings read, and read-back;
  never exposed as a node `domain`. Implementations vary by substrate and persistence behind this one
  write/read face: the store's whole public surface is the Manifold contract + `Writable` +
  `quantize`. Its `project` is the **holdings query**, total over raw asks — the store translates
  the ask onto its private boxes internally, and the Holdings come back as records carrying
  their own domains and provenance; asked-but-unheld parameters are **omitted** and an empty
  answer is normal (a cold store is a state, not an error — the Arbiter's omission precedent, not
  a `Coverage`'s raise). `quantize`'s one public job is authoring the **refill fetch-order**: the
  ask handed to the child must say `ANY` on the axes a box spans (that ask shape is what licenses
  the native multi-domain answer, above), and only the store knows its boxes. The contract is **clockless and freshness-blind**: provenance
  (`expiration` included) travels as data, and what *fresh* means is the reader's policy — the live
  `Reservoir` gates on it, an archive reader serves deliberately stale history through the same
  face. A substrate may still read a clock for its **own housekeeping** (the in-memory
  store evicts past `retention_interval`); that is a property of the substrate, not of the contract,
  which is why an archive substrate takes no clock at all. Its `capability` **narrates holdings**: honest parameter membership, and a
  per-parameter reach that truncates plural holdings to the latest-assimilated Holding's geometry —
  safe because `reach` is composition-and-narration over *producers* and a store is never composed
  ([#47](../concerns.md#47-a-stores-capability-narrates-plural-holdings-truncate-to-one-reach)).

- **`quantize` is per-axis: snap where a lattice is declared, identity where none is, `ANY` where the
  Holding spans the axis wholly.** Each axis with a declared lattice resolves to its **containing cell**
  and is emitted as that cell's **tick** — a pinned point, never the cell's span: the
  coalescing that makes a Holding shared lives in the **key**, while the ask stays a point, because a
  span member would relabel a point-measured value as valid across the cell and would graze the
  neighbouring cell at the next store hop (a tick, by contrast, is a fixed point of the fold). An
  axis **without** a declared lattice **passes through unchanged**,
  its cell becoming part of the Holding key (the **best-view** store's Z — product Holdings keyed by the
  request's vantage cell); an axis the Holding spans **entirely**, or whose native cell only the answer
  can supply (a **Source** store's Z), is asked as **`ANY`** — the same widening carried to its limit,
  answered at the producer's native extent ([ADR-0002](./0002-data-model.md)). **Which axes a store
  defers is bounded by position and decided by the producer's declared geometry**: above the fact→product
  boundary below — the best-view store, and a stored Calculator's, whose child likewise answers
  product-shaped views — only T is deferrable, because native cells are gone by relabel before an
  answer arrives there. At a **Source**, deferral is a fact of the provider's **shape**: the
  point-timeline shape yields `{T, Z}` (its heights only the answer can supply), while a
  volumetric provider declaring a real Z lattice makes Z snap like any other axis — same rule, no
  vertical special case. v1 ships one shape, so the source set lives as the wiring constant; a
  second shape moves it into the provider manifest beside taps and cadence.
  "Quantize preserves Z semantics" is thus by construction.

- **The fact→product boundary sits at the Source's read-back.** One vertical fact travels:
  Tap declaration → capability admission (`serves`) → native record Domain → Source-store Holding key →
  read-back match. The **single relabel** (native cells → the request's Z cell, value-passthrough for
  a sample inside the window or a statistic cell containing it) happens in the Source's read-back —
  **below the Arbiter**, forced structurally: the Arbiter's per-parameter assembly is positional and
  can only fold answers already conformable on one Domain. Above the boundary everything is
  **product**: the best-view store holds Holdings keyed by the *request's* cells (answers, not facts);
  a different Z question misses there and falls through to the Sources, where native Holdings answer by
  re-matching. Holding reuse across differing vantage windows is
  [concern #25](../concerns.md#25-root-store-holding-reuse-across-vantage-windows).

- **One cell-matching arithmetic, three consumers.** *"Does a Z cell at hand answer the requested
  Z?"* (membership for a point cell, inclusion for a span — the quantifier rule,
  [ADR-0004](./0004-producer-resolution-and-capability.md)) is cell-level geometry, not
  capability-private: capability admission checks **declared** cells, the store's holdings read
  checks **held Holding** cells, read-back selects the cells that feed the request. One helper, hidden
  behind `matches` / the store's `project` — no second public verb.

- **Nodes are not `Countable`; `domain` lives only on the Coverage.** A node's public shape is its
  **capability** (footprint — a Source admits uncached-but-in-footprint requests precisely because
  admission reads the forwarded footprint, not store contents); its lattice is store-private. The two
  jobs the node facet did move to their owners: the quantize/retention target is internal to the
  `Store`, provisioned from the configured **`StoreSpec`** alone — no provider hands a lattice
  anywhere, and no build-time "construction face" exists for one. A provider whose every parameter sits on one
  enumerable domain (an `EnumerableCapability`) *is* an already-materialized dataset and wires
  **storeless** — a bare `Producer`, no `Reservoir`, no store — because wrapping it would mirror
  data that is already local; the `SourceBinder` enforces the invariant loudly in both directions
  (a configured store on a materialized offering, like a missing store on a non-materialized one, is
  a `CompositionError`). A `Coverage` keeps `domain` — the positional
  contract for `ParameterData`, derived from `capability.domain`, not stored twice. Snapped resolution stays behavioural: the resolving node supplies its own lattice — a storing
  `Reservoir` quantizes, a storeless leaf resolves onto its private vendor lattice — and no caller
  reads either.

## Why

- **Losslessness where it matters:** a stored Holding carries the geometry it was measured on. Flattened
  records would need `SourceKey` → the then-active Tap table to recover heights — version-fragile against
  tap changes and useless for cross-provider reconciliation or verification.
- **The Arbiter stays a pure fold:** admission on footprint, reads on the handed shape, positional
  assembly. Geometry work lives only in nodes that own data.
- **Store heterogeneity without contract leaks:** with the lattice private and Holdings per-parameter,
  stores may differ by substrate, persistence, and lattice structure behind one face; the
  single-`EnumerableDomain` node facet was the only thing forcing them to look alike.
- **Each Reservoir level does one downward reshape (quantize before asking — so `assimilate` is an
  identity write) and one upward reshape (read-back after storing).** Nothing is processed twice.

## Considered options

- **Flatten per fetch** (one Coverage, shared Z tick; heights only in the Tap table). Rejected: lossy
  on the data plane (above); the store cannot answer availability honestly. Native multi-domain
  answers instead land in the store and read-back relabels them.
- **Per-parameter Domains inside one Coverage.** Rejected (again): breaks closed projection,
  positional `ParameterData`, and every composite — the standing decline holds.
- **Multi-level sparse Z axis** (union of heights, `present` masks off-level). Rejected: waste;
  conflates *no data* with *not applicable*; the request never wants those ticks.
- **Native Z as a descriptor side-channel** (per-parameter cell beside the Domain). Rejected: two
  homes for geometry; every consumer must know which to trust.
- **Children answer native; the Arbiter homogenizes.** Rejected: gives the substrate-less node
  kernels and makes every reconciler geometry-aware.
- **A forced co-domained store lattice (Z always snapped).** Rejected: requires inventing a fake Z
  lattice and rewrites the cells that admission and read-back need intact.
- **Keeping node-`Countable` but loosening `domain` to per-axis lattices.** Rejected: no consumer
  remains (nothing reads a node lattice — the Weaver provisions stores from the `StoreSpec`) —
  loosening a vestigial face is worse than deleting it.
