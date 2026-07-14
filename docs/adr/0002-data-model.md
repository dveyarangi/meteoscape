---
status: accepted
---

# Data model — domains, coverages, parameters

The concrete encoding of everything that flows through the [algebra](./0001-manifold-algebra-and-composition.md):
the **`Domain` / `Selection`** (the *where*), the **`Coverage` / `ParameterData`** (the data), and the
**parameter** itself (the *what* — quantity, statistic, extent). It fixes the structural slots while
allowing concrete profiles to use only the representations they need. The provenance plane a
`Coverage` carries is owned by
[ADR-0003](./0003-provenance-and-origin.md); how producers are matched and resolved is
[ADR-0004](./0004-producer-resolution-and-capability.md).

## The shape

```mermaid
classDiagram
    class Manifold {
        <<interface>>
        project(Selection) Manifold
    }
    class Selection {
        Domain domain
        frozenset~ParameterId~ parameters
    }
    class Domain {
        <<abstract>>
        contains(Domain) bool
        intersect(Domain) Domain
    }
    class EnumerableDomain {
        <<abstract>>
        get(i) Point
        len() int
        enumerate() Iterator~Point~
    }
    class Separable {
        <<facet>>
        axis(AxisName) Axis
    }
    class Axis {
        AxisName name
        extent() Interval
    }
    class EnumerableAxis {
        get(i) Cell
        len() int
    }
    class Cell {
        Coordinate coordinate
        Interval | None bounds
    }
    class Coverage {
        EnumerableDomain domain
        capability() Capability
        ranges() Map~ParameterId, ParameterData~
        provenance() ProvenanceField
    }
    class Capability {
        Map~ParameterId, ParameterDef~ parameters
        serves(ParameterId, Domain) bool
    }
    class FootprintCapability {
        Map~ParameterId, (ParameterDef, Domain)~ footprints
    }
    class ParameterData {
        float[] values
        bool[] | None present
    }
    class ParameterDef {
        ParameterId id
        Quantity quantity
        Unit canonical_unit
        CellStatistic statistic
    }
    class Quantity {
        str name
        ExtentScaling extent_scaling
        MeasurementScale scale
    }
    class ProvenanceField {
        summary(ParameterId) Provenance
        at(ParameterId, i) Provenance
    }

    Manifold <|.. Coverage : is-a
    Selection o-- Domain : where + which
    Domain <|-- EnumerableDomain : enumerable refinement
    Domain <|-- Separable : facet (GridDomain)
    Separable o-- Axis : 4 axes
    Axis <|-- EnumerableAxis : enumerable refinement
    EnumerableAxis o-- Cell : sequence (RegularAxis computes, explicit stores)
    Coverage o-- EnumerableDomain : carries (re-projectable)
    Coverage o-- Capability : descriptor block (materialized: ParameterDef x Domain)
    Capability o-- ParameterDef : one per parameter (keyed by id)
    Capability <|.. FootprintCapability : leaf (Domain private to serves)
    ParameterDef o-- Quantity : identity root (entails extent_scaling, scale)
    Coverage o-- ParameterData : one per parameter (keyed by id)
    Coverage o-- ProvenanceField : provenance plane, parameter × point (ADR-0003)
    ParameterData ..> EnumerableDomain : values + present positional to enumerate()
```

## Domain & Selection

