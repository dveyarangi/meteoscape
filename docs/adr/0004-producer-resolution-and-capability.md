---
status: accepted
---

# Producer resolution & capability

How the **Arbiter** — the one producer-resolution composite — decides *who* can serve a requested
parameter (**capability matching**), *how* overlapping producers fold onto the target lattice
(**reconcilers**), and how **derived** parameters (**Calculators**) and the build-time **Weaver** fit the
same shape. The abstraction these are shapes of is the
[algebra](./0001-manifold-algebra-and-composition.md); the data they assemble is the
[data model](./0002-data-model.md); the metadata they author is
[ADR-0003](./0003-provenance-and-origin.md).

## The Arbiter — one selecting shape

- **One selecting shape: the Arbiter.** Per requested parameter it picks, with fallback, among that
  parameter's ordered candidate producers, then assembles the per-parameter `ParameterData` into one
  Coverage. There is **no separate per-parameter "Selector" type**; a single-parameter selection is the
  degenerate case. The **top** Arbiter (the best view's child) spans all servable parameters; each
  Calculator holds its **own** scoped one (below).

- **Two combine axes, and they are not symmetric.** A Coverage combines along two axes. The **parameter
  axis** holds **orthogonal** `ParameterData` (temperature ≠ humidity): putting them side by side is
  **record-building** (no shared coordinates, no collisions), and *deriving* a new `ParameterData` from
  them is a **Calculator**. The **coverage axis** is the **same** parameter over a **shared** coordinate
  lattice, where two producers can land on one cell — so **collisions are intrinsic**, and resolving them
  is a **reconciler**. Only the coverage axis is a reconciler, because there the producers share
  coordinates.

- **Multi-component quantities are co-declared, not runtime-coupled.** A vector or paired quantity —
  wind's `wind_u` / `wind_v`, later ocean currents / waves / complex fields — is **co-produced from one
  native field**: a producer serves the whole component set from one origin or none. The Arbiter still
  selects **per parameter**; component coherence follows from the group sharing one candidate list,
  order, and footprint — a **build-time** well-formedness property (the Weaver can assert it) — so a
  mismatched pair (A's `u`, B's `v`) never arises, including where a Calculator's scoped Arbiter resolves
  `(u, v)` together. There is **no runtime atomic co-selection**: it would guard a case producers cannot
  create.

## Capability & matching

- **Capability is a `Manifold` facet — `serves(parameter, requested)` + `parameters` — the dual of
  `project`**, on *every* node (a base-`Manifold` member,
  [ADR-0001](./0001-manifold-algebra-and-composition.md)), not an opaque per-producer `can_serve()`.
  `parameters` is the served `ParameterId → ParameterDef` map (a parameter's canonical facts: quantity,
  statistic, `extent_scaling`, canonical unit). A concrete covered `Domain` is deliberately **off the
  interface** — it lives only where it is singular and exact: **privately** inside a leaf's `serves`, and
  **publicly** as `EnumerableCapability.domain` on a materialized `Coverage`. There is **no separate
  clause or `extent` field**: a parameter's native **vertical offset / level** (`2 m above_ground`,
  `1000 hPa`) and its extensive **accumulation window** are **geometry on that covered `Domain`** — a Z
  `Cell` and a `valid_time` `Cell`'s `bounds` respectively ([data model](./0002-data-model.md)). Ordering
  and the `reconciler` are **policy**, not Capability.

