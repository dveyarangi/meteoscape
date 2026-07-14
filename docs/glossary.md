# Meteoscape

A manifold-based **Coverage-resolution engine** that resolves a request for a field into one normalized,
provenance-stamped **Coverage** under a stated policy/objective. The **best view** (best-obtainable source
plus fallback) is one objective; other profiles use the same engine under different objectives.

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

**GridDomain**:
The concrete `EnumerableDomain` representation — a `Mapping[AxisName, EnumerableAxis]`, **mixed** per axis (`RegularAxis` on X/Y/T; on Z a `VantageAxis`, a count-1 `RegularAxis` point, or an `IntervalAxis` column). Index math uses only `len` / `[]`, so mixed axes need no new arithmetic. It widens the uniform-only `RegularDomain` design and subsumes `RectilinearDomain` (explicit-cell axes are just non-`RegularAxis` members). → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: RegularDomain (the uniform-only predecessor), Grid (the raster sense; this is the domain type)

**Axis**:
The geometry along one dimension of a **`Separable`** Domain. Mirrors Domain vs EnumerableDomain: the base **`Axis`** is just a span (`extent`); the **`EnumerableAxis`** refinement adds an ordered sequence of `Cell`s, positional to a parameter's values. Enumerable representations: **`RegularAxis`** (uniform, parametric, the only snappable one), **`IntervalAxis`** (a single span cell — below), and **`VantageAxis`** (a request aperture — below). Continuous representations: **`ContinuousAxis`** (plain explicit span, X/Y reach) and **`RollingAxis`** (clock-anchored `valid_time` bound — the footprint's time axis). A continuous footprint axis may carry an optional native **`step`** ([concern #20](./concerns.md#20-provider-multi-resolution-offerings-offering-aware-selection)). → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: Dimension, Coordinate array

**IntervalAxis**:
A single-cell `EnumerableAxis` defined by one `interval` — `extent == bounds == interval`, one cell, default (containment) `matches`. The enumerable encoding of a **span cell**: the native cloud column `[0,TOA]`, and the base of `VantageAxis`. No `RegularAxis` form (a span is not `(anchor, step, count)` — no `step=inf`/`nan`). → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: ContinuousAxis (not enumerable; X/Y reach only), fat cell (that is the `Cell`, not the axis)

**VantageAxis**:
An `IntervalAxis` subclass that **overrides `matches` with intersection** — a **request** Z aperture ("the asker is somewhere in `[0, ~10 m]`"), authored at the edge. Its reason to exist is the inverted admission predicate, not geometry. Rides onto the served Coverage by closed projection; there it sits on the declared side, where only its `.extent` is read, so the inverted predicate never leaks. Never appears in a capability footprint. → [ADR-0002](./adr/0002-data-model.md), [ADR-0004](./adr/0004-producer-resolution-and-capability.md).
_Avoid_: Vantage cell (it is an axis; its one `Cell` is the aperture), footprint axis (never appears in a capability)

**matches** (admission predicate):
The per-axis admission test, owned by the **request** axis: `requested_axis.matches(declared_axis) -> bool`. Default (`Axis` base / `IntervalAxis`) = `declared.extent.contains(self.extent)` (request inside the footprint); `VantageAxis` overrides with `intersects` (overlap). `Domain.matches` composes it per axis — the **admission gate**, distinct from the *selection* of which admitted cell answers (maximal served cell / resampler, [ADR-0004](./adr/0004-producer-resolution-and-capability.md)). → [ADR-0004](./adr/0004-producer-resolution-and-capability.md).
_Avoid_: serves (the parameter-level Capability method that composes this), contains (Interval geometry only; not the Domain verb)

**Cell**:
One position on an `Axis` — a representative **coordinate** with optional **bounds**; no bounds ⇒ an **instant / point**. The unit a parameter's value aligns to; coordinate and bounds are independent (the coordinate sits *within* the bounds by convention, not by definition). → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: Tick (the coordinate alone), Pixel

**Bounds**:
A `Cell`'s span on one axis (its `Interval`); absent ⇒ the coordinate is an **instant / point**. The geometry an extensive or windowed parameter reads as its **extent** — the statistic / integration window. → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: Range (collides with a Coverage's `ranges`), Extent (the parameter-side window that *rides on* these bounds), span

**Interpolable axis**:
An axis whose values may be **synthesized between samples** (homogenization) — the 3 spatial axes and `valid_time`. → [ADR-0002](./adr/0002-data-model.md).

**Vertical reference**:
The datum a vertical (Z) axis is measured in — `above_ground` (the home of near-surface offsets like 2 m / 10 m), `isobaric` (pressure), `height_above_msl`. An **attribute of the Z axis** (**one per Domain**), *not* part of the coordinate, which stays a plain scalar. A **fat (layer) tick** — a Z `Cell` with layer-spanning `bounds` (e.g. 2–10 m) — lets near-surface parameters share **one** Domain. Non-comparability, height aliases, native offsets → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: Altitude (ambiguous across references), level (one value, not the datum)

**Vantage (Z request mode)**:
The request-Z mode carried by a **`VantageAxis`** (above) — the asker's position / acceptance window (`[0, ~10 m]` for the default near-surface bundle), authored at the edge, admitting by overlap. Its dual is the exact mode — a count-1 `RegularAxis` (level) or `IntervalAxis` (layer) **addressing** a precise cell, the alias table's target. → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: Ground mode (any altitude can be a vantage), Z tolerance (the window *is* the tolerance)

**Maximal served cell**:
For one functional's declared statistic cells, the served cell **containing all the others** (cloud total `[0,TOA]` over low/mid/high) — the cell a **vantage** request resolves to; none exists ⇒ per-parameter omission. A derivable fact, not a flag; exact-cell requests bypass it. → [ADR-0004](./adr/0004-producer-resolution-and-capability.md).
_Avoid_: Canonical/default cell (suggests authored config), total (the meteorological instance, not the rule)

**Categorical key**:
A discrete dimension you **select / group / iterate**, never interpolate — the **collection-layer** mechanism for `issue_time` archives and **ensemble / scenario** keys. **Not** a core field-Domain axis (the `Domain`'s four axes are all **field axes** — resamplable according to each parameter's `scale`). → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: Categorical axis (it is not a Domain axis), Label axis, index axis

### Data

**Coverage**:
A **field sampled onto an enumerable Domain** — the shape-agnostic data exchange unit; itself a Manifold (`Coverage <: Manifold`), equivalently a Selection filled with data. **Self-describing**: carries its `capability` (the `ParameterDef` per parameter × Domain — the descriptor block) beside its `ranges` and `provenance` plane, so it interprets standalone without the global Parameter table. → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: DataBlock, single-parameter Coverage

**Field**:
A Manifold (or projected view) **before sampling** — the general result of `project`; a Coverage is its sampled (countable) case. → [ADR-0001](./adr/0001-manifold-algebra-and-composition.md).
_Avoid_: Coverage (the sampled leaf), Parameter

**CoverageRecord**:
The canonical **memory-backed realization** of the `Coverage` protocol — the inert value object (`capability` + `ranges` + `provenance`) every projection materializes into. Realizations may vary by **backing** (memory, file, database), **never by domain shape** — Timeline / Grid are shapes of its `Domain`, not classes. → [architecture.md](./architecture.md#canonical-data-model).
_Avoid_: Timeline / Grid (domain shapes, not types), Tensor, DataBlock

**Timeline**:
A **domain shape**, not a type: a `CoverageRecord` whose domain varies only along `valid_time` (fixed location); its provenance plane is `PerParameter` (each parameter single-origin), the run identity stamped as `issue_time` on each origin. → [architecture.md](./architecture.md#canonical-data-model).

**Grid**:
A **domain shape**, not a type: a `CoverageRecord` whose domain varies spatially (fixed `valid_time`); its provenance plane may vary per geometry point (a mosaic), the `PerPoint` case. → [architecture.md](./architecture.md#canonical-data-model).

**Parameter**:
A single weather variable (e.g. temperature) that identifies a **`ParameterData`** within a Coverage — **not** a coordinate axis. → [architecture.md](./architecture.md#canonical-data-model).
_Avoid_: Variable, field, metric

**ParameterData**:
One parameter's **materialized data slice** in a Coverage — pure numbers `(values, present mask)`, positional to the Domain; every interpreting descriptor is id-entailed and lives in the `ParameterDef`, surfaced via the Coverage's `capability`. One per parameter; not itself a Manifold. → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: Range (reads as an interval — collides with a `Cell`'s `bounds`), DataBlock, slice

**ParameterDef**:
The **canonical definition** of a parameter — its stored facts `(id, quantity, canonical_unit, statistic)`, with `extent_scaling` and `scale` **entailed by its `quantity`** (the identity root), not restated — the single home of every fact entailed by its id; a Coverage surfaces it via its `capability` **descriptor block**, and producers / the edge resolve it by `ParameterId` from the **Parameter table**. → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: Parameter (the identifier), schema

**Canonical unit**:
A parameter's **single** unit (`ParameterDef.canonical_unit`) — every value of that parameter, everywhere in the algebra, is in it (the **canonical-mono-unit invariant**); the interior is unit-blind, conversion happens only at the two edges. → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: display unit (a surface-egress concern), per-value unit

**Parameter table**:
The injected **lookup of `ParameterDef`s** (keyed by `ParameterId`) that producers and the edge resolve canonical parameter facts from; a swappable interface whose backing may be static or dynamic. → [architecture.md](./architecture.md#config-binders-weaver).
_Avoid_: SourceBinder, CalculatorCatalog / CalculatorRegistry, Catalogue


**CellStatistic**:
The **window statistic** a value summarizes its cell with — `point | max | min | mean`; *dimension-preserving*; fixed by parameter identity (lives on `ParameterDef`). The calculus axis (accumulation) is the quantity **`extent_scaling`**, not a value here. → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: Operator (too generic), aggregation (connotes the extensive integral — the very thing this is *not*), sum (that is integration — extent-scaling), cell-method (statistic × extent, not the verb alone)

**Quantity**:
The **identity root** of a parameter — a physical field carrying an **`extent_scaling`** (`intensive` / `extensive`) and a **`scale`** (measurement scale); rain-intensity (`intensive` rate) and precipitation (`extensive` integral) are *distinct* quantities, related by integration. → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: Parameter (that is the functional `(quantity, statistic)`), variable

**ExtentScaling**:
A quantity's relationship to a cell's temporal extent — **intensive** (instantaneous, extent-independent: temperature, rain-rate; window statistics apply) or **extensive** (additive, the integral over the extent: precipitation; extent required). → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: Kind (vague), state / rate / accumulation (those conflate identity with the integration edge)

**MeasurementScale**:
A quantity's measurement scale — `linear` / `circular` / `nominal` / `ordinal` — which selects the **refine-up resampler**. Provider-served wind components are linear; derived `wind_direction` is circular. A nearest-neighbor read-back does not exercise circular interpolation. → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: Type, dtype

**Resampler**:
The per-parameter, **asymmetric** rule for moving a value across resolutions — **refine-up** from the `scale`, **coarsen-down** from the `statistic` (whole phase-aligned aggregation; never disaggregation). Entailed by `(scale, statistic, extent_scaling)`, so interpolability is a **parameter** fact, not a Domain/axis one; kernels are a deferred registry (mirror of the `reconciler`). `serves` admits on a **lossless** resampler path. → [ADR-0004](./adr/0004-producer-resolution-and-capability.md) · [concern #5](./concerns.md#5-read-time-homogenization-fidelity).
_Avoid_: Interpolator (only the refine-up, linear half), kernel (one implementation)

**Functional**:
A **requestable parameter** = `statistic(quantity)` — the materialized key `(quantity, statistic)`; neither extent **nor vertical height** is in it (extent rides the Domain's `valid_time` `Cell` `bounds`, height rides the Z `Cell`). Aliases like `precip_3h` or `temperature_2m` are surface sugar desugaring to functional + Domain cells. → [ADR-0002](./adr/0002-data-model.md).
_Avoid_: Alias (the sugar), parameter name (ambiguous)

**Nodata**:
A **cell-level data gap** — a producer succeeded but has no value at a cell (`present[i] = False`); **data, not a fault**. → [architecture.md](./architecture.md#failure-nodata-and-availability).
_Avoid_: Missing (ambiguous with an absent parameter), failure, error, null

**ProvenanceField**:
A **Coverage's provenance plane** over (parameter, geometry-point) — `Uniform`, `PerParameter`, and `PerPoint` behind one interface: `summary(parameter)` is the **O(1)** per-parameter handle; `at(parameter, i)` is the exact per-cell record. → [ADR-0003](./adr/0003-provenance-and-origin.md).
_Avoid_: provenance array, per-point provenance (the `PerPoint` case only), per-`ParameterData` attribute

**Provenance**:
One **origin record** — what a (parameter, point) value derives from (origin, fetched-at, `expiration`); held by a Coverage's `ProvenanceField`. → [ADR-0003](./adr/0003-provenance-and-origin.md).
_Avoid_: Lineage (part of a *synthetic* Origin)

**Origin**:
What a (parameter, point) value derives from — **atomic** (a single Provider fetch) or **synthetic** (derived from multiple parent provenances, its **lineage**). → [ADR-0003](./adr/0003-provenance-and-origin.md).
_Avoid_: Source (the Manifold)

**SourceKey**:
The **identity of a configured producer** — the origin an atomic `Origin` is *stamped with* (the **producer / leaf**, not the Reservoir `Source` role). **Structured** `(provider, dataset)`; `dataset` is **always named** and **discriminates offerings opaquely** (compared for equality, never parsed). Its `__str__` is the SourceRegistry / config token (e.g. `open-meteo:best_match`). Defined in `identity.py` (Tier-0 leaf). Build-time derivation, extensibility, and what stays out of the key → [ADR-0003](./adr/0003-provenance-and-origin.md).
_Avoid_: Source (the Reservoir role), raw source string

**Valid time**:
The time a value describes (what the weather *is* at). → [architecture.md](./architecture.md#canonical-data-model).

**Issue time**:
Which forecast **issuance** a value came from — the **model run (reference) time in UTC**, a **provenance stamp (run identity)** on the atomic `Origin`, **not** a Domain axis; derived via the provider's **cadence** (`CadenceDef`) and the basis of freshness. Cross-run lives in the collection / reconciler seam. → [ADR-0003](./adr/0003-provenance-and-origin.md).
_Avoid_: issue_time *axis* (it is a stamp, not an axis)

**Quality**:
How good a source's data is for a parameter — the basis for the Arbiter's selection. → [architecture.md](./architecture.md#arbiter).

**Cadence**:
A **Provider**'s run interval `Δ` (with publication latency `L` and `max_lead`) — the **`CadenceDef`** from which `issue_time`, `expiration`, and the footprint forward edge derive. → [ADR-0003](./adr/0003-provenance-and-origin.md).

**Clock**:
The system time source — the single wall-clock read, a **build-time** dependency injected into **Provider**s by `SourceBinder` at construction (never threaded through `project`), like a configured logger. `Metronome` floors `now()` to a coarse resolution tick (so the run anchor is a step function); `StoppedClock` freezes an instant for tests. → [ADR-0003](./adr/0003-provenance-and-origin.md).

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
The **store-private, per-axis** grids `quantize` snaps to (provider-exact where a vendor declares one, a configured guess otherwise); an axis without one passes through `quantize` identity. Never exposed as a node `domain`. → [ADR-0006](./adr/0006-materialization-granularity-and-store-shape.md) · [architecture.md](./architecture.md#store--one-type-several-positions).

**Quantize**:
The `Store`-side operation that maps a Selection to the store's **storable shape** — **per axis**: an axis with a declared lattice snaps onto it **and widens the extent outward to whole assimilable units** (for example, a parameter's timeline at a spatial cell), so the result **encloses** the request (extent ≥ request) and `assimilate` only ever replaces whole units; an axis **without** a lattice passes through **identity**, its cell joining the unit key. Resolving stored cells back onto the requested coordinates is **Homogenization** (read-back), not quantize. → [ADR-0006](./adr/0006-materialization-granularity-and-store-shape.md) · [architecture.md](./architecture.md#reservoir).
_Avoid_: snap (only quantize's grid-alignment half), align / round (align is homogenization)

### Roles

**Gateway**:
The surface-neutral **caller-policy boundary** (authz, rate-limit, quota) in front of a served profile; resolves a canonical Selection to a **Coverage** (or rejects); not a Manifold itself. → [architecture.md](./architecture.md#gateway--caller-policy-boundary).
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
_Avoid_: Formula node, DewpointManifold, Derivation (ambiguous build-time noun)

**CalculatorCatalog**:
Process-wide map of function ids to `CalculatorManifest`s available for profile composition. → [ADR-0005](./adr/0005-build-time-composition.md).
_Avoid_: CalculatorRegistry (the bound weave input), live Calculator map, DerivationCatalog

**CalculatorManifest**:
A calculator plugin's cohesive declaration: its combine function and the constraints under which it may be invoked. → [ADR-0005](./adr/0005-build-time-composition.md).
_Avoid_: Calculator instance, data-flow edge, DerivationManifest

**CalculatorSpec**:
Profile recipe for one derived parameter — `(output, inputs, fn_id, stored?)`. Bound by `CalculatorBinder` before weave. → [ADR-0005](./adr/0005-build-time-composition.md).
_Avoid_: Calculator instance, RegisteredCalculator, formula DSL, DerivationSpec

**CalculatorRegistry**:
Build product of `CalculatorBinder` — output-keyed `RegisteredCalculator`s (catalog-resolved bindings, not live Calculator nodes). Peer of `SourceRegistry` on `ProfileDef`. → [ADR-0005](./adr/0005-build-time-composition.md).
_Avoid_: CalculatorCatalog, live Calculator map, DerivationRegistry

**RegisteredCalculator**:
One catalog-resolved calculator binding — resolved manifest + inputs + `stored?`. Weaver builds the `Calculator` node. → [ADR-0005](./adr/0005-build-time-composition.md).
_Avoid_: Calculator (the graph node), CalculatorSpec (the unbound declaration), RegisteredDerivation

**CalculatorBinder**:
Resolves `CalculatorSpec`s against a `CalculatorCatalog` into a `CalculatorRegistry`. Peer of `SourceBinder`. → [ADR-0005](./adr/0005-build-time-composition.md).
_Avoid_: Weaver, SourceBinder, DerivationBinder

**SourceBinder**:
Resolves `OfferingDef`s against a `ProviderCatalog` into a `SourceRegistry`. Peer of `CalculatorBinder`. → [ADR-0005](./adr/0005-build-time-composition.md).
_Avoid_: Weaver, CalculatorBinder, OfferingBinder, Registry (ambiguous factory role)

**SourceRegistry**:
Build product of `SourceBinder` — `SourceKey`-keyed `RegisteredSource`s (configured producer + priority + Source-store lattice). Peer of `CalculatorRegistry` on `ProfileDef`. → [ADR-0005](./adr/0005-build-time-composition.md).
_Avoid_: OfferingRegistry, ProviderCatalog, live Source map

**RegisteredSource**:
One configured producer plus extrinsic priority and its Source-store lattice. → [ADR-0005](./adr/0005-build-time-composition.md).
_Avoid_: Source (the Reservoir role), OfferingDef, RegisteredOffering

**ProviderCatalog**:
Process-wide map of implementation ids to cohesive `ProviderManifest`s available for profile composition. → [ADR-0005](./adr/0005-build-time-composition.md).
_Avoid_: Provider instance map, Parameter table

**ProviderManifest**:
A provider plugin's cohesive declaration: identity, offerings, secret requirement, and construction operation. → [ADR-0005](./adr/0005-build-time-composition.md).

**SecretSlot**:
Impl-level secret binding name on a `ProviderManifest` (offerings inherit); values live in the injected secrets map, keyed usually by `OfferingDef.secret_ref`. → [architecture.md](./architecture.md#config-binders-weaver).
_Avoid_: secret value, API key field on OfferingDef

**OfferingSpec**:
Catalogue product row — offering `name`, exact `ParameterId` set, optional `StoreSpec` (configured guess when the Provider declares no native lattice). → [architecture.md](./architecture.md#config-binders-weaver).
_Avoid_: OfferingDef (enablement), ParameterDef, default_lattice (duplicates construction state)

**StoreSpec**:
Operator/catalogue knobs for a `Store` that needs a **configured guess** — `{ spatial_step, retention_interval }`. Same shape for the profile root, a Source whose provider declares no native lattice, and a stored Calculator; the factory builds the declared grid at weave. Provider-exact lattices reach the factory via the build-time construction face instead. → [architecture.md](./architecture.md#store--one-type-several-positions) · [ADR-0005](./adr/0005-build-time-composition.md).
_Avoid_: RootStoreSpec (duplicates `StoreSpec`), default_lattice, prebuilt EnumerableDomain as catalogue config

**OfferingDef**:
Profile **enablement declaration** for one catalogue offering — `{ impl, name?, priority, secret_ref?, settings, store? }` — that `SourceBinder` builds from (with `ProviderCatalog`); optional `store` overrides the catalogue `StoreSpec`. No raw `SourceKey`. `name=None` selects the expand path. → [architecture.md](./architecture.md#config-binders-weaver).
_Avoid_: SourceDef, Source (the built role), OfferingSpec (catalogue product), Provider (the impl)

**ProfileConfig**:
Operator-side, per-profile enablement — `offerings` (`OfferingDef`s), `calculators` (`CalculatorSpec`s), root `StoreSpec`, arbiter policy. → [architecture.md](./architecture.md#config-binders-weaver).
_Avoid_: sources / derivations (misname declarations), RootStoreSpec (duplicates `StoreSpec`)

**ProfileDef**:
Weave input for one served root: `SourceRegistry` + `CalculatorRegistry` + root store + arbiter. → [ADR-0005](./adr/0005-build-time-composition.md).
_Avoid_: WeavePlan, freeform DAG script, ProfileConfig

**Weaver**:
The **build-time graph constructor**: `Weaver(stores).weave(ProfileDef)` allocates every `Store` via
`StoreFactory`, builds the Source map, constructs the `Arbiter` from that map + `SourceRegistry` +
`ArbiterPolicy`, and returns the best-view root; absent from the request path. Holds no catalogue;
does not interpret priority. → [architecture.md](./architecture.md#config-binders-weaver) ·
[ADR-0004](./adr/0004-producer-resolution-and-capability.md) ·
[ADR-0005](./adr/0005-build-time-composition.md).
_Avoid_: Builder, Compiler, Orchestrator, Planner, CalculatorBinder

**Countable**:
A **materialized result's** property — a `Coverage` exposes the enumerable `domain` it was sampled onto (derived from its `capability`), conferred by the Selection's Domain. **Not a node facet**: a node's lattices are private to its `Store`. → [ADR-0001](./adr/0001-manifold-algebra-and-composition.md) · [ADR-0006](./adr/0006-materialization-granularity-and-store-shape.md).
_Avoid_: node-Countable (nodes expose capability, not domain), Enumerable, Browsable, Indexed

**Writable**:
A Manifold facet: accepts `assimilate(coverage)` — the materialization boundary. The **`Store`** is the only Writable Manifold. → [ADR-0001](./adr/0001-manifold-algebra-and-composition.md).
_Avoid_: Materialized, Scratchboard, MaterializedManifold, SourceCache, ManifoldCache

**Store**:
The substrate a `Reservoir` owns — a `Writable` Manifold leaf holding **per-parameter units** (`(parameter, per-axis cells, window)`; `assimilate` splits a native record into units and replaces each atomically); the only `assimilate` target. **Unit-granular, never co-domained**; its per-axis lattices (**provider-exact or a configured guess**) are **private** — the `quantize` / report / read-back target, never a public `domain`. Allocated by the Weaver through **`StoreFactory.create`**. → [ADR-0006](./adr/0006-materialization-granularity-and-store-shape.md) · [architecture.md](./architecture.md#store--one-type-several-positions).
_Avoid_: Cache (over-claims transience), Buffer, Vault, Pool

**Reservoir**:
The **generic retention wrapper** — a read-only Manifold composed of a **`Store` + one child**; one reusable node that may sit at a **profile's root or inside it** (a Source is a Reservoir; the best view's root is a Reservoir). Adds retention, **not** selection — reduction lives in the **Arbiter** it may wrap. → [architecture.md](./architecture.md#reservoir).
_Avoid_: CachingManifold, Cache, Keeper, Sentinel

**Task-oriented profile**:
A **named root composition** that resolves a requested view into a **`Coverage` on a target `Domain`** under an **objective** — the served root. **A profile is the whole composition + its objective; a `Reservoir` is one reusable node that may sit at a profile's root or inside it.** The **best view** is one profile; a server may host several. Distinct from the **reduction policy** (the Arbiter's reconciler). → [architecture.md](./architecture.md#guiding-principles).
_Avoid_: View, Mode, Pipeline

**Best view**:
A **task-oriented profile** — `Reservoir(store, top Arbiter)` — that resolves the most suitable `Coverage` for a request under a best-obtainable-source-with-fallback objective. The `Reservoir` adds retention; the **Arbiter** carries the policy. → [architecture.md](./architecture.md#reservoir).
_Avoid_: Best provider, Router result

**Capability**:
What a Manifold serves — a **facet of every Manifold, the dual of `project`**: a `serves(parameter, requested)` predicate + the served `parameters` (`ParameterId → ParameterDef`); a concrete covered `Domain` is **not** on the interface. Distinct from the `Writable` facet. The leaf/composite family and the matching predicate → [ADR-0004](./adr/0004-producer-resolution-and-capability.md).
_Avoid_: Coverage, clause

**Footprint**:
A producer's **declared reach** — the region its `FootprintCapability` tests `serves` against: per-axis declarations of **mixed kind** — **span** axes (spatial region, a statistic-cell Z, the **clock-anchored** `valid_time` window around the run anchor — the provider's cadence, [ADR-0003](./adr/0003-provenance-and-origin.md)) and **sample point-cell** axes (`RegularAxis` count-1, e.g. Z `[2,2]`). Modelled as the `FootprintDomain` — never an `EnumerableDomain`; its `matches` composes per-axis request-driven `matches` and is clock-relative — distinct from a materialized `Coverage`'s enumerable grid. → [ADR-0002](./adr/0002-data-model.md) · [ADR-0004](./adr/0004-producer-resolution-and-capability.md).
_Avoid_: coverage, grid, extent

**Arbiter**:
The one **producer-resolution composite**: constructed with the woven Source map
(`SourceKey → Manifold`), the raw **`SourceRegistry`**, and **`ArbiterPolicy`**. Per parameter it folds
candidates with a `reconciler` (default `priority` = selection; ranking reads
`RegisteredSource.priority` from the registry). The **top** Arbiter spans all servable parameters;
each Calculator holds its **own** scoped one. → [architecture.md](./architecture.md#arbiter) ·
[ADR-0004](./adr/0004-producer-resolution-and-capability.md).
_Avoid_: Selector, Dispatcher, Router, Resolver, Gateway

**Reconciler**:
The per-parameter strategy the Arbiter folds its producers with at each cell — `priority` (default; pick + fallback = selection), `tile`, `consensus`, `feather`. → [ADR-0004](./adr/0004-producer-resolution-and-capability.md).
_Avoid_: Mosaic, Combiner, Stitcher, Merger, Tiler

**Provider**:
A leaf Manifold: the vendor adapter + its **Normalizer** + capability / cadence declarations; authors the Coverage's provenance (a single-fetch `Uniform` plane) at fetch. → [architecture.md](./architecture.md#provider-leaf-manifold).
_Avoid_: Vendor, backend, driver

**Source**:
A `Reservoir(store, Provider)` — the serve-or-fetch view of one provider's data; a **role, not a distinct type**. Forwards its Provider's **Capability** to the Arbiter unchanged. → [architecture.md](./architecture.md#source).

**Normalizer**:
The provider-specific mapping from vendor shape to canonical *semantics* (parameter identity, units, time encoding) in native geometry; lives inside a Provider. Emits **native records** — one per set of parameters sharing a native Domain. → [architecture.md](./architecture.md#normalization-vs-homogenization) · [ADR-0006](./adr/0006-materialization-granularity-and-store-shape.md).

**Native record**:
One **co-domained Coverage a fetch materializes per shared native Domain** — its Domain is true native geometry (e.g. the parameter's native Z cell); the assimilation input and the landing-layer content. The grouping is emergent from the `Tap` declarations and axis-agnostic (one record when everything shares a geometry). → [ADR-0006](./adr/0006-materialization-granularity-and-store-shape.md).
_Avoid_: Z-group (one possible grouping, not the rule), raw response (that is vendor JSON)

**Homogenization**:
**Sampling a field onto a target enumerable Domain** so its `ParameterData` are conformable — read-time, strictly geometric / temporal (distinct from normalization). The kernel degenerates to **identity when the target rides the grid** (a snapped read = a lossless crop); nearest-neighbor is the degenerate off-grid kernel. → [architecture.md](./architecture.md#normalization-vs-homogenization).
