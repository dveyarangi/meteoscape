# Meteoscape

A manifold-based **Coverage-resolution engine** that resolves a request for a field into one normalized,
provenance-stamped **Coverage** under a stated policy/objective. v1 ships one objective — the **best view**
(best-obtainable source + fallback) over timeline provider data — surfaced via MCP (other surfaces later).

> Lookup only: each entry defines **what a term is**. Behaviour, rationale, and mechanics live in
> [`architecture.md`](./architecture.md) and the [ADRs](./adr); follow the `→` pointers.

## Language

### Domains

**Domain**:
A **coordinate set** over the 4 axes (the *where*) — **continuous** (a region) or **enumerable** (a lattice / point set). → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: Bounds, extent, region

**EnumerableDomain**:
The **enumerable case of a Domain** — an indexable set of coordinate positions, **regular lattice** or **irregular point set** (cardinality-1 is a single coordinate); enumeration (`enumerate` / index / `len`) lives here, not on the base `Domain`. Only the regular case can be a `quantize` target. → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: Geometry (suggests GIS vector shapes), Lattice (the regular subset only — a point set may be irregular)

**Axis**:
One axis of a **`Separable`** Domain — its ordered sequence of `Cell`s, positional to a parameter's values. A **`RegularAxis`** is the uniform case (the only snappable one), defined parametrically rather than enumerating each cell. → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: Dimension, Coordinate array

**Cell**:
One position on an `Axis` — a representative **coordinate** with optional **bounds**; no bounds ⇒ an **instant / point**. The unit a parameter's value aligns to; coordinate and bounds are independent (the coordinate sits *within* the bounds by convention, not by definition). → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: Tick (the coordinate alone), Pixel

**Bounds**:
A `Cell`'s span on one axis (its `Interval`); absent ⇒ the coordinate is an **instant / point**. The geometry an extensive or windowed parameter reads as its **extent** — the aggregation / integration window. → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: Range (collides with a Coverage's `ranges`), Extent (the parameter-side window that *rides on* these bounds), span

**Interpolable axis**:
An axis whose values may be **synthesized between samples** (homogenization) — the 3 spatial axes and `valid_time`. → [ADR-0002](./adr/0002-data-model.md).

