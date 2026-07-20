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

- **Materialization is grouped by native Domain.** `Normalizer.normalize` emits **native records** —
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
  returns — with `ANY` on the axes its unit spans wholly. By shape-correspondence
  ([ADR-0001](./0001-manifold-algebra-and-composition.md)) that answer is legitimately
  **multi-domain**: temperature at 2 m beside wind at 10 m. This is what preserves native geometry
  through the boundary; a fully-enumerable question would force a flattened answer and destroy the
  native cells before the store could key units by them. The **store** slices that answer per
  parameter, because only it holds both
  halves of each unit `Selection` — `X/Y`+`T` from its private lattice, the native cell from the
  answer. `assimilate` therefore consumes **the answer** and samples the units it retains, rather than
  being handed one pre-sliced record by a caller that would have to know the store's lattice. The exact
  slicing API remains provisional until a retentive Store implements this contract.

- **The store is unit-granular, never co-domained.** A `Store` holds **per-parameter units**
  (`(parameter, per-axis cells, window)`); `assimilate` consumes the producer's answer and samples it
  into units, replacing each atomically. Its lattices are **per axis** (and, where native cadences differ,
  per parameter family) and **private** — consumed by `quantize`, the per-unit report, and read-back;
  never exposed as a node `domain`. Implementations vary by substrate and persistence behind this one
  write/report/read face.

- **`quantize` is per-axis: snap where a lattice is declared, identity where none is, `ANY` where the
  unit spans the axis wholly.** Each axis with a declared lattice snaps onto it and widens outward to
  whole units (extent ≥ request); an axis **without** a declared lattice (for example, Z) **passes
  through unchanged**, its cell becoming part of the unit key; an axis the unit spans **entirely** is
  asked as **`ANY`** — the same widening carried to its limit, answered at the producer's native
  extent ([ADR-0002](./0002-data-model.md)). A volumetric provider may declare a real Z lattice, making Z snap like any other axis —
  same rule, no vertical special case. "Quantize preserves Z semantics" is thus by construction.

- **The fact→product boundary sits at the Source's read-back.** One vertical fact travels:
  Tap declaration → capability admission (`serves`) → native record Domain → Source-store unit key →
  read-back match. The **single relabel** (native cells → the request's Z cell, value-passthrough for
  a sample inside the window or a statistic cell containing it) happens in the Source's read-back —
  **below the Arbiter**, forced structurally: the Arbiter's per-parameter assembly is positional and
  can only fold answers already conformable on one Domain. Above the boundary everything is
  **product**: the best-view store holds units keyed by the *request's* cells (answers, not facts);
  a different Z question misses there and falls through to the Sources, where native units answer by
  re-matching. Unit reuse across differing vantage windows is
  [concern #25](../concerns.md#25-root-store-unit-reuse-across-vantage-windows).

- **One cell-matching arithmetic, three consumers.** *"Does a Z cell at hand answer the requested
  Z?"* (membership for a point cell, inclusion for a span — the quantifier rule,
  [ADR-0004](./0004-producer-resolution-and-capability.md)) is cell-level geometry, not
  capability-private: capability admission checks **declared** cells, the store report checks
  **held unit** cells, read-back selects the cells that feed the request. One helper, hidden behind
  `matches` / the report — no second public verb.

- **Nodes are not `Countable`; `domain` lives only on the Coverage.** A node's public shape is its
  **capability** (footprint — a Source admits uncached-but-in-footprint requests precisely because
  admission reads the forwarded footprint, not store contents); its lattice is store-private. The two
  jobs the node facet did move to their owners: the quantize/retention target is internal to the
  `Store`; a provider-exact lattice is a **build-time declaration** handed to the `StoreFactory` at
  weave (construction face, not a request-path facet). A `Coverage` keeps `domain` — the positional
  contract for `ParameterData`, derived from `capability.domain`, not stored twice. "Snapped resolves
  at a storing `Reservoir`" stays behavioural: the node *has* a store and quantizes; no caller reads
  the lattice.

## Why

- **Losslessness where it matters:** a stored unit carries the geometry it was measured on. Flattened
  records would need `SourceKey` → the then-active Tap table to recover heights — version-fragile against
  tap changes and useless for cross-provider reconciliation or verification.
- **The Arbiter stays a pure fold:** admission on footprint, reads on the handed shape, positional
  assembly. Geometry work lives only in nodes that own data.
- **Store heterogeneity without contract leaks:** with the lattice private and units per-parameter,
  stores may differ by substrate, persistence, and lattice structure behind one face; the
  single-`EnumerableDomain` node facet was the only thing forcing them to look alike.
- **Each Reservoir level does one downward reshape (quantize before asking — so `assimilate` is an
  identity write) and one upward reshape (read-back after storing).** Nothing is processed twice.

## Considered options

- **Flatten per fetch** (one Coverage, shared Z tick; heights only in the Tap table). Rejected: lossy
  on the data plane (above); the store cannot answer availability honestly.
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
  remains (the Weaver read moves to the construction face; nothing else reads it) — loosening a
  vestigial face is worse than deleting it.