- **`Domain` is an interface; representations vary behind it.** A `Domain` is an abstract coordinate set
  over the **4 axes** (3 spatial + `valid_time`) whose **universal** surface is just the set-algebra —
  `contains` / `intersect` (the Capability filter) — with **nothing in it assuming the axes are
  separable**. **Enumeration is the `EnumerableDomain` refinement** (`enumerate` / index / `len`), so
  *being* one is the enumerability discriminator — a continuous `region` Domain never claims it. The
  contract defines two concrete representations; the interface admits richer ones without changing the interface:
  - **`GridDomain`** — a `Mapping[AxisName, EnumerableAxis]`, **mixed** per axis: `RegularAxis` on
    X/Y/T, and on Z a `VantageAxis` (request / result aperture), a count-1 `RegularAxis` (native
    sample level), or an `IntervalAxis` (native column cell). This is the enumerable representation;
    index math uses only `len` / `[]`, so mixed axes need no new arithmetic. (Was `RegularDomain`,
    uniform-only; widening it subsumes `RectilinearDomain` — explicit-cell axes are just
    non-`RegularAxis` `EnumerableAxis` members of the same mapping.)
  - **`FootprintDomain`** — a separable provider reach, **never claiming enumerability** (even when its
    Z axis is an enumerable `IntervalAxis`): per-axis **extent** declarations of mixed kind — a
    **`ContinuousAxis`** on X/Y (region reach — the only continuous axes left), the clock-anchored
    **`RollingAxis`** on `valid_time` (`extent = [A, A + max_lead]` around the run anchor `A` — the
    provider's cadence, [ADR-0003](./0003-provenance-and-origin.md)), and on **Z** either a **point
    cell** (`RegularAxis` count-1, e.g. `[2,2]`; count-N declares multiple sample levels) or a
    **statistic-cell span** (`IntervalAxis`, e.g. `[0,TOA]` cloud). The footprint declares only
    extents; admission is the **request-side** gate `requested.matches(declared)` (`VantageAxis` →
    `intersects`, default → `contains`, [ADR-0004](./0004-producer-resolution-and-capability.md)), so
    `contains` reads each declared axis's `.extent`, never its kind. Its `RollingAxis` makes the reach
    **clock-relative** — the one intentional exception to Domain-as-pure-geometry, isolated to this
    representation — so the Capability filter tracks a rolling horizon while `serves` stays a plain
    `contains` ([#18](../concerns.md#18-clock-anchored-footprint-fidelity)).
  - **`CurvilinearDomain`** — deferred non-separable geometry (radar geotangent slice, satellite
    swath); the base interface deliberately leaves room for it
    ([#12](../concerns.md#12-curvilinear-domains)).

- **Separability is a facet; enumerability and regularity are per-axis choices.** Mirroring the
  algebra's *capabilities, not subtypes*: per-axis decomposition is the one optional facet a
  **separable** representation exposes — its per-axis `Axis`. An **`Axis` mirrors `Domain`**: its
  universal surface is a span (`extent`), and **enumeration is the `EnumerableAxis` refinement** — a lazy
  `Sequence[Cell]` (`axis[i] -> Cell`, `len`). Regularity is a choice *within* an enumerable axis: a
  `RegularAxis` generates its cells from `(anchor, step, count)` and stays snappable; an explicit one
  stores them. Whether a `RegularAxis` generates **bounded** cells (each spanning one step,
  `bounds = [coord, coord + step]`) or bare **instants** (`bounds = None`) is its **`cellular`** flag — the
  generative counterpart of a `Cell`'s optional `bounds`: it is how the shared `valid_time` axis emits the
  hourly `bounds` an **extensive** parameter reads as its accumulation extent, while an intensive parameter
  samples the tick and ignores them. A single-cell **`IntervalAxis`** is the enumerable encoding of one
  **span cell** (`extent == bounds == its interval`, one cell) — the native column (`[0,TOA]`) and the
  base of the request **`VantageAxis`** (which only overrides `matches`); a span has no `RegularAxis`
  form (it is not `(anchor, step, count)`, so no `step = inf`/`nan`). A **continuous** axis carries only
  its bound — a plain `ContinuousAxis` (X/Y reach) or a clock-anchored `RollingAxis` (`valid_time` reach) —
  a `FootprintDomain`'s X/Y and time axes. Curvilinear domains satisfy the base interface without being
  separable. **Only a regular axis can be snapped-to.**

- **Mode is the Domain's shape, not a separate field** — `region` / `snapped` / `exact` are *which kind
  of Domain* you built, so **`Selection = Domain + parameters`** (no redundant `mode` field that could
  disagree with the Domain):
  - **Continuous** (`region`) — bounds, no discretization → projects to a **field**.
  - **Snapped** — regular **step** fixed, anchor / extent open → resolvable against a declared grid.
  - **Enumerable** (`exact`) — concrete coordinate set (regular-anchored or irregular point set) →
    a materialized (countable) Coverage result.

- **One regular descriptor unifies snapped / declared-grid / exact.** A regular lattice is
  `{anchor, step, extent}`; its members differ only in which parts are fixed — **Snapped** fixes `step`
  (+ request bounds), a **declared grid** fixes `anchor + step` (extent open), an **exact** lattice
  fixes all three. So a declared grid is just the **anchored-regular member** — **provider-exact where a
  vendor declares a lattice, a configured guess for point vendors that expose none** — and the read-back
  resolution `snapped → exact = step(request) ⊕ anchor(grid) ⊕ bounds(request)` keeps **`bounds(request)`**.
- **Grid alignment is per storing node and per axis, and splits into two opposite-extent steps.** A
  `Reservoir`'s `Store` **`quantize`s** a request for **retention** — **per axis**: an axis with a
  declared lattice snaps onto it **and widens the extent outward to whole assimilable units**, so the
  retrieval shape **encloses** the request (extent **≥** request; the rounding is the store lattice's
  own business); an axis **without** a declared lattice (for example, Z) **passes through identity**, its cell
  becoming part of the unit key
  ([ADR-0006](./0006-materialization-granularity-and-store-shape.md)). At
  **read** the `Reservoir` **homogenizes** the stored cells back onto the requested `Domain` — extent
  **=** request (`snapped → exact` above) — so `project(sel)` always returns a Coverage on `sel.domain`
  ([ADR-0001](./0001-manifold-algebra-and-composition.md)). Resolving to the caller's exact output is the
  **read-back, not the `Store`'s job**; the two steps move extent in **opposite directions** (quantize
  widens past the request, read-back crops back to it). The per-axis snap is `quantize`'s internal
  mechanism (no standalone operation): an open-anchor regular axis borrows the grid's anchor (the
  `valid_time` case), a **concrete coordinate snaps to its nearest grid node** (the lat/lon case);
  `issue_time` is not requested, so it is never snapped. A request's **mode** (Snapped vs Enumerable) may
  be resolved at the edge, but **internal nodes are handed enumerable (store-shaped) Selections**, never
  Snapped. Store lattices are **private to the `Store`** and **emergent per node**; there is no global
  lattice config and no public node `domain`.

- **`issue_time` is a provenance stamp, not a Domain axis.** The per-Coverage / per-request `Domain`
  has **4 interpolable axes** (3 spatial + `valid_time`); `issue_time` (the forecast issuance a value
  came from) is **never interpolated, never snapped, never in a request**, so it is **not** a coordinate
  the caller navigates — it is **run identity carried on the atomic `Origin`**
  ([ADR-0003](./0003-provenance-and-origin.md)) and the basis of freshness (run currency).
  The 4 axes are therefore all **field axes** (resamplable dimensions); **no categorical axis sits in
  the core**. Whether a given *parameter* may be resampled along an axis is its **resampler** fact (its
  `scale`; see *Parameters*), not an axis property. The **categorical-key mechanism** (select / group,
  never interpolate) survives as a **collection-layer seam** — the home of `issue_time` *archives* and
  **ensemble / scenario** keys — not a core field axis. **Cross-run combination** is then a **reconciler
  folding run-stamped contributor Coverages along `valid_time`**
  ([ADR-0004](./0004-producer-resolution-and-capability.md)), yielding a synthetic origin — *not* an
  axis to interpolate.

- **The vertical (Z) axis carries one `vertical_reference`; the coordinate stays a plain scalar.** Z is one
  of the 3 spatial axes — an ordinary field axis of `Cell`s whose `coordinate` is a plain scalar like every
  other axis — and the **`vertical_reference` is an attribute of the Z *axis* representation** (one per
  Domain, since a Domain carries one Z axis), **not** part of the coordinate. The reference is one of
  **`above_ground`** (datum = the terrain surface; the home of near-surface offsets like 2 m / 10 m),
  **`isobaric`** (pressure levels), **`height_above_msl`**. These references are **not linearly comparable**
  — `2 m above_ground` and `1000 hPa` relate only through physics (surface pressure, hydrostatics) — so a
  single Domain's Z axis carries **one** reference, and **stacking references is a `Calculator`** (a
  reinterpolation), never a free axis read.
  *(Amends the original `(reference, value)` pair-coordinate framing — see
  [Considered options](#considered-options): the reference is axis-level, so `Coordinate` stays
  `float | datetime` and only the Z-axis representation grows a field.)*

- **Level vs layer is the `Cell`'s `bounds`, like everywhere else.** A thin Z `Cell` (`bounds = None`)
  is a single level / offset; a **fat** Z `Cell` carries `bounds` spanning a layer — `[~0, 10 m]
  above_ground` (the near-surface layer) or `[1000, 850] hPa`. A near-surface request *is* that fat cell:
  `temperature` (2 m) and `wind_u` (10 m) both land in it, each contributing its native near-surface
  value, the differing offsets **absorbed into the cell's `bounds`** ("vertically unresolved across the
  layer") — not a wasteful multi-level Domain with a sparse `present` mask. The cell's `coordinate`
  (a nominal near-surface height) sits *within* those `bounds` by convention, the same independence
  every axis's `Cell` already has. Projecting onto a Z cell is vertical **homogenization** — the exact
  analog of the temporal / spatial kernel; coarsening to a fat cell absorbs offsets, sampling to a thin
  cell interpolates (extent-scaling–aware).

- **Request Z carries the mode as an axis kind: `VantageAxis` = vantage, `RegularAxis` cell = exact.**
  The near-surface bundle **request** is a vantage
  aperture, and its cell survives as the served Coverage's Z cell by closed projection, offsets
  absorbed into its `bounds`).* A **`VantageAxis`** — a single-cell **`IntervalAxis`** that overrides
  `matches` with overlap — is **vantage mode**: the asker's position/acceptance window (`[0, ~10 m]`
  for the default bundle), authored at the edge (the consumer owns the tolerance). An **exact** Z cell
  is **cell-addressing mode** — a count-1 `RegularAxis` for a precise level (`{2 m}`) or an
  `IntervalAxis` for a layer (`[0, 2 km]`), the shape the edge alias table desugars to
  (`temperature_2m`, `cloud_cover_low`, `soil_temperature_6cm`). The `VantageAxis` lives on the `Selection`; **closed projection rides it
  onto the returned Coverage** (`resample` sets `domain = selection.domain`) — it never appears in a
  capability footprint (providers declare native Z), and once on a Coverage it sits on the *declared*
  side of a subsequent match where only its `.extent` is read, so its inverted predicate never leaks
  (re-querying a materialized vantage Coverage with a precise Z remains a deferred concern).
- **Admission is a request-side per-axis gate — `requested.matches(declared)`, with `VantageAxis`
  using `Interval.intersects`** (overlap), the default axis using `contains` (request inside the
  footprint) → [ADR-0004](./0004-producer-resolution-and-capability.md). Declarations stay **native
  facts** (a sample level; a statistic's served cells — cloud low/mid/high are *cells of one
  functional*, never `ParameterId`s). Against a point sample `intersects` **is** membership; against a
  column it **is** inclusion — one predicate, no per-declaration branch. *Which* admitted cell answers
  (maximal served cell / resampler) is a separate selection step, deferred with layers (ADR-0004).

  Every miss is an honest per-parameter omission (`capability-mismatch` reason at the edge). The
  response always rides `sel.domain` (closed projection): the served Z cell is the requested window,
  native levels/cells staying in the native records
  ([ADR-0006](./0006-materialization-granularity-and-store-shape.md)).
  **Enumerable vantage encoding:** the whole request Domain stays enumerable, so the vantage window rides as the
  request's **fat Z `Cell`** (`bounds` = the window; a point request cell is the exact/addressing
  dual) — a fully Continuous Z shape remains the general vantage form. Matching treats a fat request
  cell as the window; fat-cell-as-exact-*layer* addressing requires layer aliases and the Continuous
  form to disambiguate.