**Categorical key**:
A discrete dimension you **select / group / iterate**, never interpolate — the **collection-layer** mechanism for `issue_time` archives and future **ensemble / scenario** keys. **Not** a core field-Domain axis (the v1 `Domain`'s 4 axes are all interpolable). → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: Categorical axis (it is not a Domain axis), Label axis, index axis

### Data

**Coverage**:
A **field sampled onto an enumerable Domain** — the shape-agnostic data exchange unit; itself a Manifold (`Coverage <: Manifold`), equivalently a Selection filled with data. → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: DataBlock, single-parameter Coverage

**Field**:
A Manifold (or projected view) **before sampling** — the general result of `project`; a Coverage is its sampled (`Countable`) case. → [ADR-0001](./adr/0001-manifold-algebra-and-composition.md).
_Avoid_: Coverage (the sampled leaf), Parameter

**Timeline**:
A Coverage whose domain is a time axis (fixed location, varying `valid_time`); each `ParameterData` is single-origin, with its run identity stamped as `issue_time` in its provenance. → [architecture.md](./architecture.md#canonical-data-model).

**Grid**:
A Coverage whose domain is a spatial axis (fixed `valid_time`, varying location); each `ParameterData` carries origin metadata aligned to its geometry. → [architecture.md](./architecture.md#canonical-data-model).

**Parameter**:
A single weather variable (e.g. temperature) that identifies a **`ParameterData`** within a Coverage — **not** a coordinate axis. → [architecture.md](./architecture.md#canonical-data-model).
_Avoid_: Variable, field, metric

**ParameterData**:
One parameter's **materialized data slice** in a Coverage (`values`, `present` mask, `unit`, `aggregation`, provenance), positional to the Domain. One per parameter; not itself a Manifold. → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: Range (reads as an interval — collides with a `Cell`'s `bounds`), DataBlock, slice

**ParameterDef**:
The **canonical definition** of a parameter (`id`, `quantity`, `kind`, `canonical_unit`, `aggregation`) that a `ParameterData` clones from; fetched from the **Parameter table**. → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: Parameter (the identifier), schema

**Parameter table**:
The injected **lookup of `ParameterDef`s** (keyed by `ParameterId`) that producers and the edge resolve canonical parameter facts from; a swappable interface (v1 ships a static one). → [architecture.md](./architecture.md#config-registry-weaver).
_Avoid_: Registry (the provider leaf-factory, and the Derivation registry), Catalogue

**CellAggregation**:
The **window statistic** a value summarizes its cell with — `point | max | min | mean`; *dimension-preserving*; fixed by parameter identity (lives on `ParameterDef`). The calculus axis (accumulation) is the quantity **kind**, not a value here. → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: Operator (too generic), sum (that is integration — a quantity kind), cell-method (aggregation × extent, not the verb alone)

**Quantity**:
The **identity root** of a parameter — a physical field carrying a **kind** (`intensive` / `extensive`, i.e. extent-scaling) that sets its valid aggregations and conversion edges; rain-intensity (`intensive` rate) and precipitation (`extensive` integral) are *distinct* quantities, related by integration. → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: Parameter (that is the functional `(quantity, aggregation)`), variable

**Kind**:
A quantity's relationship to a cell's temporal extent — **intensive** (instantaneous, extent-independent: temperature, rain-rate; window statistics apply) or **extensive** (additive, the integral over the extent: precipitation; extent required). → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: state / rate / accumulation (those conflate identity with the integration edge)

**Functional**:
A **requestable parameter** = `agg(quantity)` — the materialized key `(quantity, aggregation)`; extent is *not* in it (it rides the Domain's `valid_time` `Cell` `bounds`). Aliases like `precip_3h` are surface sugar desugaring to functional + Domain cells. → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: Alias (the sugar), parameter name (ambiguous)

**Nodata**:
A **cell-level data gap** — a producer succeeded but has no value at a cell (`present[i] = False`); **data, not a fault**. → [architecture.md](./architecture.md#failure-nodata-and-availability).
_Avoid_: Missing (ambiguous with an absent parameter), failure, error, null

**ProvenanceField**:
The **geometry-aligned provenance attribute** on a `ParameterData` — `Uniform` or `PerPoint` behind one interface with an **O(1) `summary`** handle. → [ADR-0003](./adr/0003-provenance-and-origin.md).
_Avoid_: provenance array, per-point provenance (the `PerPoint` case only)

**Provenance**:
The **per-parameter** origin metadata on a `ParameterData` (origin, fetched-at, native resolution, `expiration`); carried as a `ProvenanceField`. → [ADR-0003](./adr/0003-provenance-and-origin.md).
_Avoid_: Lineage (part of a *synthetic* Origin)

**Origin**:
What a `ParameterData`'s values derive from — **atomic** (a single Provider fetch) or **synthetic** (derived from multiple parent provenances, its **lineage**). → [ADR-0003](./adr/0003-provenance-and-origin.md).
_Avoid_: Source (the Manifold)

**Valid time**:
The time a value describes (what the weather *is* at). → [architecture.md](./architecture.md#canonical-data-model).

**Issue time**:
Which forecast **issuance** a value came from — a **provenance stamp (run identity)** on the atomic `Origin`, **not** a Domain axis; the basis of freshness (run currency). Cross-run lives in the collection / reconciler seam; precise meaning is [concern #4](./concerns.md#4-issue_time-definition). → [ADR-0003](./adr/0003-provenance-and-origin.md).
_Avoid_: Reference time, run time; issue_time *axis* (it is a stamp, not an axis)

**Quality**:
How good a source's data is for a parameter — the basis for the Arbiter's selection. → [architecture.md](./architecture.md#arbiter).

**Cadence**:
How often a **Provider** refreshes — read at fetch to author each `ParameterData`'s `expiration`. → [architecture.md](./architecture.md#provider-leaf-manifold).

**Consensus**:
An Arbiter **`reconciler`** that **blends** overlapping contributors instead of picking one. → [ADR-0004](./adr/0004-producer-resolution-and-capability.md).

### Outcomes

**Capability-mismatch**:
A requested parameter that **no producer declares** — caught at the capability filter. One of the three error-taxonomy categories. → [architecture.md](./architecture.md#failure-nodata-and-availability).
_Avoid_: Not-found, unsupported (vague), nodata (that is successful data)

**Runtime-failure**:
A producer that **couldn't produce** (5xx / timeout / malformed) — an exception that triggers fall-through. One of the three error-taxonomy categories. → [architecture.md](./architecture.md#failure-nodata-and-availability).
_Avoid_: Error (the supertype), nodata, outage

**Partial success**:
The normal outcome: the Coverage holds the **producible subset**; an unserved parameter is **absent**, its reason derived at the edge. → [architecture.md](./architecture.md#failure-nodata-and-availability).
_Avoid_: Degraded, best-effort

### Requests

**Selection**:
The **one request type**: a `Domain` + parameters; the Domain's **shape** **is** the mode. → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: Need

**Selection mode**:
Which kind of Domain a Selection carries — **Continuous** / **Snapped** / **Enumerable** (region / snapped / exact). → [ADR-0002](./adr/0002-data-model.md).

**Canonical lattice**:
The enumerable grid a `Reservoir` declares (via its `Store`) that `quantize` snaps to — **per-`Countable`-node** (provider-exact where a vendor declares one, a configured guess otherwise). → [architecture.md](./architecture.md#store--one-type-several-positions).

**Quantize**:
The `Store`-side operation that maps a Selection to the store's **storable shape**: it snaps the requested axes (3 spatial + `valid_time`) onto the declared grid **and widens the extent outward to whole assimilable units** (v1: a parameter's timeline at a spatial cell), so the result **encloses** the request (extent ≥ request) and `assimilate` only ever replaces whole units. Resolving stored cells back onto the requested coordinates is **Homogenization** (read-back), not quantize. → [architecture.md](./architecture.md#reservoir).
_Avoid_: snap (only quantize's grid-alignment half), align / round (align is homogenization)

### Roles

**Gateway**:
The surface-neutral **caller-policy boundary** (authz, rate-limit, quota) in front of the best-view Manifold; not a Manifold itself. → [architecture.md](./architecture.md#gateway--caller-policy-boundary).
_Avoid_: Orchestrator, Translator

**Manifold**:
The single recursive abstraction every component below the Gateway is built from — a projectable space with one closed operation, `project(selection) -> Manifold`. → [ADR-0001](./adr/0001-manifold-algebra-and-composition.md).
_Avoid_: Repository, Orchestrator, Tensor

**Leaf Manifold**:
A Manifold backed by its own **substrate** (a Provider or a Coverage) — the only Manifolds that own data. → [ADR-0001](./adr/0001-manifold-algebra-and-composition.md).
_Avoid_: Atomic Manifold

**Composite Manifold**:
A Manifold defined over **child Manifolds + a combine rule**, owning no substrate (the Arbiter, a Calculator, the Reservoir). → [ADR-0001](./adr/0001-manifold-algebra-and-composition.md).
_Avoid_: ManifoldProduct, Operation, Combinator

**Calculator**:
A synthetic composite that **derives a parameter** from inputs via a function — a **selectable producer** the Arbiter picks like any Source; holds its own scoped Arbiter. → [ADR-0004](./adr/0004-producer-resolution-and-capability.md).
_Avoid_: Derivation, Formula node, DewpointManifold

**Derivation registry**:
Flat config for derived parameters — per parameter `(function, inputs, stored?)`; the Weaver wires it, memoizing one node per parameter. → [ADR-0004](./adr/0004-producer-resolution-and-capability.md).
_Avoid_: Plan, calculator tree, formula DSL

**Weaver**:
The **build-time graph constructor**: wires the static DAG from producers' `Capability` + policy config and allocates every `Store`; absent from the request path. → [architecture.md](./architecture.md#config-registry-weaver) · [ADR-0004](./adr/0004-producer-resolution-and-capability.md).
_Avoid_: Builder, Compiler, Orchestrator, Planner

**Countable**:
A Manifold capability: **node-Countable** declares an enumerable grid (its canonical lattice); **result** countability is conferred by the Selection's Domain. → [ADR-0001](./adr/0001-manifold-algebra-and-composition.md).
_Avoid_: Enumerable, Browsable, Indexed

**Writable**:
A Manifold capability: accepts `assimilate(coverage)` — the materialization boundary. The **`Store`** is the only Writable Manifold. → [ADR-0001](./adr/0001-manifold-algebra-and-composition.md).
_Avoid_: Materialized, Scratchboard, MaterializedManifold, SourceCache, ManifoldCache

**Store**:
The substrate a `Reservoir` owns — a `Writable`, `Countable` Manifold leaf holding sampled Coverages on its **declared grid `Domain`** (the canonical lattice — **provider-exact or a configured guess**) in **whole assimilable units** (`assimilate` replaces a unit atomically); the only `assimilate` target. → [architecture.md](./architecture.md#store--one-type-several-positions).
_Avoid_: Cache (over-claims transience), Buffer, Vault, Pool

**Reservoir**:
The **generic retention wrapper** — a read-only Manifold composed of a **`Store` + one child**; one reusable node that may sit at a **profile's root or inside it** (a Source is a Reservoir; the best view's root is a Reservoir). Adds retention, **not** selection — reduction lives in the **Arbiter** it may wrap. → [architecture.md](./architecture.md#reservoir).
_Avoid_: CachingManifold, Cache, Keeper, Sentinel;

**Task-oriented profile**:
A **named root composition** that resolves a requested view into a **`Coverage` on a target `Domain`** under an **objective** — the served root. **A profile is the whole composition + its objective; a `Reservoir` is one reusable node that may sit at a profile's root or inside it.** v1 ships one profile (the **best view**); a server may host several. Some profiles may expose **diagnostics / traces as sidecars**, but the **data product remains a `Coverage`** ([concern #14](./concerns.md#14-resolution-trace-and-observability)). Distinct from the **reduction policy** (the Arbiter's reconciler). → [architecture.md](./architecture.md#guiding-principles).
_Avoid_: View, Mode, Pipeline

**Best view**:
The **v1 task-oriented profile** — `Reservoir(store, top Arbiter)`: resolves the most suitable `Coverage` for a request under v1's objective (best-obtainable source + fallback). The `Reservoir` adds retention; the **Arbiter** carries the policy. → [architecture.md](./architecture.md#reservoir).
_Avoid_: Best provider, Router result

**Capability**:
The producer→Arbiter serving contract: structured clauses (`(quantity, aggregation)` × covered `Domain`, + native extent for extensive quantities) matched by a generic predicate (key / range-containment / extent-reachability); the **closure** of emitted functionals under exact conversion edges. Ordering and the `reconciler` are **policy**, not Capability. Distinct from `Countable` / `Writable`. → [ADR-0004](./adr/0004-producer-resolution-and-capability.md).
_Avoid_: Coverage

**Arbiter**:
The one **producer-resolution composite**: per parameter it folds candidate producers with a `reconciler` (default `priority` = selection). The **top** Arbiter spans all servable parameters; each Calculator holds its **own** scoped one. → [architecture.md](./architecture.md#arbiter) · [ADR-0004](./adr/0004-producer-resolution-and-capability.md).
_Avoid_: Selector, Dispatcher, Router, Resolver, Gateway

**Reconciler**:
The per-parameter strategy the Arbiter folds its producers with at each cell — `priority` (default; pick + fallback = selection), `tile`, `consensus`, `feather`. → [ADR-0004](./adr/0004-producer-resolution-and-capability.md).
_Avoid_: Mosaic, Combiner, Stitcher, Merger, Tiler

**Provider**:
A leaf Manifold: the vendor adapter + its **Normalizer** + capability / cadence declarations; authors each `ParameterData`'s full provenance at fetch. → [architecture.md](./architecture.md#provider-leaf-manifold).
_Avoid_: Vendor, backend, driver

**Source**:
A `Reservoir(store, Provider)` — the serve-or-fetch view of one provider's data; declares its **Capability** to the Arbiter. → [architecture.md](./architecture.md#source).

**Normalizer**:
The provider-specific mapping from vendor shape to canonical *semantics* (parameter identity, units, time encoding) in native geometry; lives inside a Provider. → [architecture.md](./architecture.md#normalization-vs-homogenization).

**Homogenization**:
**Sampling a field onto a target enumerable Domain** so its `ParameterData` are conformable — read-time, strictly geometric / temporal (distinct from normalization). The kernel degenerates to **identity when the target rides the grid** (a snapped read = a lossless crop); an off-grid point is nearest-neighbor (v1). → [architecture.md](./architecture.md#normalization-vs-homogenization).
