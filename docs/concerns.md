# Open concerns

Open design concerns, **ordered by priority** (highest first). Priority blends *how much it blocks the
encoding pass / v1 build* with *how hard it is to absorb additively later*. `architecture.md` indexes
this file by subtitle. **Numbers are stable IDs, not contiguous ranks** — when a concern is settled it
**moves out** to its owning ADR, leaving a gap (what each ADR owns →
[architecture: ADR index](./architecture.md#adr-index)).

---

## 5. Read-time homogenization fidelity

**Kind:** edge-isolated · **Refs:** [ADR-0001](./adr/0001-manifold-algebra-and-composition.md), [ADR-0002](./adr/0002-data-model.md)

**Mechanism resolved (and in v1):** every `Reservoir` `quantize`s a request for retention and
**homogenizes** the stored cells onto the requested `Domain` at read, so `project(sel)` honours
`sel.domain` — the pipeline, single-origin units, and same-run fusion live in
[ADR-0001 §materialization](./adr/0001-manifold-algebra-and-composition.md),
[ADR-0003](./adr/0003-provenance-and-origin.md), and [architecture §Reservoir](./architecture.md#reservoir).
On-grid reads degenerate to a **lossless crop**; the open question is the off-grid kernel.

**What's open is fidelity:** the **kernel choice** per field axis — the resampler registry's
implementations (nearest / linear / cubic; **conservative / area-weighted** for extensive
re-aggregation; the non-linear `circular` / categorical kernels for scales v1 does not exercise, since
wind rides as linear u/v components) — and the acceptable **accuracy bounds**; ADR-0002 fixes only
*which* axes admit a kernel and that a storing grid imposes a **fidelity floor**, not the method. v1
ships the **degenerate nearest-neighbor** kernel (kind-agnostic, pluggable) — it honours `sel.domain`
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

## 21. `serves` reach vs `project` crop-ability

**Kind:** algebra-shaped (Capability dual) · **Refs:** [ADR-0004](./adr/0004-producer-resolution-and-capability.md), [#5](#5-read-time-homogenization-fidelity), session 0008

ADR-0004 defines `serves` as *whether a valid non-lossy resampler path exists* from offered → requested;
`Domain.contains` is only the **geometric half**. Phase B shipped that half alone: `EnumerableCapability.serves`
(and leaf footprints) admit by **extent reach**, while `Coverage.project` / the sampling engine only
perform an **aligned identical-step crop** — off-phase or non-identical-step selections that still sit
inside the span are admitted, then fail at `project` with `NotImplementedError` instead of a clean
admission miss (`capability-mismatch` / Arbiter fall-through).

**v1 is unaffected** (hourly on-lattice requests). **Close inside `serves`**, not with a second check in
`Arbiter.project`: deepen the Capability predicate with the resampler / alignment branch (registry at
007; extensive horizon edge at 002). Composites (`Union` / `Derived`) and the Arbiter inherit
correctness unchanged — blast radius stays behind the Capability facet. Until then, engine
`NotImplementedError` is an internal assert that `serves` over-promised, not the normal edge path.

## 22. Lattice helpers vs `domain` / `sampling` module split

**Kind:** room-left (module layout) · **Refs:** session 0008, Phase B wrap

Index arithmetic (row-major encode/decode, `sub_lattice_offset`, `AXIS_ORDER`) is owned by `domain.py`
today; `sampling.py` consumes it one-way (`sampling → domain`, never the reverse). That matches the
geometry-vs-value-transfer cut. If Domain grows heavy with non-lattice geometry *and* lattice math, or
a third consumer appears (`quantize`, store grids), **carve a thin `lattice.py`** that both import —
pure refactor, no contract change. Not blocking; do not split preemptively.

## 23. Spatial vs temporal `RegularAxis` types

**Kind:** room-left (types / hot path) · **Refs:** ADR-0002, Phase B wrap

`RegularAxis` today is one type over `Coordinate = float | datetime` and `Step = float | timedelta`.
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

ADR-0004 settles the reconciler **topology** (one Arbiter, one declared `reconciler`, per-cell fold), but
the concrete catalogue beyond the default `priority` — `tile` (disjoint union), `consensus` (blend),
`feather` (smoothed seam) — and their precise per-cell semantics are **unspecified**. Unproven until a
real partial-coverage producer set exists. `consensus` / `feather` press toward per-point provenance
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

**Z half settled (session 0011):** vertical matching is **axis-kind-owned** — neither containment nor
intersection globally → [ADR-0004](./adr/0004-producer-resolution-and-capability.md). The open part of
this concern is now only the **partial spatial/temporal producer** admission above.

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

Canonical **parameter names, units, and spatial-ref encoding** are deferred at the contract level.
Normalizers reconcile vendor units into the **one canonical unit per parameter** (the
canonical-mono-unit invariant, [ADR-0002](./adr/0002-data-model.md)), but the canonical set itself is
unspecified. The *structure* the vocabulary must fill is fixed — quantity identity, the quantity
`extent_scaling`, and the extent-scaling–driven conversion graph ([ADR-0002](./adr/0002-data-model.md))
— as is the **delivery seam**: `ParameterDef`s are fetched from an injected **parameter table** (a
swappable interface; v1 ships a static one hosting the v1 parameters). The **v1 canonical set** (the 5
canonical + 2 derived parameters and their committed units) is recorded in
[`parameters.md`](./parameters.md); what remains deferred is the **concrete quantity table content (beyond
the v1 set) and the conversion-edge qualities**. Contained inside the Provider / Normalizer seam — safe to
defer.

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

## 18. Clock-anchored footprint fidelity

**Kind:** deferred (tuning) · **Refs:** [ADR-0003](./adr/0003-provenance-and-origin.md), [ADR-0004](./adr/0004-producer-resolution-and-capability.md)

The anchoring **mechanism is settled** ([ADR-0003](./adr/0003-provenance-and-origin.md)); what stays open
is **the numbers, not the shape**: the concrete per-provider `{Δ, L, max_lead}` (v1 ships a **conservative
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

**Contract settled** — offerings as `SourceKey` instances; priority-first band walk with in-band
`score` fall-through; boolean `serves` + leaf `Capability.score` → `Domain.match`
(→ [ADR-0004](./adr/0004-producer-resolution-and-capability.md)); axis `step` + request-constrained
product / fine-enough fit (→ [ADR-0002](./adr/0002-data-model.md)); no native-fidelity provenance field
(→ [ADR-0003](./adr/0003-provenance-and-origin.md)). Provider `exact` and native-coarse-as-distinct-origin
→ [#5](#5-read-time-homogenization-fidelity) / [#15](#15-coarser-grid-resampling-and-aggregation-semantics).

**Open (additive build; v1 unaffected — one offering per provider, `contains`-only):** populate
continuous footprint **`step`s**, implement **`Domain.match`** / **`Capability.score`**, and the Arbiter
equal-priority band walk. Note (session 0011): **multi-level samples inside one vantage window**
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

**Kind:** room-left (interface promise) · **Refs:** [ADR-0002](./adr/0002-data-model.md)

ADR-0002 makes the `Domain` interface **non-separable by default** so curvilinear geometries — radar
geotangent slices, satellite swaths — can be a **representation** later without a contract change. Not
built: the interface-conformance is a **promise**, proven by the first non-separable producer. Until then
it is only a constraint on the Domain interface (don't assume per-axis separability), not a v1 work item.
