# Meteoscape

Meteoscape is a manifold-based weather-coverage context that resolves field requests into normalized, provenance-stamped Coverages under a chosen objective.

## Language

### Domains

**Domain**:
A coordinate set over longitude, latitude, vertical position, and valid time; it may be continuous or enumerable. → [ADR-0002](./adr/0002-data-model.md)
_Avoid_: Bounds, extent, region

**EnumerableDomain**:
An indexable Domain of coordinate positions, arranged as either a regular lattice or an irregular point set. → [ADR-0002](./adr/0002-data-model.md)
_Avoid_: Geometry, lattice

**GridDomain**:
An EnumerableDomain whose axes may use different enumerable representations. → [ADR-0002](./adr/0002-data-model.md)
_Avoid_: RegularDomain, Grid

**SelectionDomain**:
The request-side Domain representation composed from SelectableAxis members; structurally separable without narrowing the Selection contract, and never enumerable. → [ADR-0002](./adr/0002-data-model.md)
_Avoid_: SelectedDomain, GridDomain (the materialized and store shape), request lattice

**SelectableAxis**:
The axis kinds a request may carry — regular (exact), vantage (aperture), or snapped (bounds-only). → [ADR-0002](./adr/0002-data-model.md), [architecture.md](./architecture.md#request-modes)
_Avoid_: input axis, request axis

**Axis**:
The geometry of one dimension of a separable Domain; an EnumerableAxis adds an ordered sequence of Cells. → [ADR-0002](./adr/0002-data-model.md)
_Avoid_: Dimension, coordinate array

**IntervalAxis**:
A single-cell EnumerableAxis whose Cell spans an interval. → [ADR-0002](./adr/0002-data-model.md)
_Avoid_: ContinuousAxis, fat cell

**VantageAxis**:
A request-only vertical aperture whose admission is based on overlap rather than containment. → [ADR-0002](./adr/0002-data-model.md)
_Avoid_: Vantage cell, footprint axis

**SnappedAxis**:
A request-only bounds-only axis: it states where an answer starts and stops and leaves anchor and step to the resolver. Span-shaped dual of the VantageAxis, and temporal by type. → [ADR-0002](./adr/0002-data-model.md)
_Avoid_: Window axis, open axis, soft axis

**Clip**:
The restriction of an Axis to bounds — the part of itself the axis says those bounds ask for, or nothing when they do not meet. Bounds are optional: asking with none asks for the axis entire, so boundlessness is answered by the axis rather than branched on by callers. Returns whatever the restriction leaves (a span stays a span, a lattice a lattice at its own phase, a clock-relative window materialises first); whether that has Cells is Ground's question, not this one. → [ADR-0002](./adr/0002-data-model.md)
_Avoid_: Snap (the request mode), clamp, trim, crop (the value-side operation on a Coverage)

**Lattice**:
A Store's private per-axis retention grid — the quantize, report, and read-back target. Never public: a node exposes no lattice, and the only public Domain is a Coverage's. → [ADR-0006](./adr/0006-materialization-granularity-and-store-shape.md)
_Avoid_: Grid (a Coverage Domain shape), node domain, public lattice

**Admission predicate**:
The per-axis rule that decides whether a request lies within a producer's declared Footprint. → [ADR-0004](./adr/0004-producer-resolution-and-capability.md)
_Avoid_: Serves, contains

**Cell**:
One position on an Axis, represented by a coordinate and optional Bounds. → [ADR-0002](./adr/0002-data-model.md)
_Avoid_: Tick, pixel

**Bounds**:
The interval spanned by a Cell; without Bounds, the Cell represents an instant or point. → [ADR-0002](./adr/0002-data-model.md)
_Avoid_: Range, extent

**Interpolable axis**:
A spatial or valid-time axis on which values may be synthesized between samples. → [ADR-0002](./adr/0002-data-model.md)

**Vertical reference**:
The datum against which a Domain's vertical coordinates are measured. → [ADR-0002](./adr/0002-data-model.md)
_Avoid_: Altitude, level

**Vantage**:
A vertical request mode that expresses the requester's position or acceptance window rather than an exact level or layer. → [ADR-0002](./adr/0002-data-model.md)
_Avoid_: Ground mode, Z tolerance

**Maximal served cell**:
The declared statistic Cell that contains every other Cell for the same Functional and therefore answers a Vantage request. → [ADR-0004](./adr/0004-producer-resolution-and-capability.md)
_Avoid_: Canonical cell, default cell, total

**Categorical key**:
A discrete collection-layer dimension used for selection, grouping, or iteration rather than interpolation. → [ADR-0002](./adr/0002-data-model.md)
_Avoid_: Categorical axis, label axis, index axis

### Data

**Coverage**:
A field sampled onto an EnumerableDomain and carrying the parameter semantics and provenance needed to interpret it. → [ADR-0002](./adr/0002-data-model.md)
_Avoid_: DataBlock, single-parameter Coverage

**Field**:
A Manifold or projected view before it is sampled into a Coverage. → [ADR-0001](./adr/0001-manifold-algebra-and-composition.md)
_Avoid_: Coverage, Parameter

**CoverageRecord**:
The canonical materialized form of Coverage, independent of Domain shape. → [architecture.md](./architecture.md#canonical-data-model)
_Avoid_: Timeline, Grid, Tensor, DataBlock

**CoverageSet**:
The multi-domain answer: the CoverageRecords one projection yielded, kept on the differing native cells a request's boundless axes licensed. A Manifold with no Domain of its own — projecting it onto enumerable cells crops each record against its own geometry and merges them into a single Coverage — and every Parameter it carries lives on exactly one record. → [ADR-0001](./adr/0001-manifold-algebra-and-composition.md), [ADR-0007](./adr/0007-capability-carries-its-domain.md)
_Avoid_: CoverageGroup, multi-Coverage, bundle, collection

**Timeline**:
A Coverage Domain shape that varies only along valid time at a fixed location. → [architecture.md](./architecture.md#canonical-data-model)

**Grid**:
A Coverage Domain shape that varies spatially at a fixed valid time. → [architecture.md](./architecture.md#canonical-data-model)

**Parameter**:
A weather variable that identifies one ParameterData within a Coverage. → [architecture.md](./architecture.md#canonical-data-model)
_Avoid_: Variable, field, metric

**ParameterData**:
The materialized values and presence information for one Parameter, positioned on a Coverage's Domain. → [ADR-0002](./adr/0002-data-model.md)
_Avoid_: Range, DataBlock, slice

**ParameterDef**:
The canonical semantic definition associated with a Parameter identity. → [ADR-0002](./adr/0002-data-model.md)
_Avoid_: Parameter, schema

**Canonical unit**:
The single unit in which a Parameter is represented inside Meteoscape. → [ADR-0002](./adr/0002-data-model.md)
_Avoid_: Display unit, per-value unit

**Parameter table**:
The authoritative lookup of ParameterDefs by Parameter identity. → [architecture.md](./architecture.md#config-binders-weaver)
_Avoid_: Catalogue, SourceBinder, CalculatorCatalog

**CellStatistic**:
The dimension-preserving statistic a value summarizes over its Cell, such as point, minimum, maximum, or mean. → [ADR-0002](./adr/0002-data-model.md)
_Avoid_: Operator, aggregation, sum, cell method

**Quantity**:
The physical field at the root of Parameter identity, characterized by its ExtentScaling and MeasurementScale. → [ADR-0002](./adr/0002-data-model.md)
_Avoid_: Parameter, variable

**ExtentScaling**:
A Quantity classification describing whether values are extent-independent (intensive) or additive over Cell extent (extensive). → [ADR-0002](./adr/0002-data-model.md)
_Avoid_: Kind, state, rate, accumulation

**MeasurementScale**:
A Quantity's linear, circular, nominal, or ordinal value structure. → [ADR-0002](./adr/0002-data-model.md)
_Avoid_: Type, dtype

**Resampler**:
The Parameter-specific rule for mapping values between resolutions. → [ADR-0004](./adr/0004-producer-resolution-and-capability.md)
_Avoid_: Interpolator, kernel

**Functional**:
A requestable Parameter identity formed from a Quantity and CellStatistic; spatial and temporal extent remain on the Domain. → [ADR-0002](./adr/0002-data-model.md)
_Avoid_: Alias, parameter name

**Nodata**:
A successful cell-level result in which no value is present. → [architecture.md](./architecture.md#failure-nodata-and-availability)
_Avoid_: Missing, failure, error, null

**ProvenanceField**:
A Coverage's provenance plane across Parameters and geometry points. → [ADR-0003](./adr/0003-provenance-and-origin.md)
_Avoid_: Provenance array, per-point provenance

**Provenance**:
The record of an Origin and its retrieval and expiration times for a value. → [ADR-0003](./adr/0003-provenance-and-origin.md)
_Avoid_: Lineage

**Origin**:
What a value derives from, either one Provider fetch or a synthetic combination of parent Provenances. → [ADR-0003](./adr/0003-provenance-and-origin.md)
_Avoid_: Source

**SourceKey**:
The stable identity of a configured producer, distinguished by provider and named dataset. → [ADR-0003](./adr/0003-provenance-and-origin.md)
_Avoid_: Source, raw source string

**Valid time**:
The time at which a weather value applies. → [architecture.md](./architecture.md#canonical-data-model)

**Issue time**:
The forecast issuance represented by a value, recorded as Origin provenance rather than as a Domain axis. → [ADR-0003](./adr/0003-provenance-and-origin.md)
_Avoid_: Issue-time axis

**Quality**:
The fitness of a producer's data for a Parameter under an Arbiter's objective. → [architecture.md](./architecture.md#arbiter)

**Cadence**:
A Provider's timing declaration: run interval and publication latency define run identity and freshness;
maximum lead and an optional shelf quantum define its availability window. → [ADR-0003](./adr/0003-provenance-and-origin.md)

**Consensus**:
A Reconciler that blends overlapping contributors instead of selecting one. → [ADR-0004](./adr/0004-producer-resolution-and-capability.md)

### Outcomes

**Capability mismatch**:
An unavailable requested Parameter because no producer declares support for it. → [architecture.md](./architecture.md#failure-nodata-and-availability)
_Avoid_: Not found, unsupported, Nodata

**Runtime failure**:
A producer's failure to return usable data despite declaring the requested Capability. → [architecture.md](./architecture.md#failure-nodata-and-availability)
_Avoid_: Nodata, outage

**Partial success**:
A successful Coverage containing the producible subset of requested Parameters. → [architecture.md](./architecture.md#failure-nodata-and-availability)
_Avoid_: Degraded, best effort

### Requests

**Selection**:
The canonical request formed by a Domain and a set of Parameters. → [ADR-0002](./adr/0002-data-model.md)
_Avoid_: Need

**Selection mode**:
The continuous, snapped, or enumerable form of Domain carried by a Selection — encoding what the caller fixes about the answering lattice: all of it (enumerable), only bounds with the resolver's grid supplying anchor and step (snapped), or a continuous region wanting a field (continuous). → [ADR-0002](./adr/0002-data-model.md), [architecture.md](./architecture.md#request-modes)

**Snapped**:
The request mode that fixes only an axis's bounds; the resolver's grid supplies anchor and step, and the answer is the grid's cells within the bounds. → [ADR-0002](./adr/0002-data-model.md)
_Avoid_: Soft window, clamped window, bounded-ANY

**ANY**:
The boundless form of the Snapped member — a request member that leaves one axis entirely to the producer: the answer keeps the producer's native cells on that axis and may group records that differ there. Not a separate axis kind; Snapped and ANY are one member kind differing only in whether bounds are present. A one-sided open bound is the same family's deferred "from X onward" form. → [006](./tickets/01-0115-retentive-store-freshness.md), [architecture.md](./architecture.md#request-modes)
_Avoid_: Wildcard, unbounded, whole-axis

**Canonical lattice**:
A Store-private per-axis grid used to determine storable coordinates. → [ADR-0006](./adr/0006-materialization-granularity-and-store-shape.md)

**Ground**:
Resolving a request against a node's declared or delivered geometry into the answer geometry it asks for: pinned axes pass through, snapped axes take what the answering axis Clips to. The resolver's half of shape-correspondence, and Quantize's request-side sibling (Ground restricts to the request, Quantize encloses it). → [ADR-0002](./adr/0002-data-model.md), [ADR-0001](./adr/0001-manifold-algebra-and-composition.md)
_Avoid_: Resolve (the Gateway's verb), realize, instantiate; **above_ground** / ground level (the Vertical reference sense — unrelated)

**Quantize**:
The Store transformation from a Selection to enclosing, atomically storable units on its Canonical lattice. → [ADR-0006](./adr/0006-materialization-granularity-and-store-shape.md)
_Avoid_: Snap, align, round

**Refill**:
The Reservoir's fetch-on-miss: when a requested unit is missing or stale, one projection of the child over the quantized store shape, whose answer is assimilated before serving. The ask names the missing parameters; the answer may carry the child's natural fetch unit. → [006](./tickets/01-0115-retentive-store-freshness.md)
_Avoid_: Cache fill, fetch-through, backfill, revalidation

**Natural fetch unit**:
What one trip to a producer inherently carries — the Provider's own economy fact. An answer may be wider than the ask's parameter set by carrying it, never narrower. → [006](./tickets/01-0115-retentive-store-freshness.md), [#43](./concerns.md#43-narrow-answering-providers-re-open-mixed-request-run-divergence)
_Avoid_: Whole offering (one producer's particular natural unit, not the concept)

**Envelope**:
The summary a surface narrates of what a profile can answer — its served Parameters and Reach. → [#29](./concerns.md#29-narrated-reach-what-a-profile-promises)
_Avoid_: Capability (the admission authority), coverage

**Horizon**:
A conservative statement of how far ahead a profile serves — the `valid_time` projection of a Reach, narrated as a duration ahead of the latest run rather than an instant. → [#29](./concerns.md#29-narrated-reach-what-a-profile-promises)
_Avoid_: Reach (the whole Domain, not one axis of it); default window (what the edge authors from a Horizon); lead time

### Composition

**CalculatorCatalog**:
The available Calculator plugin declarations, keyed by function identity. → [ADR-0005](./adr/0005-build-time-composition.md)
_Avoid_: CalculatorRegistry, live Calculator map, DerivationCatalog

**CalculatorManifest**:
A Calculator plugin's function and invocation constraints. → [ADR-0005](./adr/0005-build-time-composition.md)
_Avoid_: Calculator instance, data-flow edge, DerivationManifest

**CalculatorDef**:
A profile enablement of one calculator — its function identity, co-produced output group, inputs, priority, and retention choice (the calculator peer of `OfferingDef`). → [ADR-0005](./adr/0005-build-time-composition.md)
_Avoid_: CalculatorSpec, Calculator, RegisteredCalculator, DerivationSpec

**CalculatorKey**:
The identity of a configured calculator — its method plus a named variant (`method`, `name`); the calculator peer of `SourceKey`, one arm of `ProducerKey`. `name` is binder-defaulted to `"default"` when the `CalculatorDef` omits it. → [ADR-0005](./adr/0005-build-time-composition.md)
_Avoid_: fn_id (that is only the method arm), output group

**CalculatorRegistry**:
The bound Calculator declarations for a ProfileDef, keyed by `CalculatorKey`. → [ADR-0005](./adr/0005-build-time-composition.md)
_Avoid_: CalculatorCatalog, live Calculator map, DerivationRegistry

**RegisteredCalculator**:
One catalog-resolved Calculator binding. → [ADR-0005](./adr/0005-build-time-composition.md)
_Avoid_: Calculator, CalculatorDef, RegisteredDerivation

**CalculatorBinder**:
The build-time role that resolves CalculatorDefs against a CalculatorCatalog. → [ADR-0005](./adr/0005-build-time-composition.md)
_Avoid_: Weaver, SourceBinder, DerivationBinder

**SourceBinder**:
The build-time role that resolves OfferingDefs against a ProviderCatalog. → [ADR-0005](./adr/0005-build-time-composition.md)
_Avoid_: Weaver, CalculatorBinder, OfferingBinder

**SourceRegistry**:
The bound producer declarations for a ProfileDef, keyed by SourceKey. → [ADR-0005](./adr/0005-build-time-composition.md)
_Avoid_: OfferingRegistry, ProviderCatalog, live Source map

**RegisteredSource**:
One configured producer with its selection priority and storage lattice. → [ADR-0005](./adr/0005-build-time-composition.md)
_Avoid_: Source, OfferingDef, RegisteredOffering

**ProviderCatalog**:
The available Provider plugin declarations, keyed by implementation identity. → [ADR-0005](./adr/0005-build-time-composition.md)
_Avoid_: Provider instance map, Parameter table

**ProviderManifest**:
A Provider plugin's identity, offerings, secret requirement, and construction contract. → [ADR-0005](./adr/0005-build-time-composition.md)

**Tap table**:
A Provider shape's declaration of what it serves and how — per Parameter: the vendor variables it reads, their expected units, the transform that yields canonical values, and the vertical cell it lands on. Narrows to the taps one request engages. → [edge/provider.md](./edge/provider.md)
_Avoid_: Parameter map (ParameterTable is the canonical descriptor table), variable list, schema

**SecretSlot**:
A ProviderManifest's named secret requirement. → [architecture.md](./architecture.md#config-binders-weaver)
_Avoid_: Secret value, API key field

**OfferingSpec**:
A catalog declaration of a named Provider offering and its exact Parameter set. → [architecture.md](./architecture.md#config-binders-weaver)
_Avoid_: OfferingDef, ParameterDef

**StoreSpec**:
The operator or catalog declaration of a Store's configured spatial and retention assumptions. → [architecture.md](./architecture.md#store--one-type-several-positions)
_Avoid_: RootStoreSpec, default lattice

**OfferingDef**:
A profile's enablement and configuration of one catalog offering. → [architecture.md](./architecture.md#config-binders-weaver)
_Avoid_: SourceDef, Source, OfferingSpec, Provider

**ProfileConfig**:
The operator-facing declaration of a profile's offerings, Calculators, root Store, and Arbiter policy. → [architecture.md](./architecture.md#config-binders-weaver)
_Avoid_: Sources, derivations, RootStoreSpec

**ProfileDef**:
The bound build-time definition from which one served profile root is woven. → [ADR-0005](./adr/0005-build-time-composition.md)
_Avoid_: WeavePlan, ProfileConfig

**Weaver**:
The build-time role that constructs a served profile graph from a ProfileDef. → [ADR-0005](./adr/0005-build-time-composition.md)
_Avoid_: Builder, compiler, orchestrator, planner

### Roles

**Embedding surface**:
The supported Python package boundary through which a host application uses Meteoscape's weather capabilities without running a protocol server. Its API shape is unresolved. → [architecture.md](./architecture.md#embedding-surface)
_Avoid_: Internal composition API, headless mode, client SDK

**Edge record**:
The living per-surface seam document between architecture and user-oriented design, aggregating one product edge's status: contract shape, upstream invariants with their validation state, edge-scoped concerns, and staged roadmap. Customer-facing edge descriptions derive from it as subsets. → [docs/edge](./edge/provider.md)
_Avoid_: public API guide (a derivation, not the record), surface spec, contract doc; *edge* alone (the system's outer boundary, not the document about it)

**Gateway**:
The caller-policy boundary in front of a served profile. → [architecture.md](./architecture.md#gateway--caller-policy-boundary)
_Avoid_: Orchestrator, translator

**Manifold**:
The recursive abstraction for a projectable weather space. → [ADR-0001](./adr/0001-manifold-algebra-and-composition.md)
_Avoid_: Repository, orchestrator, tensor

**Leaf Manifold**:
A Manifold backed by its own data substrate. → [ADR-0001](./adr/0001-manifold-algebra-and-composition.md)
_Avoid_: Atomic Manifold

**Composite Manifold**:
A Manifold defined by child Manifolds and a combination rule rather than its own data substrate. → [ADR-0001](./adr/0001-manifold-algebra-and-composition.md)
_Avoid_: ManifoldProduct, operation, combinator

**Calculator**:
A composite producer that derives a co-produced output group from inputs and participates in Arbiter selection. → [ADR-0004](./adr/0004-producer-resolution-and-capability.md)
_Avoid_: Formula node, DewpointManifold, derivation

**Countable**:
The property of a materialized result whose Domain can be enumerated. → [ADR-0001](./adr/0001-manifold-algebra-and-composition.md)
_Avoid_: Node-Countable, Enumerable, browsable, indexed

**Writable**:
The Manifold facet that accepts materialized Coverage. → [ADR-0001](./adr/0001-manifold-algebra-and-composition.md)
_Avoid_: Materialized, Scratchboard, ManifoldCache

**Store**:
The Writable substrate owned by a Reservoir, holding independently replaceable per-Parameter units on private lattices. → [ADR-0006](./adr/0006-materialization-granularity-and-store-shape.md)
_Avoid_: Cache, buffer, vault, pool

**Reservoir**:
A retention composite formed from a Store and one child Manifold. → [architecture.md](./architecture.md#reservoir)
_Avoid_: Cache, CachingManifold, keeper, sentinel

**Task-oriented profile**:
A named root composition that resolves requests under one objective. → [architecture.md](./architecture.md#guiding-principles)
_Avoid_: View, mode, pipeline

**Best view**:
The task-oriented profile whose objective is best-obtainable source with fallback. → [architecture.md](./architecture.md#reservoir)
_Avoid_: Best provider, router result

**Capability**:
What a Manifold declares it can serve: its Parameters, the Domain it serves each of them over (its Reach), and an admission predicate that may be stricter than that Domain. → [ADR-0004](./adr/0004-producer-resolution-and-capability.md), [ADR-0007](./adr/0007-capability-carries-its-domain.md)
_Avoid_: Coverage, clause

**Footprint**:
One producer's declared spatial, vertical, and valid-time span — a leaf's own Reach, and the unit composition works from. Interpreted by `serves`. → [ADR-0004](./adr/0004-producer-resolution-and-capability.md)
_Avoid_: Coverage, grid

**Reach**:
A **Manifold's** per-Parameter Domain — the Domain its Capability publishes. The profile's Reach is the woven root's; a Calculator's input Reach is its scoped Arbiter's. Composed from the children's, never synthesized, so it is **tight**: exact in any profile that composes, since one that would be looser fails the build. → [ADR-0007](./adr/0007-capability-carries-its-domain.md)
_Avoid_: Range, limit, horizon (a projection of Reach, not Reach); envelope (the narration, not the Domain); footprint (a producer's own, before composition)

**Arbiter**:
The composite that resolves competing producers per Parameter under a Reconciler. → [ADR-0004](./adr/0004-producer-resolution-and-capability.md)
_Avoid_: Selector, dispatcher, router, resolver, Gateway

**Reconciler**:
The per-Parameter policy for combining an Arbiter's competing producers — it both ranks them and composes the Reach the combination publishes, since how producers combine is what the combination serves. As built it orders candidates and the Arbiter picks the first admitted (combining reconcilers need a wider interface → [#28](./concerns.md#28-reconciler-interface-selection-ordering-vs-per-cell-fold)). → [ADR-0004](./adr/0004-producer-resolution-and-capability.md), [ADR-0007](./adr/0007-capability-carries-its-domain.md)
_Avoid_: Mosaic, combiner, stitcher, merger, tiler

**Provider**:
A leaf Manifold that adapts one external weather-data producer into Meteoscape semantics. → [architecture.md](./architecture.md#provider-leaf-manifold)
_Avoid_: Vendor, backend, driver

**Probe**:
The vendor-facing intake a Provider drives: it obtains one producer's raw readings and interprets none of them. Paired with the Provider shape that resolves geometry, converts, and assembles around it. → [edge/provider.md](./edge/provider.md)
_Avoid_: Core, intake, sonde, client, adapter; Transport (the HTTP seam a Probe uses, one layer below)

**Provider parity check**:
An independent comparison between a single-Provider Meteoscape profile and that external producer's reference response for the same request. → [edge/provider.md](./edge/provider.md)
_Avoid_: Truth check, accuracy test, Provider unit test

**Collector**:
The operator-owned external service that continuously captures vendor forecasts and station observations into the operator's database, which Meteoscape's archive sources project over read-only. Its schema is an external contract Meteoscape adapts to but does not own. → [#45](./concerns.md#45-the-collector-schema-is-a-contract-meteoscape-depends-on-but-does-not-own)
_Avoid_: Scraper, harvester, ingester; archive (the accumulated data, not the process that accumulates it)

**Source**:
The role of a Reservoir that serves retained data or fetches it from one Provider. → [architecture.md](./architecture.md#source)

**Producer**:
A ranked candidate an Arbiter selects over for a Parameter — a live node (a Source or a Calculator) paired with a `ProducerKey` identity (`SourceKey | CalculatorKey`). → [ADR-0004](./adr/0004-producer-resolution-and-capability.md)
_Avoid_: candidate, node

**Normalization**:
The Provider-owned translation from vendor semantics to Meteoscape semantics without changing native geometry. A **role, not a type**: the vendor leaf *declares* it as a Tap table and the Provider shape wrapper *executes* it. → [architecture.md](./architecture.md#normalization-vs-homogenization), [edge/provider.md](./edge/provider.md)
_Avoid_: Normalizer (there is no such object — declaration and machinery are separately owned)

**Native record**:
A co-domained Coverage materialized by one fetch for Parameters that share native geometry. → [ADR-0006](./adr/0006-materialization-granularity-and-store-shape.md)
_Avoid_: Z-group, raw response

**Homogenization**:
The geometric or temporal sampling of a Field onto a target EnumerableDomain so its ParameterData are conformable. → [architecture.md](./architecture.md#normalization-vs-homogenization)