- **The family composes bottom-up like `project`** — leaves declare, composites derive:
  - **`FootprintCapability`** — a general leaf (a `Provider`'s declaration): per-parameter covered
    `Domain` footprint, kept private to `serves`.
  - **`EnumerableCapability`** — the materialized, co-domained leaf a `Coverage` exposes; its one
    enumerable `domain` **is** the Coverage's positional grid, so `Countable.domain` derives from it (not
    a second copy).
  - **`UnionCapability`** — an **Arbiter**: the union of its members — `serves` iff *some* member does;
    `parameters` is the members' union. Takes members **flat** (each `Capability` carries its own
    `parameters`, so no per-parameter pre-indexing). Its future dual is an **intersection / consensus**
    fold (`serves` iff *all* members do) — the capability of the deferred `consensus` reconcilers
    ([#6](../concerns.md#6-reconciler-catalogue)) — not built.
  - **`DerivedCapability`** — a **Calculator**: a **unary input→output transform** (not a set-op). It
    serves its single **output** parameter (present in *no* input) iff *all* its fixed inputs are servable
    through the scoped resolver; `parameters` is that output alone.
  - a **`Reservoir`** **forwards** its child's unchanged (the `Store` grid is a fidelity floor, not a
    capability boundary).
  Composition only ever **unions parameter sets and ANDs/ORs the predicate** — it never *synthesises* a
  `Domain`, so the multi-candidate union has no representation problem: it collapses to one concrete
  `EnumerableCapability.domain` only when you `project`. A coarse `parameters × max-horizon`
  **introspection envelope** aggregates from leaf reach (composites publish no `Domain`); v1 narrates it
  in the tool description, and a dedicated introspection surface is deferred.

- **A leaf's temporal reach is clock-anchored (v1)** — its `valid_time` window tracks the provider's run
  anchor (the cadence, [ADR-0003](./0003-provenance-and-origin.md)), encapsulated in the continuous
  footprint `Domain` ([ADR-0002](./0002-data-model.md)) so `serves` stays a plain `contains`. The
  per-provider numbers are [#18](../concerns.md#18-clock-anchored-footprint-fidelity).

- **The predicate** `serves(parameter, requested_domain)` reads the pair `(def, offered)` and asks
  whether a **valid, non-lossy resampler path** exists from `offered` to `requested` — the
  `ParameterDef` is why the value is a pair, not a bare `Domain`. A parameter's **resampler** is
  entailed by its `(scale, statistic, extent_scaling)` and is **asymmetric**:
  1. the requested parameter is in the mapping (**key presence** — the closure below gives each key its
     reachable family);
  2. **refine up** (finer request) — a `linear` scale interpolates to any tick, a categorical scale
     snaps to members, and an **extensive** window cannot be split;
  3. **coarsen down** — whole, **phase-aligned integer-multiple** aggregation via the statistic's
     combine (`sum` for extensive, `max` / `min` / `mean` for windowed): a 3h producer serves 3h / 6h /
     9h…, **not** 1h, 2h, or a shifted phase.
  `Domain.contains` is only the **geometric half** (linear-refine / snap); extent-reachable aggregation
  is not containment (6h ⊄ 3h) and lives in `serves`, which holds the `def`. Interpolability is thus a
  **parameter** fact (its scale), never a `Domain`/axis one.

- **Resamplers are a registry** The `ParameterDef` carries a resampler
  **selector** (derived from scale × statistic × extent, not hand-set); the **implementations**
  (linear / angular / area-weighted / categorical kernels) live in a catalogue looked up at
  homogenization, deferred with the kernel choice ([#5](../concerns.md#5-read-time-homogenization-fidelity)).
  Matching reads only resampler **existence and losslessness**; **lossy** resamplers (extensive
  disaggregation, categorical priority-down) are a later, purely **additive** tier
  ([#7](../concerns.md#7-quality-scoring)).

- **Capability is the closure of emitted functionals under *exact* conversion edges** (aligned coarsening
  by additivity), so one declared functional serves a whole reachable family without enumeration.
  Anything outside the closure is **`capability-mismatch`** — a first-class outcome, so there is **no
  disaggregation / quality-degradation machinery** in the contract. The degrading tier (e.g. splitting 3h
  into 1h by assumption) is deferred ([#7](../concerns.md#7-quality-scoring)); when it lands it only
  *grows* a producer's closure — purely additive. Match is **boolean**; ranking stays static priority.

- **Static / dynamic split.** The **Weaver** indexes producers by key `(quantity, statistic)` to wire
  each parameter's candidate set (build-time). The **Arbiter** applies range-containment + extent
  reachability per request to filter that set, then walks it in **priority** order. A candidate is a
  **configured producer** identified by a **`SourceKey`** (`provider` + `dataset`; → [glossary:
  SourceKey](../glossary.md)) — **not** a bare provider — so priority discriminates *within* a provider
  (`best_match ≻ gfs_seamless`). An **offering** (a distinct resolution / cadence *product*) is a distinct
  `SourceKey` via its `dataset` tag — the tag **discriminates identity opaquely**; the offering's native
  geometry is **not** in the key and **not** a second provenance identifier — ranking reads the footprint
  Domain's per-axis **`step`** via `Domain.match`
  (→ [ADR-0002](./0002-data-model.md); build [#20](../concerns.md#20-provider-multi-resolution-offerings-offering-aware-selection)).
  The two selection tiers differ by **timing and precedence**: **quality / model** is **static
  `priority`** (weave-time, baked into the ordered candidate list) and **always wins across bands**;
  **resolution** is **dynamic `Capability.score` → `Domain.match`** (project-time), firing only as a
  **tie-break among equal-`priority`** peers (contiguous band in the baked list: admit via boolean
  `serves`, then try peers in **`score` order** — `project` the best, on runtime fault try the next
  admitted peer in the band, leave the band only when none remain). A worse step-fit at higher priority
  still beats a perfect fit at lower priority — cross-priority geometric override is a later scorer
  policy behind [#7](../concerns.md#7-quality-scoring), not the default. **`score` defaults:** a leaf
  without a native `step` (or a request with no constrained axes) returns a **constant** — peers tie and
  wired order wins; composites (`UnionCapability`, `DerivedCapability`) expose the same constant — the
  Arbiter scores **leaf** candidates, not the union, and a Calculator is not ranked on geometry (its
  inputs were already selected). Distinguish an offering (a
  distinct published **origin**, its own `SourceKey`) from **coarsening within** one product (same
  `SourceKey`, served by read-back homogenization, [#5](../concerns.md#5-read-time-homogenization-fidelity) /
  [#15](../concerns.md#15-coarser-grid-resampling-and-aggregation-semantics)) — the former is `match`, the
  latter is resampling. This is the **same mechanism** as separate observation / forecast sources (folded
  later by a `valid_time` reconciler). v1 is one offering per provider (Open-Meteo defaults to
  `best_match`); the `OfferingDef` config surface and footprint-axis `step`s are the deferred build recipe
  ([architecture](../architecture.md#config-binders-weaver) /
  [#20](../concerns.md#20-provider-multi-resolution-offerings-offering-aware-selection)).

## Reconcilers — the coverage fold

- **One shape, parameterized by a `reconciler`.** Per parameter the Arbiter samples each producer onto
  the Selection's **target lattice** (fixed by the `Domain`, **independent of any child's coverage**) and
  folds the contributors **per cell**: **0** contributors → **nodata**, **1** → passthrough, **≥2** → the
  reconciler decides. The default is **`priority`** — take the top-priority contributor with data, **fall
  through on a runtime fault** (*not* on nodata, which is a successful gap) — **this is selection**.
  Coverage reconcilers (`tile` disjoint union, `consensus` blend, `feather` smoothed seam) are the same
  shape with a different fold. So tiling, gap-fill, radar / regional mosaicking, **observation +
  forecast along `valid_time`**, and **cross-run combination** (folding **run-stamped contributor
  Coverages** — different `issue_time`s — along `valid_time`; `issue_time` is each contributor's
  provenance stamp, [ADR-0003](./0003-provenance-and-origin.md), not a Domain axis) are all the Arbiter
  under a reconciler. The catalogue beyond `priority` is deferred ([#6](../concerns.md#6-reconciler-catalogue)).

- **The `reconciler` is declared config, defaulting to `priority`** — **not inferred** from geometry.
  Point / timeline producers fully overlap on one location, so they engage no spatial machinery: the
  default just picks. **The same Arbiter serves timeline and grid** with no `timeline` flag — trivial
  geometry degenerates to a pick on its own.

- **A whole-coverage producer is a gap-filler, not a separate fallback.** It joins the **same** Arbiter's
  producer set at **low priority**; the per-cell `priority` reconciler then yields the high-resolution
  source where it reaches and the whole model in the gaps. No separate node, no whole-vs-partial branch.

- **A point-observation network is one provider, not one-per-station.** A station *network* (or a vendor
  analysis surface) is a **single** `Provider` whose `FootprintCapability` advertises the network's
  **aggregate hull** — a continuous `FootprintDomain` ([ADR-0002](./0002-data-model.md)), so v1's plain
  `contains` gate admits any interior request with **no `intersect` dependency** — and whose `project`
  runs the scattered→lattice interpolation **inside the leaf**. Interpolating one network's own stations
  is resampling **within one origin** (one `SourceKey`), not a cross-origin fold, so it stays private
  like `best_match`; combining *distinct* networks stays a reconciler. Interior network holes return as
  first-class **nodata**, filled by the model under the same `priority` fold, so a generous hull is safe.
  Faithful lineage is **`PerPoint`** (contributing stations, method, distance), above the leaf's default
  single-fetch `Uniform` plane ([ADR-0003](./0003-provenance-and-origin.md)); honest hull-vs-real
  coverage and interpolation quality ride the availability / scoring seams
  ([#18](../concerns.md#18-clock-anchored-footprint-fidelity) / [#7](../concerns.md#7-quality-scoring)).
  A single station addressed at its **known** point is the **dual** shape — an ordinary point `Provider`
  — for the named / IoT case; the two coexist by footprint geometry, not by node type.

## Calculators — derived parameters as candidates

- **A Calculator is just another candidate producer.** It declares its **output** parameter (its
  Capability) and is a candidate for that parameter exactly like a Source. Routing a derived parameter to
  its Calculator is still **selection**; the **combination happens inside the Calculator**, so an Arbiter
  never computes formulas.

- **A Calculator holds one Arbiter, scoped to its inputs.** It declares input parameter **names** + `fn`
  and receives a **single** Arbiter that resolves all of them in one `project`. That Arbiter is a
  **distinct instance scoped to the calculator's inputs** — wired to those inputs' producers and nothing
  else — so it can **never route back** to the calculator. Every edge points **downward**, so the object
  graph is an acyclic **DAG** at any derivation depth.

  ```python
  class Calculator:
      def __init__(self, out, inputs, fn, resolver):   # resolver: ONE scoped Arbiter
          self.out, self.inputs, self.fn, self.resolver = out, inputs, fn, resolver
      async def project(self, sel):
          ins = await self.resolver.project(sel.with_params(self.inputs))  # all inputs, one call
          return combine(self.fn, ins)                                     # + synthetic provenance
  ```

- **The graph is woven once by the Weaver; runtime nodes are dumb.** A **`CalculatorRegistry`** of
  catalog-resolved **`RegisteredCalculator`**s (output → manifest + inputs + `stored?`) — produced by
  `CalculatorBinder` from profile **`CalculatorSpec`**s against a **`CalculatorCatalog`**
  (`fn_id → CalculatorManifest`; layering → [ADR-0005](./0005-build-time-composition.md)) — feeds the
  Weaver. The Weaver constructs the graph, **memoizing one Calculator instance per derived parameter**
  (a shared intermediate is a **shared node** — common-subexpression elimination); an in-progress set
  guards a **parameter-dependency cycle**. At request time nodes project their **fixed** children — no
  registry, no lookup. Omniscience lives only in the build-time Weaver.

  ```python
  def build_calc(param):                       # memoized: one (maybe stored) node per derived param
      if param in memo: return memo[param]
      if param in visiting: raise CycleError(param)
      visiting.add(param)
      fn, inputs, stored = registry[param]
      input_arb = Arbiter(candidates_for(inputs))       # scoped Arbiter over this calc's inputs
      calc      = Calculator(param, inputs, fn, input_arb)
      node      = Reservoir(store, calc) if stored else calc
      visiting.remove(param); memo[param] = node; return node

  def candidates_for(params):                  # Weaver-derived from the Capability index
      return {p: order_by_policy(p, sources_serving(p) +
                                    ([build_calc(p)] if p in registry else []))
              for p in params}

  top       = Arbiter(candidates_for(all_servable_params))
  best_view = Reservoir(store, top)
  ```

- **Prioritization is policy data, baked into ordered candidate lists.** The priority policy feeds the
  **Weaver**, whose `candidates_for` returns each parameter's candidates **already ordered** — including
  where the Calculator ranks relative to direct providers (derived-vs-direct competition is just its
  position in that list). A runtime Arbiter is a **dumb iterator**: walk the ordered candidates, fall
  through on failure. The same policy applies wherever a parameter appears, so ordering is consistent
  across the top Arbiter and every scoped Arbiter.

- **Retention lives in `Store`s, added by wrapping; only `Store`s hold state.** A heavy or
  shared intermediate — a Calculator's output included — is always retained by wrapping it in a
  `Reservoir`. An **optional single-flight** guard on the `Reservoir` can coalesce concurrent identical
  `project`s so a shared intermediate computes **once** under parallelism — a wired-but-unbuilt seam,
  **deferred** until contention warrants it ([deferred in v1](../v1-requirements.md)). Primary-parameter
  fetches dedupe at the **Source** `Store`. Arbiters, Calculators,
  Providers and `Reservoir`s are **stateless transformers** — exactly the
  [algebra](./0001-manifold-algebra-and-composition.md)'s logically-read-only model with retention as
  transparent memoization.

## Outcomes

Three distinct results, never conflated: **nodata** (0 contributors — a *successful* gap), **runtime
fault** (an exception that triggers per-cell / per-candidate fall-through), and **capability-mismatch**
(no candidate serves the requested functional). A parameter whose candidates **all** fault — or which no
producer can serve — is **omitted** from the record; how that absence surfaces at the request edge is the
request-level contract, whose canonical home is
[architecture: Failure, nodata, and availability](../architecture.md#failure-nodata-and-availability).

## Why

- One shape (the Arbiter) for all selection, with a Calculator as an ordinary candidate, vindicates the
  simplest model — *a calculator is just another producer the Arbiter picks* — without letting the
  selector compute formulas. Scoping each calculator's input Arbiter to its inputs keeps the graph an
  acyclic DAG while letting the Calculator depend on a single resolver.
- Capability as **data + a fixed predicate** (not behaviour) stays introspectable, so the Weaver can
  index candidates statically; the extent-scaling–aware extent rule is the only thing that distinguishes "3h precip
  yes / 1h no", and it is exactly the data model's *exact* conversion edge — one mechanism, not two.
- "Assembly vs reduction" is a false split on the coverage axis: pick-one is just a reducer, and one
  request needs nodata + passthrough + reconcile *simultaneously*, decided per cell by how many producers
  cover it. A declared reconciler avoids a `timeline`-vs-`grid` flag; trivial geometry picks for free.
- Weaving once and memoizing reifies the parameter-dependency graph into dumb, pre-wired, testable nodes;
  a natural home for single-flight dedupe and future scheduling.

## Considered options

- **A single global registry-aware Arbiter** shared as every calculator's resolver. Coherent and scales,
  but makes the runtime arbiter omniscient, introduces a **cyclic object graph** (arbiter ⇄ Calculators),
  re-walks the structure each request, and must grow node + future machinery to dedupe concurrent shared
  intermediates. Rejected **as the default** in favour of scoped per-calculator Arbiters; *a preference
  about where omniscience and the cycle live, not a hard invariant.*
- **Merge derivation into the Arbiter (a select-or-derive node).** Rejected — load-bearing: it puts
  formula / numeric logic into the selector, conflating routing with computation. (Routing *to* a
  Calculator does not; computing *inside* the Arbiter would.)
- **Self-storing `Calculator(fn, stored)`; per-parameter `Selector` nodes; a per-request planner for
  standing params.** Rejected: retention is the `Store`'s role, added by wrapping in a `Reservoir`, not by
  widening the Calculator to `Writable`; a
  Calculator wants a single resolver (sharing is already provided by the Source `Store` and memoized
  Calculator instances); the standing DAG is built once (per-request building is only for caller formulas).
- **A separate coverage composite (a "Mosaic" node) the Arbiter ranks as a producer.** Rejected: it
  duplicates the Arbiter's per-cell gather, drops the reconciler choice, and is dead weight for
  point / timeline data — the coverage fold belongs on the Arbiter.
- **An opaque per-producer `can_serve()` capability, or a capability DSL.** Rejected: opaque defeats the
  Weaver's static candidate index; a DSL is unjustified when a structured `parameters` map + one predicate
  suffice.

## Consequences

- **Nodata is first-class and is not failure**, needing the explicit `present` mask on `ParameterData`
  ([data model](./0002-data-model.md)). Provenance granularity **splits by reconciler**: `priority` /
  `tile` keep `Uniform` / per-sub-`Domain` lineage; `consensus` / `feather` press toward `PerPoint`
  provenance ([ADR-0003](./0003-provenance-and-origin.md)).
- **Statically wired, per-cell routed.** The Arbiter's producer set is injected at construction and
  **not re-linked per Selection**; which contributors fire is decided at `project` by intersecting each
  footprint with the requested `Domain`.
- **Deferred seams:**
  - **Probed / discovered real availability.** The clock-anchored footprint (above) declares the
    *envelope*; a leaf that reflects **which runs / timesteps actually exist right now** — vs the declared
    window — needs **I/O at selection time**, reopening the **Arbiter → Broker** pressure
    ([#8](../concerns.md#8-arbiter-to-broker-pressure)). v1's window is metadata-only (no probe); the
    accuracy of that declared window against real availability is [#18](../concerns.md#18-clock-anchored-footprint-fidelity).
  - **Caller-supplied formulas (a request-time DSL).** The function arrives *in the Selection*; the
    Weaver then runs **per request** (weave → project → discard), the same recursion used at build time.
    The static registry is the v1 shape.
  - **Dynamic / quality scoring** ([#7](../concerns.md#7-quality-scoring)). Replace the static order with
    a request-aware `score(candidate, selection)` behind the **same selection signature**: the static
    order is the **degenerate constant scorer** (`score = -wired_index`), so it is a strict
    generalization. A **stateless metadata scorer** fits the read-only algebra untouched; a scorer that
    **probes** sources needs state + I/O at selection time, reopening the **Arbiter → Broker** pressure
    ([#8](../concerns.md#8-arbiter-to-broker-pressure)) — a separate, larger decision. The match-cost
    tier of capability (degrading conversion edges) joins this seam. **Offering / resolution-aware
    selection** ([#20](../concerns.md#20-provider-multi-resolution-offerings-offering-aware-selection))
    is a concrete driver: its geometric half is a graded **`Domain.match()`**
    (→ [ADR-0002](./0002-data-model.md)) surfaced as **`Capability.score`** (boolean `serves`
    unchanged), used as an **equal-priority tie-break** only — priority-first; in-band fall-through
    tries the next peer by `score` before leaving the band; the covered Domain stays private.
  - **Input `Store` placement.** v1 resolves a Calculator's inputs through its scoped Arbiter
    (Source-`Store`d), not the top `Store`; pulling from the top `Store` is the only thing that would want
    a feedback edge, deliberately not done.
