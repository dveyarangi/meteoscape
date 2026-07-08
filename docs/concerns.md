# Open concerns

Open design concerns, **ordered by priority** (highest first). Priority blends *how much it blocks the
encoding pass / v1 build* with *how hard it is to absorb additively later*. `architecture.md` indexes
this file by subtitle. **Numbers are stable IDs, not contiguous ranks** — when a concern is settled it
**moves out** to its owning ADR, leaving a gap. (Settled earlier: nodata/mask + temporal-cell + the
parameter functional model → [ADR-0002](./adr/0002-data-model.md); per-point provenance →
[ADR-0003](./adr/0003-provenance-and-origin.md); capability propagation — the base-`Manifold` facet and
its leaf/composite family — → [ADR-0001](./adr/0001-manifold-algebra-and-composition.md) /
[ADR-0004](./adr/0004-producer-resolution-and-capability.md) — the clock-anchored footprint reach is v1,
its accuracy is [#18](#18-clock-anchored-footprint-fidelity), and only *probed* real-availability stays an
ADR-0004 deferred seam.)

---

## 4. issue_time definition

**Kind:** algebra-shaped (metadata) · **Refs:** [ADR-0002](./adr/0002-data-model.md), [ADR-0003](./adr/0003-provenance-and-origin.md)

The **status is resolved**: `issue_time` is **demoted from a Domain axis to a provenance stamp** — run
identity on the atomic `Origin` (ADR-0002 / ADR-0003); it is never interpolated, snapped, or requested.
What remains is its **meaning**: a sharp, generalized definition — model **run time** vs **publication
time** vs **assimilation window** — and how it is set for **observations** (no forecast run) and for
**synthetic / derived** `ParameterData` (which inherit from multiple parents). Prerequisite for
[cross-run combination](#9-cross-run-combination).

**Freshness ties to this.** A `ParameterData` is fresh while its run (`issue_time`) is **still current**;
`expiration` (`fetched_at + cadence`) is a **proxy for run-rollover** — when the next run supersedes this
one. With a real rollover signal the proxy is exact; an **over-estimated cadence** opens the one window
where a previous run's entries still read as fresh after the new run lands (the only time two runs' entries
coexist, hence the only risk of cross-run mixing). v1 sidesteps it (single latest run). The real signal is
the `ideas.md` provider-real-freshness upgrade.

## 18. Clock-anchored footprint fidelity

**Kind:** edge-isolated (capability) · **Refs:** [ADR-0004](./adr/0004-producer-resolution-and-capability.md), [ADR-0002](./adr/0002-data-model.md), [#4](#4-issue_time-definition)

v1 admits providers by **temporal containment** against a **clock-anchored footprint window**
`[now − retention, now + lead]` (the continuous `FootprintDomain`,
[ADR-0002](./adr/0002-data-model.md)). But a provider's real availability is **run-phased and
latency-delayed**: the latest run `r` sits on the cadence grid, becomes available only at
`r + publication_latency`, and covers `[r, r + max_lead]`, so the faithful forward edge is
`latest_available_run + max_lead` — which drifts **below** `now + lead` as the run ages (by up to a
cadence + latency). Anchoring naïvely to raw `now()` therefore **over-promises** at the forward edge when
the run is stale (admit → the fetch returns short / nodata, surfacing as **nodata / runtime**, not
**capability-mismatch**) and **flickers** at the boundary as `now()` moves continuously. Open: the
**offset** (subtract publication latency) and **rounding** (floor `now` to the run cadence) that derive
the *effective* anchor (`latest_available_issue_time`) from `now`, using the provider's **cadence +
latency** facts (cadence already the freshness proxy, [#4](#4-issue_time-definition)). v1 can ship a
**conservative default** (round `now` to the hour, generous `retention`), accepting occasional edge
nodata; precise per-provider latency / rounding is the open work. Additive; no contract change.

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
stations, mixed grids), and the **provider "exact" capability** (a vendor that serves true off-grid
points, bypassing the store-grid floor) are the later stress on the kernel.
Contained behind the sampling seam. This concern owns **how accurately** a coarsened value is computed;
**which** cell statistic it should be, and how a request asks for it, is
[#15](#15-coarser-grid-resampling-and-aggregation-semantics).

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

## 7. Quality scoring

**Kind:** deferred seam · **Refs:** [ADR-0004](./adr/0004-producer-resolution-and-capability.md), [ADR-0001](./adr/0001-manifold-algebra-and-composition.md)

Quality is **implicit in Arbiter ordering** (static priority). This may prove insufficient — *when does a
static order start returning visibly worse data than an available alternative?* A request-aware **scorer**
can replace the static order behind the **same selection signature** (ADR-0004: the static order is the
degenerate constant scorer). The same seam covers the **match-cost tier of capability** — degrading
conversion edges (e.g. disaggregating 3h into 1h), which only *grow* a producer's closure. The
**metadata-only soft tier** fits the read-only algebra untouched; a scorer that **probes** sources needs
state + I/O at selection time, reopening [Arbiter → Broker](#8-arbiter-to-broker-pressure).

## 8. Arbiter to Broker pressure

**Kind:** algebra-shaped (boundary) · **Refs:** [ADR-0001](./adr/0001-manifold-algebra-and-composition.md)

ADR-0001 keeps acquisition a **property of a shape**, not a coordination layer above the algebra, and the
Arbiter is a stateless transformer. If acquisition later grows real logic — live latency probing,
sampling at selection time, failure-adaptation — the Arbiter boundary may have to **harden into a richer
acquisition shape (a "Broker")** with state and I/O at selection time. A larger, separate decision; the
soft (metadata-only) tier of [quality scoring](#7-quality-scoring) deliberately stays on the near side of
this line.

## 9. Cross-run combination

**Kind:** deferred seam · **Refs:** [ADR-0002](./adr/0002-data-model.md), [ADR-0004](./adr/0004-producer-resolution-and-capability.md)

A v1 `ParameterData` is **single-origin**, with its run identity carried by the provenance `issue_time`;
the enclosing Coverage has no shared run identity. Combining runs for one parameter is a **reconciler
folding run-stamped contributor Coverages along `valid_time`** (ADR-0004), yielding a synthetic origin —
*not* interpolation along an `issue_time` axis (there is none; `issue_time` is a provenance stamp —
ADR-0002 / ADR-0003). Archives that retain many runs are a **collection keyed by `issue_time`** (the
categorical-key seam, generalizing to ensemble / scenario). The semantics (which run wins where, blended
consensus, how observations join forecasts along `valid_time`) are undecided and depend on a sharpened
[issue_time definition](#4-issue_time-definition).

## 10. Parameter conventions

**Kind:** edge-isolated · **Refs:** [architecture.md](./architecture.md#deferred-decisions), [ADR-0002](./adr/0002-data-model.md)

Canonical **parameter names, units, and spatial-ref encoding** are deferred at the contract level.
Normalizers reconcile vendor units into the **one canonical unit per parameter** (the
canonical-mono-unit invariant, [ADR-0002](./adr/0002-data-model.md)), but the canonical set itself is
unspecified. The *structure* the vocabulary must fill is fixed — quantity identity, the quantity
`extent_scaling`, and the extent-scaling–driven conversion graph ([ADR-0002](./adr/0002-data-model.md))
— as is the **delivery seam**: `ParameterDef`s are fetched from an injected **parameter table** (a
swappable interface; v1 ships a static one hosting the v1 parameters). What remains deferred is the **concrete
quantity table content (beyond the v1 set) and the conversion-edge qualities**. Contained inside the
Provider / Normalizer seam — safe to defer.

## 11. Incremental synthetic recompute

**Kind:** deferred (optimization) · **Refs:** [ADR-0003](./adr/0003-provenance-and-origin.md)

A synthetic `ParameterData` re-derives whenever **any** parent expires (worst-case `min` expiration —
ADR-0003). Recomputing **only the stale sub-domain** instead of the whole is an **unmodeled optimization**.
Purely a performance concern; correctness is unaffected by deferring it.

## 12. Curvilinear domains

**Kind:** room-left (interface promise) · **Refs:** [ADR-0002](./adr/0002-data-model.md)

ADR-0002 makes the `Domain` interface **non-separable by default** so curvilinear geometries — radar
geotangent slices, satellite swaths — can be a **representation** later without a contract change. Not
built: the interface-conformance is a **promise**, proven by the first non-separable producer. Until then
it is only a constraint on the Domain interface (don't assume per-axis separability), not a v1 work item.

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

## 17. Vector-parameter coupling across the Arbiter

**Kind:** algebra-shaped (boundary) · **Refs:** [ADR-0004](./adr/0004-producer-resolution-and-capability.md), [ADR-0002](./adr/0002-data-model.md)

Wind is canonical as two **independent** scalar parameters `wind_u` / `wind_v` (ADR-0002), but the
per-parameter Arbiter selects each parameter's producer **independently**. Nothing in the algebra forces
`wind_u` and `wind_v` to resolve to the **same provider/run** — mixing provider A's `u` with B's `v` is
an **incoherent vector**, and the derived `wind_speed` / `wind_direction` computed from a mismatched pair
are physically wrong. The same holds for any future multi-component quantity (vector, complex, paired
statistics). **v1 is unaffected**: a provider serves wind as one native fetch, so the Normalizer
co-produces `u` and `v` from one origin and, under a single shared priority order, both resolve to the
same provider (it serves both components or neither). The open question is whether coherent
multi-component parameters need a **first-class coupling** — a co-selected parameter group the Arbiter
resolves **atomically** (all components from one contributor) — vs. leaving it a **convention** the
Normalizer / Weaver upholds. Additive; no v1 work.

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