- **Resampling a parameter onto an axis is its `resampler`, entailed by `(scale, statistic,
  extent_scaling)` and asymmetric.** **Refine up** follows the measurement **scale** — `linear`
  interpolates to any tick, `circular` is angular, categorical fills / snaps; **coarsen down** follows
  the **statistic** — whole, phase-aligned integer-multiple aggregation (`sum` for extensive,
  `max` / `min` / `mean` for windowed), never disaggregation. So interpolability is a **parameter**
  fact, not an axis one. The matching half (does a **lossless** path exist) lives with Capability
  ([ADR-0004](./0004-producer-resolution-and-capability.md)); the kernel **implementations** (a
  registry, the mirror of reconcilers) and any **lossy** tier stay deferred
  ([#5](../concerns.md#5-read-time-homogenization-fidelity), [#7](../concerns.md#7-quality-scoring)).

## Coverage & ParameterData

- **A Coverage carries its Domain, its `capability`, and values positional to the Domain.** `Coverage
  = (EnumerableDomain, Capability, {parameter: ParameterData}, ProvenanceField)` — the Coverage
  *contains* the one `EnumerableDomain` (so it is a re-projectable `Manifold`), its **`capability`**
  (the `ParameterDef` per parameter × that Domain — the self-describing **descriptor block**, capability
  being exactly parameters × Domain), one
  `ParameterData` per parameter, and a `provenance` plane (below); `values[i]` is the value at the i-th
  `Point` of `domain.enumerate()`. **No coordinates are duplicated** in a `ParameterData` ("a Coverage
  is a Selection filled with data," literally). **Flat packing order is specified:**
  `ParameterData.values[i]` is positional to `EnumerableDomain` enumeration under the canonical
  nesting **X → Y → Z → T, T fastest-varying** (row-major). Index arithmetic lives only in the Domain
  and the sampling engine (discipline rule). Array *backing* (numpy/xarray, N-D views) stays deferred
  behind the `ParameterData` interface — only the positional order is locked. The per-parameter element
  is **`ParameterData`**, not "range" — that reads
  as an interval, colliding with a `Cell`'s `bounds`. `capability` / `ranges` / `provenance` share one
  parameter key set. Co-domain is an invariant of this **exchange record** only — a producer's fetch
  materializes into one record **per set of parameters sharing a native Domain**, and stores retain
  per-parameter units ([ADR-0006](./0006-materialization-granularity-and-store-shape.md)).

- **`ParameterData` is pure numbers `(values, present)`; every descriptor is id-entailed.** The slice
  does **not** restate its own `ParameterId` (the `ranges` map key) and carries **no** descriptors at
  all. Under the **canonical-mono-unit invariant** (*Parameters* below) every fact that interprets the
  numbers — `quantity`, `extent_scaling`, `unit`, `statistic` — is *entailed by the parameter's
  identity*, so it has exactly one home, the `ParameterDef`. A tableless reader interprets the slice
  through the Coverage's own **`capability`** (`capability.served[pid][0].canonical_unit` /
  `.statistic` / `.quantity` / `.extent_scaling`); the global `ParameterTable` is not needed at read. This
  mirrors CoverageJSON, where a `range` carries minimal value facts and the `parameters` block carries
  the descriptors — here those descriptors **travel with** the Coverage inside its `capability`.

- **The descriptor block is carried, not resolved.** A Coverage is **self-describing**: it embeds its
  `capability` (the `ParameterDef` per parameter × Domain) so a stored / serialized / inter-node Coverage
  interprets standalone without the injected `ParameterTable` — the same `(parameters × Domain)` shape as a
  `Selection` and a `Capability` clause set. The descriptors are id-entailed canonical facts, so there
  is no per-slice denormalization to drift out of sync; the block is the one place they ride.

- **Nodata is an explicit per-parameter mask.** `present: Sequence[bool] | None`, positional to
  `values`: `present[i] is False` ⇒ **nodata** at that point (a *successful* gap — 0 contributors, not a
  fault, [ADR-0004](./0004-producer-resolution-and-capability.md)); `present is None` ⇒ all cells
  present (the elided common case). An explicit boolean mask — **not** a NaN sentinel — because it is
  dtype-agnostic (categorical / integer parameters can't carry NaN) and keeps "no data" distinct from a
  legitimate not-a-number value. Per-parameter, since each parameter's coverage footprint differs.

- **A parameter's extent → the optional `bounds` on each axis `Cell`.** An axis is a `Sequence[Cell]`,
  and a `Cell` pairs its representative `coordinate` with optional `bounds: Interval`; `bounds is None` ⇒
  the coordinate is an **instant / point**. The two are independent — the `coordinate` sits within the
  `bounds` by convention (centre, or an edge for period-ending accumulations), never by definition. It
  generalizes to all axes uniformly (a spatial cell is the product of per-axis intervals). Cells live on
  the **`Separable` facet**, not the base `Domain` (non-separable per-cell bounds are the deferred
  curvilinear case). So the statistic / integration window for `values[i]` — an extensive parameter's **extent** — is
  the shared `valid_time` axis cell's `bounds`, stated **once** on the Domain, read by every parameter.

- **Provenance is a Coverage-level plane, owned by [ADR-0003](./0003-provenance-and-origin.md).** Not a
  `ParameterData` attribute: origin varies over **two** axes — **parameter** (the Arbiter picks a source
  per parameter) and **geometry point** (a mosaic differs per cell) — so it is a `ProvenanceField` on
  the `Coverage`, peer to `domain` and `ranges`, indexed `at(parameter, i)` with `summary(parameter)`
  the O(1) per-parameter freshness handle. Keeping it off the slice is what lets the Arbiter assemble
  one Coverage from many single-origin sources without rewriting each slice.

## Parameters — quantity, statistic, extent

- **Quantity is the identity root, carrying an `extent_scaling`.** A parameter's identity root is a
  physical field — its **quantity** — whose **`extent_scaling ∈ {intensive, extensive}`** is its
  relationship to a cell's temporal extent, and sets which statistics are meaningful:
  - **Intensive** — instantaneous, **extent-independent** (temperature, rain-rate, pressure, wind).
    Window statistics apply; **extent optional**.
  - **Extensive** — **additive**, the value is the **integral over the cell extent** (precipitation,
    snowfall, radiant energy). **Extent required**; values sum across adjacent cells.
  `extent_scaling` is not a units claim: rain-rate `mm/hr` carries a time unit yet is intensive
  (window-independent); precip `mm` carries none yet is extensive (3h > 1h).

- **Measurement scale selects the refine-up resampler.** `Quantity.scale ∈ {linear, circular, nominal,
  ordinal}` — `linear` interpolates / averages, `circular` is angular, categorical scales fill / mode /
  priority. **Wind is canonical as its u/v (eastward / northward) components** — both `linear`, so
  linear interpolation of u/v *is* correct wind interpolation and **speed / direction are derived
  views** (Calculators above u/v), keeping the coupling out of per-parameter resamplers. Provider-facing
  catalogues may remain linear while derived views use the declared non-linear scales.

- **Units are canonical and mono per parameter — the interior is unit-blind.** Each parameter has
  **exactly one** unit, `ParameterDef.canonical_unit`; every value of that parameter, everywhere in the
  algebra, is in that unit. Unit is therefore **id-entailed**, never a navigable degree of freedom: it
  is *not* in the parameter key, *not* in a `Capability` clause (a vendor emitting °F is the same
  parameter, not a different one), and *not* in a `Selection`. Unit conversion happens at **exactly two
  boundaries** — the Provider's **Normalizer** on ingest (vendor unit → canonical, write-time, in the
  data) and the **surface adapter** on egress (canonical → a requested presentation unit, read-time,
  when presentation conversion is offered). In between, the whole tree —
  Capability matching, the Arbiter's fold, Calculators, the `Store` — is **unit-blind**: physics relies
  on the canonical *convention*, never a runtime conversion. The concrete canonical-unit choice per
  parameter is a deferred **parameter convention** ([#10](../concerns.md#10-parameter-conventions)).

- **The two cell axes, split by dimension.** A cell's value statistic is two independent things:
  - **`CellStatistic = point | max | min | mean`** — a **window statistic**, *dimension-preserving*
    (mean temp is K, peak intensity is mm/hr); lives on `ParameterDef`, surfaced via the Coverage's
    `capability` (descriptor block); `point` is the degenerate window (an instant). The Provider's
    Normalizer coerces vendor data to the canonical statistic, so it is not a freely-chosen runtime
    value.
  - **Calculus depth** — *dimension-changing* (`∫ rate dt → accumulation`, `mm/hr·h → mm`); this is the
    quantity `extent_scaling`, **not** a `CellStatistic` value. Accumulation is the **integration edge**
    between an intensive `rate` quantity and its extensive integral (e.g. rain-rate ↔ precipitation) — a
    vocabulary-declared quantity pair, not a third value.

- **Extent never enters the parameter key.** Extent is carried by the Domain's `valid_time` `Cell` `bounds` (above). So the
  **materialized / requested parameter key = `(quantity, statistic)`**; "3h precipitation" = parameter
  `precipitation` over a Domain whose `valid_time` cells are 3h wide — one shared axis serving parameters
  of different temporal meaning.

- **A parameter is a functional `statistic(quantity)`; requests name it explicitly.** The window
  statistic + quantity form the key; the **extent is requested through the Selection's `valid_time`
  cells**, never in the parameter name. Ergonomic **aliases** (e.g. `precip_3h`) are **surface sugar**
  that desugars at the edge into *(parameter `(precipitation, ·)`, valid_time cells = 3h)* — the on-ramp
  to formula injection, **not** a second identity. A surface may accept a bare quantity name as
  `point(quantity)`.

- **An extensive quantity's extent is producer-intrinsic.** Unlike an intensive quantity (resampleable
  to any tick), an extensive quantity has a native extent (period + phase) only coarsenable by aligned
  additivity. That native extent is a **per-parameter Capability fact**
  ([ADR-0004](./0004-producer-resolution-and-capability.md)), carried by the `Store`'s declared grid and
  the returned Coverage's `valid_time` `Cell` `bounds`. A request for an unreachable extent (1h from a 3h
  producer, a shifted phase, instants) is simply **`capability-mismatch`** — no disaggregation machinery.

- **A surface parameter's height is a Domain Z coordinate, not the key — `temperature_2m` is an alias.**
  Like extent, vertical position rides the Domain (its Z `Cell`), never the parameter key:
  `temperature_2m` / `wind_u_10m` are **aliases** desugaring at the edge into *(quantity
  `air_temperature` / `eastward_wind`, statistic `point`, Z = `2 m` / `10 m` above_ground)* — the
  materialized key stays `(quantity, statistic)`. A producer's **native vertical offset** is a
  per-parameter **Capability** fact, exactly parallel to an extensive quantity's native **extent**
  `{period, phase}` ([ADR-0004](./0004-producer-resolution-and-capability.md)): the request's Z cell
  (a fat near-surface layer or a specific level) is matched against it and sampled onto. A 2 m diagnostic
  joined onto a pressure column is the cross-reference `Calculator` (above).

## Why

- One Domain interface with swappable representations keeps the common case (a uniform hourly lattice)
  trivial while leaving curvilinear radar reachable without reshaping consumers — the Arbiter's fold,
  homogenization, and serialization bind to the interface, not a representation.
- Folding mode into the Domain removes a redundant field and makes illegal states unrepresentable; the
  single regular descriptor collapses request-snap / store-grid / exact-lattice into one parameterized
  shape, so snapping is an algebraic combine, not special-case code.
- Putting **extent on the Domain** keeps coordinates in one place and lets a single shared axis serve
  parameters of different temporal meaning; carrying the **`capability`** (its descriptor block) keeps a
  Coverage self-describing without the global `ParameterTable`, which the stateless-Provider /
  store-and-flow model needs — while `ParameterData` stays pure `(values, present)`, so there is no
  id-entailed fact denormalized onto the slice to drift.
- **A canonical-mono-unit interior** collapses unit handling to two edges (Normalizer ingest, surface
  egress) and leaves the entire algebra unit-blind: Capability, the Arbiter's fold, and Calculators
  never negotiate or convert units, so a derived parameter's formula is unit-safe by *convention*.
- **Vertical position on the Domain (not the key)** is the same move as extent: `temperature_2m` is an
  alias, height is a Z `Cell`, and a near-surface bundle of mixed offsets is one **fat** Z cell — so the
  vertical axis reuses the whole `Cell` / `bounds` / Capability apparatus instead of inventing a
  parameter-side height. The 3-D column and pressure-level products are then reachable purely additively
  (materialize the Z axis; cross-reference joins are Calculators).
- **Provenance as a Coverage plane** (not a per-slice field) lets the Arbiter assemble one Coverage from
  many single-origin sources, and a mosaic vary origin per point, without reshaping `ParameterData` —
  while `summary(parameter)` keeps the common per-parameter freshness read O(1).
- **Quantity-as-root + `extent_scaling`** explains *why precipitation differs from temperature* — how the
  value scales with extent (integration depth), not a special enum value — and keeps units honest (the
  dimension change rides the quantity edge, not a cell attribute). Splitting the cell axes stops `sum`
  masquerading as a peer of `max` / `min`: a statistic and an integral are categorically different and
  per-level exclusive over a single extent ("daily max of hourly accumulation" is a two-window calculator
  chain).
- An explicit `present` mask makes partial coverage representable from day one without retrofitting the
  value layout when partial producers or coverage reconcilers are introduced.

## Considered options

- **Keep `mode` as an explicit `Selection` field.** Rejected: it restates the Domain shape and the two
  can disagree (a snapped flag on an irregular point set). *(Reversible as a derived accessor.)*
- **A single separable (per-axis product) Domain as the base type.** Rejected: bakes separability into
  the contract, excluding curvilinear geometries; separability is a facet.
- **Keep `issue_time` as a 5th (categorical) axis.** Rejected: it is never interpolated, snapped, or
  requested, so it is a **phantom axis** that double-accounts with the provenance run stamp. Demotion
  keeps **cross-run / forecast-convergence** expressible — cross-run is a **reconciler over run-stamped
  contributors** ([ADR-0004](./0004-producer-resolution-and-capability.md)) and convergence a **derived
  enumerable view** over those contributors, both with `issue_time` as a stamp. The categorical-key
  shape survives as a **collection-layer seam** (archives, ensemble, scenario). *(Reversible: restore the
  axis if a native 2-D `valid_time × issue_time` Coverage is ever wanted.)*
- **The vertical reference as part of the coordinate — `(reference, value)`.** Originally recorded that
  way; **amended**. The reference is one-per-Domain (hence one-per-Z-axis), never varies cell to cell, and
  is never interpolated, so pairing it into every coordinate would tax `Coordinate` (forcing it past
  `float | datetime`) and every axis for a Z-only fact. It moves to an **attribute of the Z-axis
  representation**; coordinates stay plain scalars, and the whole `Cell` / `bounds` apparatus is untouched.
  *(Reversible: restore the pair if a single Domain ever needs to mix references on one axis — but
  cross-reference conversion is modeled as a `Calculator`, so the axis carries exactly one.)*
- **A single per-parameter `cell_method` carrying both statistic and extent.** Rejected: duplicates the
  extent into every `ParameterData` and can disagree with the Domain — split extent (Domain) from
  statistic (parameter).
- **Clone descriptors (`unit` / `statistic`) onto `ParameterData`.** Rejected: under the
  canonical-mono-unit invariant these are *id-entailed* canonical facts, identical for every value of
  the parameter — denormalizing them onto each slice is pure redundancy with a drift risk and re-opens
  "why this id-entailed fact on the slice and not `quantity` / `extent_scaling`?". The slice stays pure
  `(values, present)`; the descriptors ride the Coverage's `capability` once.
- **Resolve descriptors from the injected `ParameterTable` instead of carrying them.** Rejected: a
  stored / serialized / inter-node Coverage would not interpret standalone — it would couple every
  reader to the live catalog. Carrying the `capability` (the `(parameters × Domain)` shape a
  `Selection` and a `Capability` already use) makes the Coverage self-describing; it is the link,
  and `ParameterData` never restates its `ParameterId` (the `ranges` map key — restating it invites
  key/value disagreement and diverges from CoverageJSON, where a `range` does not repeat its id).
- **Unit polymorphism inside the algebra (per-slice or requestable units).** Rejected: it would push
  unit awareness into Capability matching, the Arbiter's fold, and every Calculator. Canonicalizing at
  the Provider edge and converting for presentation at the surface edge keeps the interior unit-blind.
- **Provenance as a per-`ParameterData` attribute.** Rejected: origin varies by *both* parameter and
  geometry point, and the Arbiter assembles one Coverage from many sources, so provenance is a
  Coverage-level plane (above), not a field on each slice.
- **NaN sentinel for nodata.** Rejected: only works for float-valued data and conflates "no data" with a
  legitimate not-a-number value.
- **A literal `CellIntegration` peer enum beside `CellStatistic`.** Rejected: integration is
  dimension-changing and per-level-exclusive with window statistics, so it is truer as the quantity
  `extent_scaling` than a per-cell attribute.
- **Extent in the parameter key — `statistic(quantity, extent)`.** Rejected: the Domain already owns extent;
  putting it in the key too makes "extent" sayable in two places that can disagree. Aliases give the
  ergonomic bundling without the second source of truth.
- **Statistic not part of identity (one quantity, many cell-methods at read).** Rejected for the
  *materialized key* — `max(temp)` and `mean(temp)` must coexist in one Coverage — but reconciled: the
  **identity root** is the quantity, the **materialized key** is `(quantity, statistic)`.

## Consequences

- The **materialized key is `(quantity, statistic)`**: "instantaneous temperature" and "daily-max
  temperature" sit at different keys, not one parameter with two cell-methods.
- **Mixed *periods* of one parameter in one Coverage are not yet representable** — `precipitation` over
  1h vs 3h `valid_time` cells would need different `Cell` `bounds` for the same coordinate (a
  **per-parameter bounds override** seam). An extent/Domain matter, not identity; a profile using one
  uniform time grid does not need the override, while mixed periods do.
- The statistic vocabulary and canonical quantity set are the deferred **parameter conventions**
  ([#10](../concerns.md#10-parameter-conventions)); this ADR fixes the *structure* (quantity identity,
  `extent_scaling`, the cell axes), while the concrete quantity table, conversion edges, and their
  quality costs stay deferred (#10, [#7](../concerns.md#7-quality-scoring)).
- **Curvilinear domains** and the **sampling-kernel choice** remain interface promises / edge-deferred
  ([#12](../concerns.md#12-curvilinear-domains), [#5](../concerns.md#5-read-time-homogenization-fidelity)).
- **The model degenerates cleanly.** Unfilled slots — `present = None`, the `Uniform` / `PerParameter`
  provenance plane (`PerPoint`), windowed `CellStatistic` (`max` / `min` / `mean`), the
  per-parameter bounds override, a **navigable Z axis** (pressure levels / 3-D columns; the surface
  bundle is the degenerate near-surface fat cell) — cost nothing, so each is purely additive. Concrete
  profiles select positions on these slots without changing the model.
- **Offering / resolution-aware selection is an additive Domain seam.** Continuous footprint axes gain
  an optional native **`step`**; **`Domain.match(other) -> scalar`** is the ranking sibling of
  `contains` (hard admission unchanged). Only axes the **request constrains** (carries a step)
  participate; per-axis fits **combine by product**. Per axis (request step `r`, offering step `o`):
  prefer `o <= r` (at least as fine), among those closest to `r`; any `o > r` ranks below all
  fine-enough peers — upsampling invents detail, downsampling is the normal path. Surfaced as
  **`Capability.score`** so the covered Domain stays private; equal-priority tie-break only
  (ADR-0004). Deferred decision,
  [#20](../concerns.md#20-provider-multi-resolution-offerings-offering-aware-selection).
