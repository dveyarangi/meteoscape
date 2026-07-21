# Open concerns

Open design concerns, **ordered by priority** (highest first). Priority blends *how much it blocks the
encoding pass / v1 build* with *how hard it is to absorb additively later*. `architecture.md` indexes
this file by subtitle. **Numbers are stable IDs, not contiguous ranks** — when a concern is settled it
**moves out** to its owning ADR, leaving a gap (what each ADR owns →
[architecture: ADR index](./architecture.md#adr-index)).

This file owns unresolved design pressure, not delivery sequencing.

---

## 5. Read-time homogenization fidelity

**Kind:** edge-isolated · **Refs:** [ADR-0001](./adr/0001-manifold-algebra-and-composition.md), [ADR-0002](./adr/0002-data-model.md)

**Mechanism resolved (required by v1):** every `Reservoir` `quantize`s a request for retention and
**homogenizes** the stored cells onto the requested `Domain` at read, so `project(sel)` honours
`sel.domain` — the pipeline, single-origin units, and same-run fusion live in
[ADR-0001 §materialization](./adr/0001-manifold-algebra-and-composition.md),
[ADR-0003](./adr/0003-provenance-and-origin.md), and [architecture §Reservoir](./architecture.md#reservoir).
On-grid reads degenerate to a **lossless crop**; the open question is the off-grid kernel.

**What's open is fidelity:** the **kernel choice** per field axis — the resampler registry's
implementations (nearest / linear / cubic; **conservative / area-weighted** for extensive
re-aggregation; the non-linear `circular` / categorical kernels for scales v1 does not exercise, since
wind rides as linear u/v components) — and the acceptable **accuracy bounds**; ADR-0002 fixes only
*which* axes admit a kernel and that a storing grid imposes a **fidelity floor**, not the method. The
v1 contract specifies the **degenerate nearest-neighbor** kernel (kind-agnostic, pluggable) — it honours `sel.domain`
without real interpolation; **per-kind** kernels (linear intensive incl. u/v wind, area-weighted
extensive, the deferred non-linear scales), accuracy bounds, irregular vendor geometries (sparse
stations, mixed grids), and the **provider "exact" capability** (true off-grid points bypassing the
store-grid floor — realized as another `SourceKey`-identified offering under the instance model,
[ADR-0004](./adr/0004-producer-resolution-and-capability.md)) are the later stress on the kernel.
Always fetching the finest native product and resampling down is faithful **only** when the kernel is
aggregation-correct **and** the coarser product is a true downsample of the same origin — a native-coarse
offering is often a **distinct origin**, so it is sometimes required, not merely cheaper
([#15](#15-coarser-grid-resampling-and-aggregation-semantics),
[#20](#20-provider-multi-resolution-offerings-offering-aware-selection)). Contained behind the sampling
seam. This concern owns **how accurately** a coarsened value is computed;
**which** cell statistic it should be, and how a request asks for it, is
[#15](#15-coarser-grid-resampling-and-aggregation-semantics).

## 21. `serves` extent vs `project` crop-ability

**Kind:** algebra-shaped (Capability dual) · **Refs:** [ADR-0004](./adr/0004-producer-resolution-and-capability.md), [#5](#5-read-time-homogenization-fidelity)

ADR-0004 defines `serves` as *whether a valid non-lossy resampler path exists* from offered → requested;
`Domain.matches` is only the **geometric half**. The implementation seam under concern is a mismatch:
`EnumerableCapability.serves` (and leaf footprints) admit by **extent containment**, while
`Coverage.project` / the sampling engine only
perform an **aligned identical-step crop** — off-phase or non-identical-step selections that still sit
inside the span are admitted, then fail at `project` with `NotImplementedError` instead of a clean
admission miss (`capability-mismatch` / Arbiter fall-through).

The fixed hourly on-lattice v1 request does not exercise this mismatch. **Close inside `serves`**, not with a second check in
`Arbiter.project`: deepen the Capability predicate with the resampler / alignment branch (registry at
007; extensive horizon edge at 002). Composites (`Union` / `Derived`) and the Arbiter inherit
correctness unchanged — blast radius stays behind the Capability facet. Until then, engine
`NotImplementedError` is an internal assert that `serves` over-promised, not the normal edge path.

## 22. Lattice helpers vs `domain` / `sampling` module split

**Kind:** room-left (module layout)

Index arithmetic (row-major encode/decode, `sub_lattice_offset`, `AXIS_ORDER`) is owned by `domain.py`;
`sampling.py` consumes it one-way (`sampling → domain`, never the reverse). That matches the
geometry-vs-value-transfer cut. If Domain grows heavy with non-lattice geometry *and* lattice math, or
a third consumer appears (`quantize`, store grids), **carve a thin `lattice.py`** that both import —
pure refactor, no contract change. Not blocking; do not split preemptively.

## 23. Spatial vs temporal `RegularAxis` types

**Kind:** room-left (types / hot path) · **Refs:** [ADR-0002](./adr/0002-data-model.md)

`RegularAxis` is one type over `Coordinate = float | datetime` and `Step = float | timedelta`.
`sub_lattice_offset` (and axis arithmetic) pays an `isinstance` crawl on every call to branch float
tolerance vs exact `timedelta` math. The lasting fix is **split types** (spatial vs temporal regular
axes) so dispatch is structural, not runtime — not a pair of private helpers that paper over the union.
Additive when the axis surface is next touched; v1 behaviour is correct as-is.

## 15. Coarser-grid resampling and aggregation semantics

**Kind:** edge-isolated (data-model + surface) · **Refs:** [ADR-0002](./adr/0002-data-model.md), [#5](#5-read-time-homogenization-fidelity)

The temporal-axis counterpart to [#5](#5-read-time-homogenization-fidelity)'s spatial fidelity, and as
central. Coarsening the `valid_time` grid below the native/store cadence is **not one operation**, and
the choice is **product semantics, not kernel accuracy** ([#5](#5-read-time-homogenization-fidelity) owns
the latter). Three regimes:

- **Extensive** (precipitation): the coarse cell is the **integral** (sum over the interval) — the
  conservative re-aggregation kernel of [#5](#5-read-time-homogenization-fidelity).
- **Intensive, small factor** (3 h temperature): **point subsampling** at the tick is acceptable — the
  tick still represents its neighbourhood.
- **Intensive, large factor** (24 h temperature): a **point** sample is **unrepresentative** — one
  instant is night/day-arbitrary, not "the day". The faithful product is a **window statistic**
  (`min` / `max` / `mean`), already modelled as **`CellStatistic`** on `ParameterDef`
  ([ADR-0002](./adr/0002-data-model.md)).

Two expression gaps block honouring this — both **additive**, neither in v1:

1. **Which statistic.** `Functional = (quantity, statistic)` can name `tmax` / `tmin` / `tmean`, but the
   surface exposes only `point`; a request cannot ask for "daily max temperature", and whether the
   statistic is **chosen automatically by coarsening factor** or **stated explicitly** is undecided.
2. **Several statistics of one quantity at once.** Daily **min and max** temperature in one response are
   distinct `Functional`s / `ParameterData`; the surface alias layer and the Coverage must carry
   **multiple aggregations of the same quantity** together.

v1 sidesteps it entirely — **hourly-only, `point` statistic**, no `step` input. The open work is the
**request-expression surface** and the **auto-vs-explicit statistic policy**, not the data model (the
`CellStatistic` slot and a multi-`ParameterData` Coverage already exist).

## 6. Reconciler catalogue

**Kind:** algebra-shaped (extension) · **Refs:** [ADR-0004](./adr/0004-producer-resolution-and-capability.md)

ADR-0004 settles the reconciler **topology** (one Arbiter, one declared `reconciler`), but
the concrete catalogue beyond the default `priority` — `tile` (disjoint union), `consensus` (blend),
`feather` (smoothed seam) — and their precise per-cell semantics are **unspecified**. Unproven until a
real partial-coverage producer set exists. Note the per-cell fold these need is **not the built
interface** — the implemented `Reconciler` only orders producers, so the catalogue arrives together with an
interface widening → [#28](#28-reconciler-interface-selection-ordering-vs-per-cell-fold). `consensus` / `feather` press toward per-point provenance
([ADR-0003](./adr/0003-provenance-and-origin.md)) and require the nodata / mask
slot ([ADR-0002](./adr/0002-data-model.md)).

## 13. Candidate admission: containment vs intersection

**Kind:** algebra-shaped (boundary) · **Refs:** [ADR-0004](./adr/0004-producer-resolution-and-capability.md)

ADR-0004 states two admission rules that **only agree for fully-overlapping producers**. The capability
filter admits a candidate by **whole-request `Domain`-containment** (clause region / time-range ⊇ request),
yet the per-cell **gap-filler** ("a whole-coverage producer joins the set at low priority; the per-cell
`priority` reconciler yields the high-res source where it reaches and the whole model in the gaps") needs
**partial** producers in the set — i.e. **intersection** admission (footprint ∩ request ≠ ∅). Under strict
containment a partial-coverage producer is filtered out, so spatial gap-fill and any `valid_time` splicing
**cannot occur**. **v1 is unaffected and in fact relies on containment** — wholesale fallback, "select,
never combine", no horizon splicing. The open question: when coverage reconcilers
([#6](#6-reconciler-catalogue)) land, admission must generalize to **intersection** with per-cell folding,
at which point the two rules must be reconciled (likely: containment is the *degenerate* case of
intersection). Additive; no v1 work.

Vertical matching is **axis-kind-owned** — neither containment nor intersection globally →
[ADR-0004](./adr/0004-producer-resolution-and-capability.md). The open part of this concern is only the
**partial spatial/temporal producer** admission above.

## 9. Cross-run combination

**Kind:** deferred seam · **Refs:** [ADR-0002](./adr/0002-data-model.md), [ADR-0004](./adr/0004-producer-resolution-and-capability.md)

A v1 `ParameterData` is **single-origin**, with its run identity carried by the provenance `issue_time`;
the enclosing Coverage has no shared run identity. Combining runs for one parameter is a **reconciler
folding run-stamped contributor Coverages along `valid_time`** (ADR-0004), yielding a synthetic origin —
*not* interpolation along an `issue_time` axis (there is none; `issue_time` is a provenance stamp —
ADR-0002 / ADR-0003). Archives that retain many runs are a **collection keyed by `issue_time`** (the
categorical-key seam, generalizing to ensemble / scenario). The semantics (which run wins where, blended
consensus, how observations join forecasts along `valid_time`) are undecided.

## 7. Quality scoring

**Kind:** deferred seam · **Refs:** [ADR-0004](./adr/0004-producer-resolution-and-capability.md), [ADR-0001](./adr/0001-manifold-algebra-and-composition.md)

Quality is **implicit in Arbiter ordering** (static priority). This may prove insufficient — *when does a
static order start returning visibly worse data than an available alternative?* A request-aware **scorer**
can replace the static order behind the **same selection signature** (ADR-0004: the static order is the
degenerate constant scorer). The same seam covers the **match-cost tier of capability** — degrading
conversion edges (e.g. disaggregating 3h into 1h), which only *grow* a producer's closure. The
**metadata-only soft tier** fits the read-only algebra untouched; a scorer that **probes** sources needs
state + I/O at selection time, reopening [Arbiter → Broker](#8-arbiter-to-broker-pressure).
**Offering / resolution-aware source selection**
([#20](#20-provider-multi-resolution-offerings-offering-aware-selection)) is a concrete instance —
→ [ADR-0004](./adr/0004-producer-resolution-and-capability.md) (equal-priority `score` tie-break).

## 8. Arbiter to Broker pressure

**Kind:** algebra-shaped (boundary) · **Refs:** [ADR-0001](./adr/0001-manifold-algebra-and-composition.md)

ADR-0001 keeps acquisition a **property of a shape**, not a coordination layer above the algebra, and the
Arbiter is a stateless transformer. If acquisition later grows real logic — live latency probing,
sampling at selection time, failure-adaptation — the Arbiter boundary may have to **harden into a richer
acquisition shape (a "Broker")** with state and I/O at selection time. A larger, separate decision; the
soft (metadata-only) tier of [quality scoring](#7-quality-scoring) deliberately stays on the near side of
this line.

## 10. Parameter conventions

**Kind:** edge-isolated · **Refs:** [architecture.md](./architecture.md#deferred-decisions), [ADR-0002](./adr/0002-data-model.md)

Canonical **parameter names, units, and spatial-ref encoding** remain open beyond v1. The structure
and mono-unit invariant are owned by [ADR-0002](./adr/0002-data-model.md); the **v1 canonical set**
(6 provider-served + 2 derived parameters) is recorded in [`parameters.md`](./parameters.md).
This concern owns the **quantity-table content beyond v1 and conversion-edge qualities**, contained
inside the Provider / Normalizer seam.

## 14. Resolution trace and observability

**Kind:** deferred seam · **Refs:** [ADR-0004](./adr/0004-producer-resolution-and-capability.md), [architecture.md](./architecture.md#failure-nodata-and-availability)

How a profile **explains** a resolution is unspecified — per parameter: which candidate won, what fell
through (**runtime-fault** vs **nodata** vs **capability-mismatch**), the `issue_time` / freshness used, and
whether each cell was a **`Store` hit or a refill**. The data product is a **`Coverage`**, so a trace must
ride **alongside** it as a **sidecar** — a profile may expose diagnostics / traces without changing the
Coverage — and **never** inside `ParameterData`. Open: the trace's **shape and granularity** (per-request /
per-parameter / per-cell); its relation to per-parameter **provenance** (provenance = *what the data is*;
trace = *how it was chosen*); and the wider **observability** surface (structured logs + metrics: selection
counts, fallback rate, cache hit-rate, provider latency / error). Keeping the trace a sidecar channel leaves
the read-only algebra untouched. v1 may emit a **minimal structured log**; the structured sidecar is deferred.

## 36. Unserved and uncomparable are indistinguishable

**Kind:** deferred seam (diagnosability) · **Refs:** [#14](#14-resolution-trace-and-observability), [ADR-0002](./adr/0002-data-model.md), [ADR-0004](./adr/0004-producer-resolution-and-capability.md)

`Capability.serves` is a bool, so the Arbiter's candidate loop skips a producer identically whether it
**does not cover** the requested extent or **cannot be compared to it at all**. `Domain.matches`
returning `False` for both is correct — a representation that cannot determine coverage cannot serve,
and the total predicate is what keeps the degrade path alive (a raise would abort the loop and fail
requests a later producer could serve, [ADR-0002](./adr/0002-data-model.md)). What is lost is not
correctness but **diagnosis**.

The operator-visible symptom is one message — *"no producer admits any requested parameter"* — for two
very different situations: *"nothing covers this region"* (the system working) and *"this source can
**never** participate, and nothing told you"* (a configuration or implementation gap). The second is
not curvilinear-specific: a separable but **misconfigured** footprint — a region narrower than
intended, a Z level nothing requests — is skipped just as silently and passes every build-time check.
The [#12](#12-curvilinear-domains) case is narrower still: a curvilinear producer fails the **build**,
because the `priority` reconciler's domain composition compares candidates per-axis and rejects one it
cannot compare — so it never reaches the request path at all.

This belongs to the resolution trace ([#14](#14-resolution-trace-and-observability)) rather than to the
predicate: the skip needs a **reason code** alongside the existing runtime-fault / nodata /
capability-mismatch vocabulary, not a third return state no caller could branch on. Open: whether a
build-time *reachability* check ("this enabled source can serve nothing any plausible request asks
for") is worth having as well, or whether the trace alone is enough.

## 18. Clock-anchored footprint fidelity

**Kind:** deferred (tuning) · **Refs:** [ADR-0003](./adr/0003-provenance-and-origin.md), [ADR-0004](./adr/0004-producer-resolution-and-capability.md)

→ [ADR-0003: cadence](./adr/0003-provenance-and-origin.md#run-identity--freshness--the-cadence).
What stays open is **the numbers, not the shape**: the concrete per-provider `{Δ, L, max_lead}` (v1 specifies a **conservative
default** — floor to the hour, generous `L` — accepting occasional edge nodata), and the residual
**estimate error** (under-estimating `L` still over-promises → edge nodata; over-estimating
under-promises). The real fix is a provider's **actual reference / availability signal** when it exposes
one (rounded guess as fallback) → `ideas.md`. Additive; no contract change.

## 11. Incremental synthetic recompute

**Kind:** deferred (optimization) · **Refs:** [ADR-0003](./adr/0003-provenance-and-origin.md)

A synthetic `ParameterData` re-derives whenever **any** parent expires (worst-case `min` expiration —
ADR-0003). Recomputing **only the stale sub-domain** instead of the whole is an **unmodeled optimization**.
Purely a performance concern; correctness is unaffected by deferring it.

## 20. Provider multi-resolution offerings (offering-aware selection)

**Kind:** algebra-shaped (extension) · **Refs:** [#5](#5-read-time-homogenization-fidelity), [#7](#7-quality-scoring), [#15](#15-coarser-grid-resampling-and-aggregation-semantics), [ADR-0002](./adr/0002-data-model.md), [ADR-0004](./adr/0004-producer-resolution-and-capability.md)

The contract is owned by [ADR-0004](./adr/0004-producer-resolution-and-capability.md) (offering
identity and the priority-first band walk), [ADR-0002](./adr/0002-data-model.md) (axis `step` and
`Domain.match`), and [ADR-0003](./adr/0003-provenance-and-origin.md) (no native-fidelity provenance
field). Provider `exact` and native-coarse-as-distinct-origin remain with
[#5](#5-read-time-homogenization-fidelity) / [#15](#15-coarser-grid-resampling-and-aggregation-semantics).

**Open (additive build; v1 unaffected — one offering per provider, `contains`-only):** populate
continuous footprint **`step`s**, implement **`Domain.match`** / **`Capability.score`**, and the Arbiter
  equal-priority band walk. **Multi-level samples inside one vantage window**
(wind at 10 m + 80 m under `[0,100]`) are **not** offering selection — the resampler folds them to one
representative value (→ [ADR-0004](./adr/0004-producer-resolution-and-capability.md)); `match`/`score`
applies to *offerings* (distinct `SourceKey`s), not to levels within one product.

## 25. Root-store unit reuse across vantage windows

**Kind:** deferred seam · **Refs:** [ADR-0006](./adr/0006-materialization-granularity-and-store-shape.md), [ADR-0002](./adr/0002-data-model.md)

The best-view store holds **product** units keyed by the *request's* Z cell (the vantage window) —
answers, not native facts ([ADR-0006](./adr/0006-materialization-granularity-and-store-shape.md)).
v1 has exactly one edge-authored default window, so the key is stable and reuse is exact-match. When
custom vantage windows arrive, reuse needs a rule: a layer-unresolved value labeled `[0,10]` is an
**∃-claim** ("measured somewhere in the layer"), so admitting it for a narrower `[0,5]` request by
plain inclusion is suspect — unlike a ∀-claim statistic cell. Options when it bites: exact-key only
(cache misses fall through to the Sources, which re-match native units honestly — correct, just
colder), or a declared tolerance policy at the edge. No v1 work; the fall-through path is already
correct.

## 12. Curvilinear domains

**Kind:** room-left (interface promise) · **Refs:** [ADR-0002](./adr/0002-data-model.md),
[ADR-0007](./adr/0007-capability-carries-its-domain.md), [#5](#5-read-time-homogenization-fidelity)

ADR-0002 makes the `Domain` interface **non-separable by default** so curvilinear geometries — radar
geotangent slices, satellite swaths — can be a **representation** later without a contract change.
Curvilinear implementations are deferred: interface conformance is a **promise**. Until then it is only
a constraint on the Domain interface (don't assume per-axis separability), not a v1 work item.

**Two independent roles, separately committed.** Non-separable geometry appears on *both* sides of
`project`, and neither implies the other — all four combinations are real operations:

| | separable target | curvilinear target |
|---|---|---|
| **separable source** | v1 today (grid → grid) | verify a grid forecast against a swath in **observation space** |
| **curvilinear source** | nowcast blend — radar homogenized onto the node grid, answer served as a box | radar vs. satellite compared in either's native geometry |

- **Source role** (the *declaring* side — `Capability.domain`, `Coverage.domain`, the `self` side of
  `Domain.matches`): a producer *has* non-separable geometry. Committed by
  [product pillar 10](./product-roadmap.md) (local stations, regional radars, satellite products as
  sources). Proven by the **first non-separable producer**. Engineering: `matches` / `intersect` must
  compare a swath against a box.
- **Target role** (the *requesting* side — `Selection.domain`, the `other` side of `Domain.matches`,
  the output geometry of homogenization): a caller *asks for* values on non-separable geometry.
  Committed by **Phase 6** forecast-vs-observation verification done in **observation space** — the
  model is brought to the observation rather than the observation averaged onto the model grid, which
  avoids the representativeness error that would otherwise contaminate provider skill scores. The
  source may be a plain grid; only the target is curvilinear. Engineering: **`resample` must sample
  onto an arbitrary point set, not just a grid** — materially wider than
  [#5](#5-read-time-homogenization-fidelity) currently scopes.

Grid-space verification (observation → model grid) is then the special case where the target happens
to be separable; it needs neither role.

**Consequence for today's code.** Both roles being real is what keeps `Selection.domain`,
`Coverage.domain`, and `Capability.domain` typed as the base `Domain`: none of them can promise
separability. Consumers that *require* separability narrow at the use site (`isinstance(..., Separable)`
or to a concrete representation).

`Domain.matches` needs no special handling: it asks *"will I serve this request?"*, and a
representation that cannot determine whether it covers the request cannot serve it — `False` is the
correct answer, not a lossy collapse, and it is what lets the Arbiter skip that candidate and try the
next ([ADR-0002](./adr/0002-data-model.md)). What does need handling is a **rule** defined over a
restricted geometry: the `priority` reconciler composes a composite's `Domain` by comparing candidates
per-axis, so it validates that they are separable **before** comparing and rejects with a message
naming the producer. Without that precondition an all-`False` comparison set reads as *"incomparable
footprints, X/Y preference unbuilt"* — an explanation that points at the wrong problem. Because
composition happens as the graph is built, a curvilinear producer in a grid profile fails the build;
what stays invisible is the *request-path* skip, which is
[#36](#36-unserved-and-uncomparable-are-indistinguishable).

## 26. Provider / calculator plugin scaffolding

**Kind:** room-left (composition) · **Refs:** [ADR-0005](./adr/0005-build-time-composition.md),
[architecture §Config, binders, Weaver](./architecture.md#config-binders-weaver)

→ [ADR-0005: plugin binding](./adr/0005-build-time-composition.md#plugin-binding). Open: **where the
filled default catalogues live**, how **built-in vs optional** plugins are partitioned, and how
`compose` takes both catalogues symmetrically.

The composition root assembles maps by hand (`PROVIDER_CATALOG` / `CALCULATOR_CATALOG` in
`server.py`) and injects both into `compose`. That works while the shipped set is tiny. When
optional providers/calculators arrive, the root should select among **named shipped sets** (e.g.
builtin vs extended) without owning the membership lists, and `catalog/` should stay faces-only —
not import every concrete plugin.

Open: module home for shipped sets (`nodes/calculators/builtin` peer for providers?); whether
optional plugins are second maps, entry-point discovery, or install extras; keep enablement in
`Settings` / `ProfileConfig` separate from availability. No v1 blocker — mark before the second
optional calculator or a non-default provider packaging story forces an ad-hoc split.

## 27. Stored-calculator store binding

**Kind:** room-left (composition) · **Refs:** [ADR-0005](./adr/0005-build-time-composition.md),
[ADR-0004](./adr/0004-producer-resolution-and-capability.md),
[architecture §Store](./architecture.md#store--one-type-several-positions)

`CalculatorDef` carries `stored?` but **no store knobs**, so the Weaver has nothing to allocate a
stored Calculator's `Store` *from*. [ADR-0005](./adr/0005-build-time-composition.md) fixes only the
**timing** ("a stored Calculator's store can only be weave-allocated"), never **which spec**.
`weaver.py` passes `profile.root_store` into `stores.create(...)` for the `stored` branch — a
stand-in, not a decision. Nothing is wrong yet: v1's only calculator (wind) is `stored=False`, so the
branch is dead, and `StoreSpec` is an immutable value (each `create` still yields a distinct `Store`,
so ADR-0005's rejected *shared-instance* case is not what happens here). But a stored calc would
silently inherit the profile root's retention.

**Suggested resolution — not a new shape:** add an optional `store: StoreSpec | None` to
`CalculatorDef`, the exact peer of `OfferingDef.store`, carried onto `RegisteredCalculator` and read
by the Weaver when `stored=True`. This is ADR-0005's own rule — *same knobs shape everywhere,
separate instances per store position* (it rejected sharing one store **instance** while accepting one
`StoreSpec` **shape**). A `stored=True` def with no spec then becomes a `CompositionError` rather than
a silent root-store inheritance, mirroring `SourceBinder`'s "missing store for non-Countable source".

Open: whether a stored calc's lattice should instead derive from its resolved input domain (a
Calculator has no native lattice of its own), and whether "heavy" is a catalogue-side hint on
`CalculatorManifest` rather than a per-profile flag. No v1 work — this bites with the first heavy or
shared intermediate (the single-flight / common-subexpression case in
[ADR-0004](./adr/0004-producer-resolution-and-capability.md)), alongside
[#11](#11-incremental-synthetic-recompute).

## 28. Reconciler interface: selection-ordering vs per-cell fold

**Kind:** algebra-shaped (interface widening) · **Refs:** [ADR-0004](./adr/0004-producer-resolution-and-capability.md), [#6](#6-reconciler-catalogue)

The **`reconciler` slot** is real and the "one Arbiter shape" intent holds, but the **built interface is
narrower than the fold the design language assumes**, and the gap is not a configuration away.

As built, a `Reconciler` is a **selection-ordering** policy:
`select(parameter, candidates: Sequence[Producer]) -> Sequence[Producer]` — it ranks **producers** and
never sees values. The Arbiter then applies admission (`serves(parameter, sel.domain)`), takes the
**first admitted** candidate, and projects **that one producer whole** for the parameter. There is no
per-cell gather: no *0 → nodata / 1 → passthrough / ≥2 → reconcile* branch, and no sampling of *every*
producer onto the target lattice. Admission lives in the **Arbiter**, not the reconciler, so a
reconciler also cannot score geometry.

**Consequence — a combining reconciler cannot be dropped into this signature.** `tile` / `consensus` /
`feather` need the resolved contributions, so the Arbiter must project **all** admitted producers and
hand their values to the reconciler — a second, wider method (shape: `fold(parameter, contributions) →
ParameterData`), not another `select` implementation. Three claims in the design language depend on that
widening and are **not true of the current build**: (1) the per-cell fold itself; (2) the
**gap-filler** story (a low-priority whole-coverage producer filling where a hi-res one does not reach —
the hi-res producer simply wins the whole parameter under the implemented interface); (3) **runtime-fault fall-through** to the
next candidate and per-parameter partial success.

Not a v1 gap: v1 ships only `priority`, and point/timeline producers fully overlap, so selection *is*
the whole job and the narrow interface is exactly sufficient. This concern records the **cost of the
extension** so it is not mistaken for a config change: it lands with the catalogue
([#6](#6-reconciler-catalogue)), presses toward `PerPoint` provenance
([ADR-0003](./adr/0003-provenance-and-origin.md)), and wants the first real partial-coverage producer
set to prove it.

## 29. Narrated reach: what a profile promises

**Kind:** surface/product seam · **Refs:** [ADR-0007](./adr/0007-capability-carries-its-domain.md) (the mechanism), [#30](#30-response-membership-under-runtime-degraded-fallback), [#28](#28-reconciler-interface-selection-ordering-vs-per-cell-fold)

A surface needs to tell callers **how far this profile reaches** — the MCP tool
description narrates it, and the edge uses it to author the default window when the caller omits
`end`. The mechanism is **Reach**: the per-parameter `Domain` a `Capability` publishes, composed up the
graph and read off the woven root ([ADR-0007](./adr/0007-capability-carries-its-domain.md)). What stays
open here is the **product** question, not the mechanism: **what a profile should promise**, given that
the declared geometry can still overstate what a running system will serve — a provider that is down
([#30](#30-response-membership-under-runtime-degraded-fallback)), or an admission path that tightens
below geometry (resampler-reachability, probed availability). The surface folds `min` over the
parameters *it* exposes — surface-specific, so it stays at the edge, and exact only while the surface
pins the axes it is not folding.

Why a per-axis join is invalid →
[ADR-0007: Why per-axis folding is invalid](./adr/0007-capability-carries-its-domain.md#why-per-axis-folding-is-invalid).

`serves` remains the **sole admission authority** — not because reach is a lesser value (it is the same
`Domain`), but because admission is allowed to be **stricter** than declared geometry. What a surface
narrates is therefore an upper bound on what a running system will serve, and the gap is the open part:
[#30](#30-response-membership-under-runtime-degraded-fallback) (a provider that is down) and the
resampler-reachability / probed-availability seams inside `serves`
([ADR-0004](./adr/0004-producer-resolution-and-capability.md)). Whether a profile should narrate the
declared bound, or something hedged against those, is a **product** decision this concern owns.

**Why one reach and not a quality/completeness ladder.** A **quality reach** (how far every parameter
comes from its best source) is rejected because **quality is a policy outcome, not a capability**.
Capability answers *can you serve this*; quality answers *how well did it go*, which the **response**
already reports per parameter via
provenance. Trying to declare it produced four symptoms of the same error — it leaked priority
ordering ([#7](#7-quality-scoring)), its meaning flipped with the reconciler mode, it was unverifiable
through `serves` (which is `any(...)` — it answers *whether*, never *who*), and it gave the agent no
decision procedure (no "how much worse"). A deployment that genuinely sells quality tiers expresses
them as **separate profiles behind separate tools**, matching the sibling-tool precedent for a daily
product rather than modulating one tool.

Producer selection lands near the same place from the other direction: the narrated reach *is* the
spatially-dominant source's own horizon. That is a coherent product promise ("this surface serves N
days") rather than a leaked policy boundary — the difference is that it is stated as **what the
surface delivers**, not as **where quality changes**.

A `max`-over-parameters boundary was likewise rejected: a `max` fold is **existential** ("*something*
reaches this far"), unusable until you know *which*, and it **over-promises**. Existential facts need
per-parameter structure, and structure needs a surface that can return it.

Deliberately **coarse and profile-level**: no per-parameter matrix in a description string. Per-parameter
reach is also **never a request axis** — the one-domain `Selection` encodes the profile as a united
bundle; divergence surfaces as per-parameter **dropout with reasons** and, when structural, as
introspection-tool structure →
[architecture: Failure, nodata, and availability](./architecture.md#failure-nodata-and-availability).

Open parts:

- **The shape of the config lever.** ADR-0007's recorded lever lets an operator **narrow the candidate
  set** — excluding a producer from the promise, so a `Global × 10 d` fallback cannot cap a
  `Global-minus-poles × 16 d` primary. Its shape is deliberately **unspecified**. Declaring *dense axes*
  per profile is rejected because density is neither a
  per-axis boolean nor independent of the request: a polar swath's X/Y is **curvilinear**, not sparse,
  and its answerability depends on the caller issuing a **"fat" T request** spanning revisits. Whatever
  the lever becomes, it must only **narrow candidates or assert an invariant** — never declare reach
  outright, which would be a second source of truth that can drift from the members.
- **Which compositions hole, and which are products.** Holes come from **observation-shaped and
  archive-shaped** sources; forecast-grid sources do not hole. Station networks (X/Y point set +
  irregular T), gapped grid archives (T), radar mosaics (X/Y edges), and polar swaths (curvilinear
  X/Y, no Z hole) are all real products; **disjoint regionals with no fallback** is a misconfiguration
  rather than a product, and sparse vertical profiles do not arise until Z is a request axis. **No v1
  source can hole** (→ ADR-0007 Consequences), so the raise guards a seam v1 cannot reach.
- **Location-blindness.** A static description string states one number, but reach is a `Domain` —
  with regional providers the servable window genuinely varies by lat/lon and no static prose can say
  so. Selecting the spatially-dominant producer keeps this *safe* (the narrated window is servable
  wherever the profile serves at all) at the cost of understating it where coverage is better. Stating
  the per-location truth is the concrete trigger for the deferred **capabilities-introspection tool**
  (v1-requirements), which takes a lat/lon and can return structure.
- **Backward reach** (historical provision — the archive / run-collection seam) is the other half of
  the same facet. Because reach is a `Domain` rather than a forward scalar, it should absorb this
  without a contract change.
- What a request *beyond* reach receives is **response membership**, a separate policy →
  [#30](#30-response-membership-under-runtime-degraded-fallback). Reach says where the edge is;
  membership says what happens past it.

## 30. Response membership under runtime-degraded fallback

**Kind:** serving policy (low priority — no v1 work, no v1 exercise) · **Refs:** [#13](#13-candidate-admission-containment-vs-intersection), [#28](#28-reconciler-interface-selection-ordering-vs-per-cell-fold), [#29](#29-narrated-reach-what-a-profile-promises), [ADR-0003](./adr/0003-provenance-and-origin.md)

**The case:** a long-footprint primary **faults at runtime** on a request that exceeds the
fallback's reach. The partial-success fall-through reaches only **admitted** candidates, and the
shorter fallback failed whole-request containment — so the
parameter is dropped entirely while the fallback holds most of the window. Real data left on the
table, and the client must re-request shorter: client load a good product should absorb.

**This is a `priority`-mode artifact, not a standing defect.** It exists
because **wholesale fallback admits by whole-request containment**, which filters a partial producer
out of the candidate set before the reconciler ever sees it. Under an **amendment / splice** mode the
shorter fallback is admitted by **intersection**
([#13](#13-candidate-admission-containment-vs-intersection)) and contributes its 10 days through the
per-cell fold ([#28](#28-reconciler-interface-selection-ordering-vs-per-cell-fold)). So the honest
framing is: **the mode that fixes this is the same mode padding needs** — padding is not a rival to
the reconciler widening, it is one of its consequences (plus the reason channel below). What remains
genuinely open is only whether a profile *stuck on* `priority` should get a padded tail, which is a
narrower question than it first looked.

**Why only this ordering** (*under `priority`*). Admission compares a candidate's reach to the
**request**, not to the primary — so the two orderings are structurally different, and both are real
production shapes:

- **Fallback longer** (short high-priority primary, long fallback): the fallback is admitted wherever
  the primary was *and further*, so it substitutes **wholesale** and the answer is **complete** — only
  quality changes. Nothing is lost, so membership has nothing to decide, and the change is visible
  ex post in per-parameter provenance. (The surface does **not** narrate where this happens: quality is
  a policy outcome, not a capability →
  [#29](#29-narrated-reach-what-a-profile-promises).) Its one residual want — the primary for the near
  window *and* the fallback for the tail, in one response — is **amendment**, not membership:
  [#28](#28-reconciler-interface-selection-ordering-vs-per-cell-fold)'s coverage reconciler.
- **Fallback shorter** (this concern): the fallback is admitted only on requests within its own reach,
  so fall-through is unavailable **precisely on the long requests where a primary fault hurts most**.
  The fallback is useless exactly when it is needed.

**Nodata-padding is the preferred answer — the client wants maximum relevant
data in one go — but it is low priority.** It needs three widenings, none of which this case alone
justifies pulling forward: intersection admission
([#13](#13-candidate-admission-containment-vs-intersection)), the degenerate per-cell fold
([#28](#28-reconciler-interface-selection-ordering-vs-per-cell-fold)), and a **per-cell reason
channel** — `present=False` currently means a *successful* gap, so a padded tail is indistinguishable
from measured absence (the `PerPoint` provenance seam,
[ADR-0003](./adr/0003-provenance-and-origin.md)). Until then, **omission + per-parameter reason** is
the terminus: it carries the same information a padded tail would, minus the ambiguity.
The interim cost is payload, not correctness. A server-side **strict mode** is declined — an
explicit-absence response lets a strict client enforce all-or-nothing with one `if`.

**Cases considered and dissolved** (so they are not re-litigated):

- **Single-vendor short parameter**: *not* heterogeneity. The operator bundles knowing
  what the market serves — if soil moisture reaches 7 days, the agriculture profile **is** a 7-day
  product. Supply constrains where the bundle's boundary sits; it does not force a heterogeneous
  bundle. That boundary is the profile's narrated
  [reach](#29-narrated-reach-what-a-profile-promises), declared up front.
- **Nowcast blend** (radar ~2 h + NWP beyond): a **taxonomy error** to file here. Radar is not a
  fallback for a 16-day request — the model **amends** the radar, both contributing to one
  `ParameterData` per cell. That is *who fills each cell* (the coverage reconciler,
  [#28](#28-reconciler-interface-selection-ordering-vs-per-cell-fold) / the recorded
  "obs + forecast along `valid_time`" extension point), not *who wins the parameter* (fallback).
- **Archive breadth**: a decades-long fetch is **batched**, so padding payload never arises; and its
  right policy is **strict** — a 50-year series with a parameter silently missing is a corrupted
  dataset, not a partial answer.

**Residue — a different problem.** A station that began measuring humidity in 2003, inside a
1990–2020 request, is **intra-parameter temporal availability**: genuine nodata (the producer
succeeded; it has no value there), plus a *slice-extraction* need ("which intervals are useful?") that
is introspection/metadata, not response shape. Filed here only so it is not mistaken for this concern.

**Three policies stay distinct:** **fallback** (who serves — the reconciler's),
**membership** (what a beyond-boundary request gets — this concern), **narration** (what the client is
told up front — [#29](#29-narrated-reach-what-a-profile-promises)).

## 31. Positional alignment is asserted, never checked

[`Coverage`](../src/meteoscape/manifold/core.py) states the invariant — `capability`, `ranges`, and
`provenance` share one parameter key set and **align positionally** over `domain`, so
`ranges[pid].values[i]` is `pid` at the domain's i-th point — and nothing verifies it.

**Not a live defect.** Every construction site is safe *by construction*,
not by luck: `sampling` maps over an index list sized to the target domain; `arbiter` moves whole
`ParameterData` objects between Coverages whose domains it has already compared; `open_meteo` checks
length explicitly at both sites; and `Calculator`'s kernel is the one caller that authors `domain`
and `ranges` independently — but the only kernel that exists (`wind_from_uv`) computes element-wise
and returns its input domain unchanged, so its ranges cannot differ in length from it.

**What opens the hole** — either of these, whichever ships first, should add the check and own it:

- **A non-pointwise kernel.** A windowing calculator ("daily max of hourly accumulation", anticipated
  by [ADR-0002](./adr/0002-data-model.md)) computes a coarser Domain *and* shorter ranges separately;
  an off-by-one on a partial trailing window yields a 7-cell domain and 8 values. Validate at the
  plugin boundary in `Calculator.project`, where the error can name the kernel
  ([ADR-0004](./adr/0004-producer-resolution-and-capability.md) already requires this).
- **Store read-back** ([ADR-0006](./adr/0006-materialization-granularity-and-store-shape.md)). The Store holds
  *independently replaceable* per-Parameter units, so reassembly joins separately-persisted pieces —
  a partially-written or stale unit is the first payload that can be the wrong length without a bug
  in the assembling code. Validate on `CoverageRecord` itself, since the pieces arrive from storage
  rather than a caller.

**Length is only a proxy.** It cannot catch transposed axis order or a value list built by iterating
a `dict` instead of the domain — both are the right length and both silently read values against the
wrong coordinates. Order is held by the convention that every producer builds values by iterating the
domain (or index-maps from a source), and by universal agreement on the `AXIS_ORDER` flattening. A
check that catches the length class should not be described as enforcing alignment.

**Deliberately excluded:** the invariant's *provenance* arm. `Uniform` is keyless by construction,
`PerParameter` has keys, `PerPoint` is deferred — comparing key sets across them needs a
`ProvenanceField.covers()` seam, a real design decision that belongs with the per-parameter omission
contract → [architecture: Failure, nodata, and availability](./architecture.md#failure-nodata-and-availability).

## 32. Footprint-aware ranking inside the algebra

**Kind:** room-left (extension) · **Refs:** [ADR-0007](./adr/0007-capability-carries-its-domain.md), [#29](#29-narrated-reach-what-a-profile-promises), [#7](#7-quality-scoring), [#28](#28-reconciler-interface-selection-ordering-vs-per-cell-fold)

The **placement** question this concern opened is closed — the declared geometry is on the `Capability`,
so it is reachable at request time ([ADR-0007](./adr/0007-capability-carries-its-domain.md)).

**What stays open is the extension that motivated it:** a **footprint-aware `reconciler`** that ranks
candidates by how tightly each covers the request (prefer a regional high-resolution producer over a
global one), adjacent to [#7](#7-quality-scoring). The geometry it would rank on is now published, so
what remains is the **ranking policy** and the `Reconciler` interface widening it needs
([#28](#28-reconciler-interface-selection-ordering-vs-per-cell-fold)).

**Ranking is a separate mechanism from composition.** They share the published geometry and nothing
above it:

| | Reach | Footprint-aware reconciler |
|---|---|---|
| Output | **one** `Domain`, per parameter | an **ordering** over candidates |
| When | build time, static | per request, dynamic |
| On ambiguity | **raises** (misconfiguration) | ranks anyway; ambiguity is normal |
| Purpose | narrate one product promise | pick the best producer for *this* request |

So a reconciler wanting this does **not** want a `ReachRule` — it wants per-candidate footprint access,
which `build_reconciler` can already obtain from the registries at build, or which would justify
exposing footprint on the `Capability` surface if it must be read per request.

**Terminology:** Reach (what a Manifold publishes it serves) vs Footprint (a producer's own
declaration, before composition) → [glossary](./glossary.md): Reach, Footprint.

**Trigger to revisit:** a profile that needs per-request producer *ranking* rather than the wholesale
`priority` fallback — the first regional high-resolution provider alongside a global one. Nothing about
the geometry blocks it now; the reconciler interface does
([#28](#28-reconciler-interface-selection-ordering-vs-per-cell-fold)).

## 33. Reconciler owns domain composition

**Kind:** policy coherence (contract-level) · **Refs:** [ADR-0007](./adr/0007-capability-carries-its-domain.md), [#29](#29-narrated-reach-what-a-profile-promises), [#28](#28-reconciler-interface-selection-ordering-vs-per-cell-fold), [#6](#6-reconciler-catalogue), [#32](#32-footprint-aware-ranking-inside-the-algebra)

The **coherence** half is settled — domain composition is a `Reconciler` member, so it moves with the
reconciler and cannot be paired incoherently
([ADR-0007](./adr/0007-capability-carries-its-domain.md)).

**What stays open is the member's shape.** `priority` composes by dominance-or-raise; `tile` would
compose a spatial union, `splice` a temporal one. Whether one signature serves all three is unknown
until a second reconciler is built — the same uncertainty
[#28](#28-reconciler-interface-selection-ordering-vs-per-cell-fold) records about `select`, and the
reason a reshape is expected rather than feared.

## 34. Producer-DAG walking is duplicated

**Kind:** room-left (build-time structure) · **Refs:** [ADR-0005](./adr/0005-build-time-composition.md), [ADR-0007](./adr/0007-capability-carries-its-domain.md)

Two build-time passes walk the same producer DAG over `ProfileDef`. A third — the standalone reach
resolver — was removed by [ADR-0007](./adr/0007-capability-carries-its-domain.md): the capability tree
already composes that geometry structurally, so recomputing it over `ProfileDef` was duplicate work.

- **`Weaver._weave_calculators`** — memoizes a `Producer` per `CalculatorKey`, with a `visiting` set
  raising `CompositionError("calculator cycle at ...")`. A **backstop**: `compose()` validates before
  weaving, and `validate_calculators` is required to reject every cycle the Weaver cannot build, so
  this should never fire. The two messages differ deliberately — the operator's names the whole cycle —
  so if it ever does fire, which guard caught it is observable.
- **`validate_calculators`** — checks every Calculator input is producible; owns the operator-facing
  `visiting` cycle guard and the wiring errors, and runs first
  ([ADR-0007](./adr/0007-capability-carries-its-domain.md)). Its guard must be **exactly as strict as the
  Weaver's**: it descends into upstream calculators even when a source also serves that input, because
  the Weaver scopes each input Arbiter over *all* producers of it. A cycle a source shadows is still
  unbuildable — and slipping one past this pass hangs the next one.
`validate_calculators` carries its own guard so it stays standalone and unit-testable without weaving —
**deliberate duplication of ~3 lines**, not an accident.

**The two walks diverge** — the Weaver builds `Producer`s and composes each node's `Capability`
geometry as it goes; `validate_calculators` checks presence and cycles — so a premature extraction
would abstract over two different bodies. Extract when they stop diverging (or a third appears, e.g.
a resolution-trace builder [#14](#14-resolution-trace-and-observability)). The shape would be a pure
`ProfileDef` traversal yielding a topologically-ordered producer graph the consumers share; the cycle
check moves there. Pure refactor, no contract change. Do not extract preemptively — while the bodies
diverge, the indirection costs more than it saves.

## 35. Calculator satisfiability vs optional-provider degrade

**Kind:** composition policy · **Refs:** [ADR-0007](./adr/0007-capability-carries-its-domain.md), [v1-requirements](./v1-requirements.md) (graceful degrade)

A Calculator whose input **no producer serves** is a build-time
`CompositionError` naming the calculator + input: declaring a Calculator is an operator **promise**, so
an unwired input must fail loudly at build, not surface as an accidental runtime `capability-mismatch`.
This is strict and correct for v1, where every Calculator input (`wind_u` / `wind_v`) comes from
Open-Meteo — the always-on keyless primary — so the strict check can never collide with graceful
degrade.

**The collision is a future question.** If a Calculator input were served *only* by an **optional**
provider (one that degrades away on a missing secret), the strict rule would fail the build where
graceful degrade intends the server to start without that capability. Two resolutions, undecided:
(a) **fail the build** — force the operator to drop the Calculator or keep the provider; matches
"Calculator = promise". (b) **drop the unsatisfiable Calculator** like a degraded provider and narrate
the reduced set; matches "optional provider = availability". No v1 driver.

**Related, broader:** an operator wants to assert a composition *serves what they expect* — but
graceful degrade deliberately won't hard-fail on a missing *provider* parameter, so this is an opt-in
"validate my profile serves {…}" mode, not a hard rule. A product-side want, not v1 → [ideas](./ideas.md).
