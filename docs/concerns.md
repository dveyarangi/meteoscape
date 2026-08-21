# Open concerns

Open design concerns, **ordered by priority** (highest first) and numbered by **stable ID**, so the
sequence is deliberately full of gaps — a settled concern has moved out to its owning ADR (what each
ADR owns → [architecture: ADR index](./architecture.md#adr-index)). `architecture.md` indexes this
file by subtitle.

This file owns unresolved design pressure — not delivery sequencing, and not decisions. How entries
are written, ordered, and retired is owned by
[/align](../.agents/skills/align/SKILL.md#extract-open-questions-and-risks).

---

## 39. Python embedding surface and public failures

**Kind:** Phase-1 product boundary · **Refs:** [architecture §Embedding surface](./architecture.md#embedding-surface),
[v1 requirements](./v1-requirements.md), [ADR-0005](./adr/0005-build-time-composition.md),
[Edge — Embedding surface](./edge/embedding.md)

The supported embedding surface has no selected facade or public failure contract. The package root
exports only `SourceKey` and `main`; the usable internal composition path requires profile types,
both plugin catalogues, a secrets map, and a `Clock`. Select the smallest stable construction and
request surface, whether its composition handle keeps the name `Gateway`, how third-party manifests
enter, and which import paths and compatibility guarantees are public.

The failure contract must distinguish bad input, capability mismatch, producer failure, build-time
misconfiguration, unbuilt engine paths, and invariant breaks without reporting an engine defect as a
producer fault. It must also define phase boundaries, actionable context, and what deliberately
escapes uncaught. Request-building ergonomics are part of the same facade decision; capability-aware
preflight remains bounded by [#40](#40-composing-servable-requests-at-the-embedding-edge).

→ queued as [supported-python-embedding](./tickets/01-0125-supported-python-embedding.md).

## 40. Composing servable requests at the embedding edge

**Kind:** edge product seam (driver arrives with the embedding surface's facade selection) ·
**Refs:** [#39](#39-python-embedding-surface-and-public-failures),
[Edge — Embedding surface](./edge/embedding.md), [ADR-0004](./adr/0004-producer-resolution-and-capability.md),
[ADR-0007](./adr/0007-capability-carries-its-domain.md)

An embedder composes a `Selection` by hand, and the only feedback that it was unservable is a
**`CapabilityMismatch`** raised after the request runs. That is acceptable as a *failure* category
and wrong as the *primary* channel: much of what it reports is knowable before the request is
issued. This concern owns the embedder-facing consequence — **which mismatch cases the edge can
dissolve, and what a request-composition helper may honestly promise given that `Capability` is not
a perfectly faithful self-description.** It does not own the facade shape (#39) or any of the
fidelity gaps individually (each is linked below); the wider per-surface sweep is deliberately
deferred to a later embedding-edge concern.

**Arm 1 — the dissolution inventory.** Every current raise site, classified by whether the edge can
make it unrepresentable:

| Class | Cases | Dissolvable at the edge? |
|---|---|---|
| **Shape** — a representation the resolver cannot serve | a snapped member against non-`Separable` answering geometry, and snapped against an axis that clips to no cells | Pure representation errors are dissolvable without a `Capability` read. Producer-dependent snapping is only advisory; snapped X/Y is request-invalid because temporal bounds cannot address a spatial axis. |
| **Coverage** — geometry outside what any producer admits | `Arbiter.project` finds no producer admitting any requested parameter | Partially pre-emptable against published Reach, within Arm 2's limits. An overlapping Snapped-T window is already trimmed rather than refused. |
| **Runtime / race** — true when asked, false when served | a rolling window moves before fetch; requested taps or delivered records ground differently; winner domains diverge; a producer is down ([#30](#30-response-membership-under-runtime-degraded-fallback)) | No — these belong to the answer, not the request. |

**Arm 2 — what a helper may trust about `Capability`.** A builder validating against capability
inherits capability's own inaccuracies, in both directions — each already owned elsewhere; what is
new here is that they bound what the edge can promise:

- `serves` is allowed to be **stricter** than the published reach (resampler-reachability, probed
  availability) → [ADR-0007](./adr/0007-capability-carries-its-domain.md),
  [#29](#29-narrated-reach-what-a-profile-promises): a reach-satisfying request can still miss.
- `serves` is currently **looser** than the engine: extent containment admits off-phase /
  non-identical-step selections the sampler cannot crop → [#21](#21-serves-extent-vs-project-crop-ability),
  where the symptom is an internal `NotImplementedError`, not even a clean mismatch.
- Declared windows are **clock-relative estimates**: a `RollingAxis` extent moves with the clock and
  unprobed provider timing may be conservative → [#18](#18-clock-anchored-footprint-fidelity).
  A reach read is instantaneous truth, never durable — an embedder that reads reach and composes a
  request later is already out of date.
- **Miss reasons are indistinguishable** — "does not cover" and "cannot be compared" are the same
  `False` → [#36](#36-unserved-and-uncomparable-are-indistinguishable); the reason channel is
  [#14](#14-resolution-trace-and-observability)'s trace.

**Open:**

- **Shape-safe constructors vs a capability-aware builder.** The first is cheap, total, and needs no
  capability read (it dissolves the whole Shape class); the second consults a live `Capability` and
  can only ever be advisory (Arm 2). Whether the edge ships one, both, or neither is a facade
  decision at #39.
- **Whether pre-flight validation is public API at all**, versus letting the request run and reading
  a reason — which presumes #14's trace exists and is actionable.
- **Whether declaration fidelity deserves its own check**: a conformance harness comparing a
  provider's declared footprint against what it actually serves, parallel to Provider parity but
  aimed at declarations rather than values, would convert several Arm 2 unknowns into
  tested facts.

**Trigger:** #39's facade selection — a request-composition helper is part of choosing the public
surface. Until then this is an inventory to keep current: **every new `CapabilityMismatch` raise
site should be classified into the Arm 1 table as it lands.**

## 48. A tap cannot declare where its value sits relative to the tick

**Kind:** algebra-shaped (declaration gap) · **Refs:** [ADR-0002](./adr/0002-data-model.md),
[parameters.md](./parameters.md), [edge/provider.md](./edge/provider.md),
[#15](#15-coarser-grid-resampling-and-aggregation-semantics)

`TimelineProvider` stamps one cellular T lattice on every record, so a tick at `T` currently declares
the cell `[T, T+step]`. A tap cannot say whether its vendor value is instantaneous at `T`, summarizes
the preceding cell, or summarizes the following cell. Real providers exercise each case:

| Vendor field | Native meaning | Current representation |
|---|---|---|
| Open-Meteo `precipitation` | preceding-hour integral `(T−1h, T]` | **wrong:** following cell `[T, T+1h]` |
| TWC `qpf` | following-hour integral `[T, T+1h)` | correct cell |
| TWC `windSpeed` | instantaneous at `T` | point statistic on a cellular axis |
| TWC `windDirection`, `cloudCover` | hourly mean | **wrong statistic:** declared as point |

The missing declaration is two-dimensional: **which temporal cell** owns the value and **which
statistic** the vendor already computed over it. `CellStatistic` exists on `ParameterDef`, but v1 fixes
every parameter to `point`; no field can declare its cell side. This is distinct from
[#15](#15-coarser-grid-resampling-and-aggregation-semantics), which owns caller-requested coarsening.

Open-Meteo precipitation therefore has a live contract error: values and units are correct, but the
published hour label is one hour late. Internal arithmetic does not yet read `Cell.bounds`, so the
error is additive to repair. Provider parity cannot detect a semantic mistake shared with its
reference reader → [Provider edge: parity limits](./edge/provider.md).

The repair must preserve vendor-native semantics and split records by temporal convention as it
already splits them by Z level. Open: whether the cell-side declaration belongs on the tap,
`ParameterDef`, or the axis.

→ queued as [tick-convention declaration](./tickets/01-0126-tick-convention-declaration.md).

## 49. Spanning asks serve the primary; max-reach is unbuilt policy

**Kind:** product/flow (decided v1 shape; the escape is unbuilt) · **Refs:**
[ADR-0004](./adr/0004-producer-resolution-and-capability.md),
[ADR-0002](./adr/0002-data-model.md), [#29](#29-narrated-reach-what-a-profile-promises),
[#28](#28-reconciler-interface-selection-ordering-vs-per-cell-fold),
[#20](#20-provider-multi-resolution-offerings-offering-aware-selection)

The priority winner serves its own clipped span even when the composed reach extends farther. The
root Reservoir opens T before producer selection, so a reconciler never sees the bounded window and
cannot implement a "serve the window whole" preference. Open: how a profile instead serves the
composed span through a non-primary producer without buying a primary call that cannot satisfy the
ask or narrating a horizon the selected source will not reach.
→ queued as [max-reach-tail-serving](./tickets/02-0180-max-reach-tail-serving.md)

## 5. Read-time homogenization fidelity

**Kind:** edge-isolated · **Refs:** [ADR-0001](./adr/0001-manifold-algebra-and-composition.md), [ADR-0002](./adr/0002-data-model.md)

The retention and read-back mechanism, including selection of the enclosing stored cell, lives in
[ADR-0001 §materialization](./adr/0001-manifold-algebra-and-composition.md),
[ADR-0006](./adr/0006-materialization-granularity-and-store-shape.md), and
[architecture §Reservoir](./architecture.md#reservoir). This concern owns how that cell's value
reaches the answer point beyond the identity Resampler.

**What's open is fidelity:** the **Resampler choice** per field axis — the registry's
implementations (nearest / linear / cubic; **conservative / area-weighted** for extensive
re-aggregation; the non-linear `circular` / categorical rules for scales v1 does not exercise, since
wind rides as linear u/v components) — and the acceptable **accuracy bounds**; ADR-0002 fixes only
*which* axes admit a Resampler and that a storing grid imposes a **fidelity floor**, not the method.
The v1 contract specifies the **identity** Resampler — kind-agnostic because identity is one rule for
every Parameter, and pluggable — which honours `sel.domain` by relabel alone, with no value transfer;
**Parameter-specific** Resamplers (linear intensive incl. u/v wind, area-weighted
extensive, the deferred non-linear scales), accuracy bounds, irregular vendor geometries (sparse
stations, mixed grids), and the **provider "exact" capability** (true off-grid points bypassing the
store-grid floor — realized as another `SourceKey`-identified offering under the instance model,
[ADR-0004](./adr/0004-producer-resolution-and-capability.md)) are the later stress on the Resampler.
Always fetching the finest native product and resampling down is faithful **only** when the Resampler is
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
perform an **aligned identical-step crop** (its uncategorized `NotImplementedError` is one of the
leaks inventoried at [#39](#39-python-embedding-surface-and-public-failures) — *unbuilt* is its own
failure class, not a producer fault) — off-phase or non-identical-step selections that still sit
inside the span are admitted, then fail at `project` with `NotImplementedError` instead of a clean
admission miss (`capability-mismatch` / Arbiter fall-through).

The fixed hourly on-lattice v1 request does not exercise this mismatch. **Close inside `serves`**, not with a second check in
`Arbiter.project`: deepen the Capability predicate with the resampler / alignment branch (extensive
horizon edge at 002). Composites (`Union` / `Derived`) and the Arbiter inherit
correctness unchanged — blast radius stays behind the Capability facet. Until then, engine
`NotImplementedError` is an internal assert that `serves` over-promised, not the normal edge path.

**What remains is off-phase or a different step** — genuinely unimplementable by index arithmetic,
still an internal assert. *A target running past the source's end* is **not** this concern: that is a
**shortfall**, well-defined over the overlap and short by a known count, which callers can diagnose (a
vendor delivered less than it declared) and
[#30](#30-response-membership-under-runtime-degraded-fallback) can eventually pad.

Nothing has narrowed it. The **identity** Resampler gained its own home — the enclosing cell answering
for a point it already contains, with no value transfer — but that adds no Resampler *registry* and
does not touch `serves`. The live-window repair is the same *admitted-by-extent then unserved* family,
a different member: it fixed the retention predicate and the in-gap serving seam rather than deepening
`serves`.

**Trigger to revisit:** the first request genuinely off-phase or on a different step from what a
producer declares — a coarsened store lattice ([#5](#5-read-time-homogenization-fidelity)'s step
question), a caller-facing resolution knob
([#15](#15-coarser-grid-resampling-and-aggregation-semantics)), or a provider whose native step
differs from the store's.

## 22. Lattice helpers vs `domain` / `sampling` module split

**Kind:** room-left (module layout) · **Refs:** [module layout](./module-layout.md)

Lattice index arithmetic and axis/domain geometry share `domain.py`, while `sampling.py` and Store
grids consume the lattice helpers. The split must preserve the one-way dependency from sampling and
storage into geometry.

→ queued as [domain-module-carve](./tickets/01-0131-domain-module-carve.md).

## 23. Spatial vs temporal `RegularAxis` types

**Kind:** room-left (types / hot path) · **Refs:** [ADR-0002](./adr/0002-data-model.md)

`RegularAxis` is one type over `Coordinate = float | datetime` and `Step = float | timedelta`.
`sub_lattice_offset` pays an `isinstance` crawl on every call to branch float tolerance vs exact
`timedelta` math. The lasting fix is **split types** (spatial vs temporal regular axes) so dispatch is
structural, not runtime — not a pair of private helpers that paper over the union.

`RegularAxis.clip` is *not* a driver: `(bound − anchor) / step` is a plain `float` for `timedelta`s and
floats alike, and `anchor + i·step` types alike, so it stays one branch-free expression for both
coordinate kinds. The standing consequence is narrower and worth keeping precise: **snapped X/Y needs a
float phase-tolerance decision inside `clip`** — a bound landing on a tick can floor to the tick before
it — which this split is one way to state statically. `quantize`'s spatial snap delegates there and the
tolerance lives in **index space** (fraction of a step), reconciled with `LATTICE_TOLERANCE` as one
shared policy and pinned by a boundary-point test. The T path never meets it: `timedelta` arithmetic is
exact.

**Constraint on the split itself:** it would double every request-facing axis kind (`SelectableAxis`:
regular / vantage / snapped), so when it lands it must stay **invisible to request authors** — one
constructor name per kind with coordinate-kind autodetection, or facade builders absorbing it
([#39](#39-python-embedding-surface-and-public-failures) owns the embedder-visible shape).

**Trigger:** a **bounded spatial snapped member**, which is a type error today. The snapped member's
temporal narrowing bites only on *bounds*, the boundless (`ANY`) form is axis-generic, and `quantize`
authors pinned cells plus boundless members — so nothing yet needs the union stated statically.

## 42. Two request representations, so resolution cannot be a method

**Kind:** room-left (request vocabulary) · **Refs:**
[ADR-0002 §Domain & Selection](./adr/0002-data-model.md#domain--selection),
[Edge — Provider](./edge/provider.md),
[#39](#39-python-embedding-surface-and-public-failures)

The request side of every seam admits **two representations**: an `EnumerableDomain` (the author already
knows the coordinates) and a `SelectionDomain` (at least one member gives bounds only). Both are legal,
so `ground` dispatches on representation in the module that owns them. Its enumerable arm returns the
request unchanged; a declared footprint is only something to ground against.

**The end-state this leaves room for: one request representation.** A `SelectionDomain` whose members may
each be exact or snapped already subsumes the enumerable case — an all-pinned one grounds to itself, by
identity. If every request author built one, `Selection.domain` would narrow from base `Domain`,
resolution would be `SelectionDomain.ground(against)`, and both the dispatch and the malformed-call arm
would become unrepresentable rather than tested. That is the same *make it unrepresentable* move
[#40](#40-composing-servable-requests-at-the-embedding-edge) makes for mismatch, one level down.

**What it costs, and why not yet:**

- **`SelectableAxis` is narrower than the enumerable axis kinds.** It admits `RegularAxis | VantageAxis |
  SnappedAxis`; an exact request over an `IntervalAxis` (or [#12](#12-curvilinear-domains)'s irregular
  points) has no `SelectionDomain` form. Narrowing the request type means widening this union — and the
  union is what makes a request's members statically knowable in the first place.
- **A crop target is coordinates, not bounds.** `resample` takes a `Selection` whose domain must be
  enumerable. One request representation means either it stops taking a `Selection`, or the grounded
  result is re-wrapped into one on every crop.
- **Request authors and crop targets would have to move together.** Store keys remain stated in
  enumerable terms even when refill requests contain boundless members.

This is about the *request* side only; `Coverage.domain` stays enumerable regardless
([ADR-0007](./adr/0007-capability-carries-its-domain.md)).

**Trigger:** [#39](#39-python-embedding-surface-and-public-failures)'s request-composition helper,
which must choose what type embedders receive. Both in-tree request authors use `SelectionDomain`;
the remaining `EnumerableDomain` request role is the internal crop target. Until the public surface
forces the choice, the cost is one representation dispatch in `domain.py`.

## 43. Narrow-answering providers re-open mixed-request run divergence

**Kind:** provider economy seam (no v1 driver — Open-Meteo answers wide) ·
**Refs:** [ADR-0001](./adr/0001-manifold-algebra-and-composition.md),
[ADR-0003](./adr/0003-provenance-and-origin.md),
[ADR-0006](./adr/0006-materialization-granularity-and-store-shape.md),
[Edge — Provider](./edge/provider.md)

Refill scope is **ask narrow, answer natural**: the `Reservoir`
asks for the missing/stale *requested* parameters; the answer is licensed to carry the provider's
**natural fetch unit** — wider on the parameter facet, never narrower — and the store absorbs it.
Open-Meteo's natural unit is its whole offering (one variable-listed call either way), which is what
dissolves the cold mixed-request double fetch: the first fetch warms `wind_u`/`wind_v`, so the
Calculator's second `Selection` hits the store. That makes the dissolution a **per-provider
property**: a per-variable-billed provider whose natural unit
is exactly-what-was-asked re-accepts the two-fetch run-divergence exposure *for its own parameters*.
The failure that exposure ends in stays guarded at the fold, where the invariant lives —
`test_winner_domains_that_differ_fail_the_whole_request` (`test_arbiter.py`), two canned winners on
disagreeing lattices, no network and no store.

Graded responses, cheapest first — decide at the first narrow-answering billed provider:

1. **Accept per-provider** — the divergence is recorded as that provider's economy choice.
2. **Detect and narrate** — assembly compares `AtomicOrigin.issue_time` across the assembled
   parameters (the data already exists in the `PerParameter` provenance plane) and narrates a
   mixed-run response. Cheap, and honest narration is the product's register.
3. **Closure-widened ask** — at fan-out, widen a source's direct-parameter `Selection` by the
   calculator inputs that source serves. Static from `RegisteredCalculator.inputs` (no prediction,
   no runtime carrier). Independent value beyond divergence: one call instead of two for a
   per-*call*-billed vendor, and one round trip instead of two sequential ones.

**Rejected:** carrying request context / breadcrumbs on `Selection` or `Coverage`. `Coverage`
already carries the detection half (`issue_time`); a `Selection`-side carrier would duplicate at
runtime what the registries know statically, and `Selection` staying pure "what is asked" is
load-bearing for composability.

## 15. Coarser-grid resampling and aggregation semantics

**Kind:** edge-isolated (data-model + surface) · **Refs:** [ADR-0002](./adr/0002-data-model.md), [#5](#5-read-time-homogenization-fidelity)

The temporal-axis counterpart to [#5](#5-read-time-homogenization-fidelity)'s spatial fidelity, and as
central. Coarsening the `valid_time` grid below the native/store cadence is **not one operation**, and
the choice is **product semantics, not Resampler accuracy** ([#5](#5-read-time-homogenization-fidelity) owns
the latter). Three regimes:

- **Extensive** (precipitation): the coarse cell is the **integral** (sum over the interval) — the
  conservative re-aggregation Resampler of [#5](#5-read-time-homogenization-fidelity).
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
**cannot occur**. **v1 relies on containment for enumerable requests** — wholesale fallback, "select,
never combine", no horizon splicing. The scoped, mode-local rule is that a **Snapped-T** request admits by
non-empty T intersection and the single winner serves `bounds ∩ its window` — no per-cell fold, no
splicing, reconciler untouched ([ADR-0004](./adr/0004-producer-resolution-and-capability.md) carries the
mode-dependent admission language). The general question stays open: when coverage reconcilers
([#6](#6-reconciler-catalogue)) land, admission must generalize to **intersection** with per-cell folding,
at which point the rules must be reconciled (likely: containment is the *degenerate* case of
intersection). Additive.

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
counts, fallback rate, cache hit-rate, provider latency / error). Also this concern's: **which cell sourced a value** — the enclosing store cell that answered, and the
step it sat on — i.e. *how far the value travelled to reach the requested point*. That is resolution
story, **not provenance**: [ADR-0003](./adr/0003-provenance-and-origin.md) already declined native
fidelity as a provenance field, leaving it recoverable server-side from the `SourceKey`. (Echoing the
*answered* coordinate is a different and smaller thing — a per-surface serialization gap, tracked on
the [MCP edge record](./edge/mcp.md#roadmap).) Keeping the trace a sidecar channel leaves
the read-only algebra untouched. Phase 1's **minimal structured log** is assigned to
[minimal resolution logging](./tickets/02-0195-minimal-resolution-logging.md); the ticket's own align
selects that narrow event surface. The structured sidecar and wider metrics remain deferred here.

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

→ [ADR-0003: cadence](./adr/0003-provenance-and-origin.md#run-identity-fetch-buckets-and-freshness--the-cadence).
Open: timing facts for providers without probe evidence; residual estimate error in Open-Meteo's run
cadence; and its vendor-served ~92-day archive edge, which remains undeclared pending product decisions
about history, provenance, payload, and parity evidence.

The run/bucket distinction is settled in
[ADR-0003 § Run and bucket regimes](./adr/0003-provenance-and-origin.md#run-and-bucket-regimes).
What remains open is the bucket regime's cost: anchored expiry gives an effective TTL from nearly zero
to Δ, averaging Δ/2, so steady traffic can make roughly twice as many vendor calls as the configured
polling interval suggests. It also makes the MCP `exp` bound vary across the bucket. Provider-real
reference and availability signals are the intended escape → [ideas: freshness](./ideas.md#freshness).

**A first real escape signal is now in hand, and deliberately unused (2026-08-11).** TWC's payload
carries a per-tick `expirationTimeUtc` — observed ~5 min out for the near-term head, ~21 min for the
tail. It is not adopted, because `expiration` currently serves **two** roles from one field: the
caller's staleness bound ([mcp_app.py:250](../src/meteoscape/api/mcp_app.py)) and the Reservoir's
serve-vs-refetch trigger ([reservoir.py:126](../src/meteoscape/nodes/reservoir.py)). Adopting a
5-minute vendor expiry would set the polling interval to 5 minutes and spend the allotment the
configured Δ exists to conserve. **Splitting those two roles is the real prerequisite** for any
provider-real freshness signal — the escape is not a per-provider declaration but that split. Wanted
by the faster-nowcast case, not by v1 → [TWC provider](./tickets/done/01-0120-twc-provider.md).

→ queued for measurement by the [vendor-call ledger](./tickets/01-0130-vendor-call-ledger.md).

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

**Related limitation:** a leaf cannot serve, in one call, two
parameters whose declared reaches **differ on a *bounded* snapped axis** — `agreed_geometry` refuses it,
because one `project` answers with one geometry on every bounded axis (ADR-0001). A vendor offering 16
days of temperature but 5 of precipitation therefore declines a mixed snapped request with
`capability-mismatch`. **This does not dissolve.** The licence for a multi-domain answer is
**boundlessness**, not the store: an ask that leaves the axis open licenses the difference,
while an ask that *states* bounds is still answered identically on them or not at all. So what 006
supplies is a second kind of ask, not a repair of this one — and this stays the per-parameter cousin of
this concern's per-offering question → [edge/provider.md](./edge/provider.md).

**The leaf side is unbuilt too.** A second offering is not only an algebra
question: the v1 leaf is **not offering-parameterized**. Three per-offering facts sit as module
constants in [open_meteo.py](../src/meteoscape/nodes/providers/open_meteo.py) — the tap table, the
`CadenceDef`, and the series step — and `build` forwards only `spec.name`, which reaches `SourceKey`
and nothing else. Three consequences, the first silent and therefore the sharpest:

- **The query carries no vendor model token**, so two offerings of one impl would fetch **identical
  payloads** under distinct `SourceKey`s — distinct atomic origins, separate store rows, and a
  priority band the Arbiter walks between duplicates, with no error anywhere. ADR-0004's own
  illustration (`best_match ≻ gfs_seamless`) is therefore not buildable today.
- **Footprints are built from the module tap table, not `spec.parameters`** — and the binder never
  reads `spec.parameters` either, since the runtime authority is `provider.capability.parameters`. An
  offering row and the capability it produces can disagree with nothing to catch it.
- **Cadence and step are authored for the first offering**, so a second inherits a reach declaration
  that is not its own — an over-promise of [#18](#18-clock-anchored-footprint-fidelity)'s kind, but
  self-inflicted rather than a vendor-fidelity estimate.

So the additive boundary is narrower than the config surface suggests: richer `dataset` values and
more `OfferingDef`s are additive, while the leaf gains a model token in its query and turns its
declarations into per-offering rows keyed by `spec.name`. Those declarations are constructor
arguments, which is where the rows attach → [edge/provider.md](./edge/provider.md).

**Open (additive build; v1 unaffected — one offering per provider, `contains`-only):** populate
continuous footprint **`step`s**, implement **`Domain.match`** / **`Capability.score`**, and the Arbiter
  equal-priority band walk. **Multi-level samples inside one vantage window**
(wind at 10 m + 80 m under `[0,100]`) are **not** offering selection — the resampler folds them to one
representative value (→ [ADR-0004](./adr/0004-producer-resolution-and-capability.md)); `match`/`score`
applies to *offerings* (distinct `SourceKey`s), not to levels within one product.

## 25. Root-store Holding reuse across vantage windows

**Kind:** deferred seam · **Refs:** [ADR-0006](./adr/0006-materialization-granularity-and-store-shape.md), [ADR-0002](./adr/0002-data-model.md)

The best-view store holds **product** Holdings keyed by the *request's* Z cell (the vantage window) —
answers, not native facts ([ADR-0006](./adr/0006-materialization-granularity-and-store-shape.md)).
v1 has exactly one edge-authored default window, so the key is stable and reuse is exact-match. When
custom vantage windows arrive, reuse needs a rule: a layer-unresolved value labeled `[0,10]` is an
**∃-claim** ("measured somewhere in the layer"), so admitting it for a narrower `[0,5]` request by
plain inclusion is suspect — unlike a ∀-claim statistic cell. Options when it bites: exact-key only
(cache misses fall through to the Sources, which re-match native Holdings honestly — correct, just
colder), or a declared tolerance policy at the edge. No v1 work; the fall-through path is already
correct.

## 44. Dedicated live archive Store for throughput

**Kind:** deferred seam · **Refs:**
[ADR-0006](./adr/0006-materialization-granularity-and-store-shape.md),
[#9](#9-cross-run-combination),
[Mongo forecast-run archive source](./tickets/01-0134-forecast-run-archive-source.md),
[persisting Store](./tickets/01-0145-persisting-store.md)

Release 02 deliberately gives meteoscape **no owned persistence** *of history*: the archive is the
operator's collector MongoDB, and meteoscape projects over it read-only ("the framework doesn't own
persistence, it projects over whatever does"). At some later point throughput will want a
**dedicated live archive Store** — meteoscape-owned, write-path, retention-managed — as a second
persistent Store shape beside the in-memory retentive Store. Nothing is designed; when it opens,
the categorical `issue_time` key (#9) and ADR-0006's Holding granularity are the constraints it
inherits. Trigger: measured read pressure on the collector DB, or an embedder that needs archive
writes meteoscape-side. A meteoscape-side collector role is deliberately **late release 02 or
after** — release 02's archive reads are served by the operator's collector,
so nothing earlier needs this. One contract fact is already settled ahead of it: the `Store`
contract is **clockless and freshness-blind** (freshness is the reader's policy), so an archive
store — whose Holdings are valuable *because* they are stale — implements the same face with no
carve-outs.

**A persisting retention cache is not this concern.** The distinction is derivability:

| | Retention cache | Archive |
|---|---|---|
| State | **derivable** — every Holding re-fetchable from the vendor | **source of truth** — once the run window passes, unreconstructable |
| Losing it costs | money and latency | information |
| Read shape | point lookups | bulk / analytical scans |
| Owner | [persisting Store](./tickets/01-0145-persisting-store.md) (rung 2, ticketed) | this concern (rung 3) |

Persisting the cache is a substrate choice already permitted by ADR-0006 and claims nobody's data;
this concern owns only the archive rung. Bulk analytical reads are a different access shape from
point cache hits, so an archive is not merely a larger retention cache.

## 45. The collector schema is a contract meteoscape depends on but does not own

**Kind:** external-contract risk · **Refs:**
[Mongo obs source](./tickets/01-0124-mongo-obs-source.md),
[Mongo forecast-run archive source](./tickets/01-0134-forecast-run-archive-source.md) ·
**→ queued as [mongo-obs-source](./tickets/01-0124-mongo-obs-source.md)**

The collector (external repo) writes parsed documents in its own schema — common camelCase forecast
fields sparse per provider, two observation document shapes, a station registry, and a source-level
freshness document. The Mongo sources map that external schema to canonical parameters, so a
collector-side schema change can silently break them. The queued source owns pinned integration
fixtures and explicit adapter ownership.

Two external signals remain unavailable: a schema version and a **per-station** latest-observation
time. Source-level freshness cannot declare the true end of each station's data
([#29](#29-narrated-reach-what-a-profile-promises), backward reach). The station network's obs `raw` payload
preserves replayability; forecast documents carry no raw, so forecast decode fidelity is bounded by
the collector's own parsing. The station network's *endpoint* is out of meteoscape's scope
permanently: if meteoscape ever takes over the collector's server edge, that integration arrives as
an **embedder-owned plug-in provider** through the plugin seam
([#26](#26-provider--calculator-plugin-scaffolding)), never an in-tree provider.

## 50. Observation-network scale: station grouping and discovery

**Kind:** deferred seam (scale; driver approaching — the collector's few dozen stations can grow to
tens of thousands) · **Refs:** [#29](#29-narrated-reach-what-a-profile-promises),
[#45](#45-the-collector-schema-is-a-contract-meteoscape-depends-on-but-does-not-own),
[ADR-0005](./adr/0005-build-time-composition.md)

An observation impl over an unbounded station network cannot be one provider hosting the world:
the registry read, its periodic refresh, the declared site set, and envelope narration all scale
with station count. The seam is the **offering boundary that already exists**
([ADR-0005](./adr/0005-build-time-composition.md)): one declared offering hosts one bounded station
group, and a deployment scales by declaring more offerings — per network, per region — never by one
provider growing unbounded. A station-*filter* offering setting is added when the second group
appears, not before. Discovery past description-string scale is
[#29](#29-narrated-reach-what-a-profile-promises)'s capabilities-introspection trigger, not more
narration. Open here: what selects a group (network id, region, explicit list), and whether
grouped offerings of one impl share a client and registry read.

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
  Its first concrete instance is the **multi-station ask**: a `ScatterDomain` as the *request* —
  already legal by construction, since `Selection.domain` stays base-typed
  ([ADR-0002](./adr/0002-data-model.md)) — which arrives as one bundle with a scatter-shaped
  `Coverage` (the positional-order contract), scatter `EnumerableDomain` conformance, sampler
  widening past the `GridDomain` gate, and multi-point provider assembly. `ANY` on X/Y then reads
  "all stations", the same everything-held reading it already carries; a vantage X/Y aperture would
  read "stations within radius", which no customer wants. A scatter reach declines all of these
  today. **Trigger:** the first consumer wanting all-stations-as-one-answer — a station-map sweep,
  or this concern's own obs-space verification.

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

## 41. Parity evidence is unenforced and unrouted

**Kind:** room-left (evidence routing) · **Refs:** [edge/provider.md](./edge/provider.md), [cicd.md](./cicd.md)

Every live Provider parity check is opt-in and hand-invoked. Three links between a Provider and its
evidence have no mechanism, only prose:

- **Coverage is unchecked.** Nothing verifies that an `impl_id` in `PROVIDER_CATALOG` has a
  `tests/parity/test_<impl>.py`. A Provider can ship complete by every automated measure — deterministic
  suite green, `pyright` green, CI green — with no live check at all. Contrast
  `test_parity_reader_guard.py`, which *does* mechanically guard every module in `readers/`: the
  pattern already exists one level down.
- **Selection is manual.** *When* to run a check is a prose list (that Provider, its reader, its
  manifest, shared normalization it uses, a Calculator in the comparison, composition or surface code),
  applied by whoever remembers. m3 states the constraint without a mechanism — *"branch naming must not
  become the only way an affected Provider is selected"* — so routing is open, not merely unbuilt.
- **The retry-once boundary policy has no failure signal.** m3 defers improving it (run pinning,
  reference metadata) *"until the simple policy demonstrably fails"*, but nothing accumulates the
  evidence that would demonstrate it. Parity evidence is retained only at failure time and the vendor
  forecast rolls over within hours, so a false-alert rate is unobservable by design.

Open: whether coverage becomes a deterministic guard (cheap, and the reader guard is the pattern) or
rides the automation; what selects an affected Provider without depending on branch names; and whether
the boundary policy needs a *signal* before it needs an improvement.

**Not this concern:** building scheduled execution and changed-file routing. This entry owns only
what enforces Provider coverage and what signal routes test selection.

## 26. Provider / calculator plugin scaffolding

**Kind:** room-left (composition) · **Refs:** [ADR-0005](./adr/0005-build-time-composition.md),
[architecture §Config, binders, Weaver](./architecture.md#config-binders-weaver)

The shipped provider and calculator sets live plugin-side in parallel `builtin.py` modules;
`server.py` declares only enablement. Open: whether optional plugins are second catalogues,
entry-point discovery, or install extras; how `compose` selects among multiple named sets
symmetrically; enablement in `ProfileConfig` stays separate from availability. Decide before the second
optional calculator or a non-default provider packaging story forces an ad-hoc split.

→ [ADR-0005: plugin binding](./adr/0005-build-time-composition.md#plugin-binding).

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
a silent root-store inheritance.

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
ParameterData`), not another `select` implementation. Claims in the design language that depend on that
widening and are **not true of the current build**: (1) the per-cell fold itself; (2) the
**gap-filler** story (a low-priority whole-coverage producer filling where a hi-res one does not reach —
the hi-res producer simply wins the whole parameter under the implemented interface); (3) **per-parameter
partial success**. Wholesale runtime-fault fall-through does not depend on this widening: it
re-enters selection and projects the next admitted candidate whole within the narrow interface.

Not a v1 gap: v1 ships only `priority`, and point/timeline producers fully overlap, so selection *is*
the whole job and the narrow interface is exactly sufficient. This concern records the **cost of the
extension** so it is not mistaken for a config change: it lands with the catalogue
([#6](#6-reconciler-catalogue)), presses toward `PerPoint` provenance
([ADR-0003](./adr/0003-provenance-and-origin.md)), and wants the first real partial-coverage producer
set to prove it.

Window-aware ordering cannot make `select` prefer a candidate that serves the snapped window whole:
the retention flow opens T before selection, so the reconciler never sees the window →
[#49](#49-spanning-asks-serve-the-primary-max-reach-is-unbuilt-policy).

## 29. Narrated reach: what a profile promises

**Kind:** surface/product seam · **Refs:** [ADR-0007](./adr/0007-capability-carries-its-domain.md) (the mechanism), [#30](#30-response-membership-under-runtime-degraded-fallback), [#28](#28-reconciler-interface-selection-ordering-vs-per-cell-fold)

A surface needs to tell callers **how far this profile reaches** — the MCP tool
description narrates it; window *fitting* is resolution's, via the Snapped-T request mode
([ADR-0002: Domain & Selection](./adr/0002-data-model.md#domain--selection); membership notes →
[#30](#30-response-membership-under-runtime-degraded-fallback)). The mechanism is **Reach**: the per-parameter `Domain` a `Capability` publishes, composed up the
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

**Shelf-anchored reach adds a static-proof obligation.** Open-Meteo's whole-day floor is conservative,
but that is not a law of the Shelf: a shorter window late in its shelf can leave
less time ahead of the latest run than its extent suggests. Before another shelf-anchored offering
contributes to this surface, either its declaration must prove the narrated floor is below the minimum
`window.upper - run_anchor`, or the horizon derivation/sentence must change. This stays surface policy,
not a generic `CadenceDef` constraint.

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

**The dominant and the priority winner need not be the same source**, and that is where the promise
strains: narration follows the dominant, while a *spanning* default ask goes to the priority winner,
which serves its own clipped shape disclosed through `valid_time`. The narrated reach therefore
over-promises the tail whenever primary ≠ dominant — the decided serving shape and the unbuilt
max-reach escape are
[#49](#49-spanning-asks-serve-the-primary-max-reach-is-unbuilt-policy)'s.

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
  without a contract change. A past-facing declaration is an **estimate** the same way a forward one
  is — a clock-riding bound admitted from a snapshot, with truth at serve. Open here: when
  admission must tighten, the accurate feed is a **writer-declared span** published by whoever
  writes the data (→ [#45](#45-the-collector-schema-is-a-contract-meteoscape-depends-on-but-does-not-own)
  for the first such contract, today incomplete), never per-reader scanning.
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

**Where padding would be written.**
Leaf assembly crops values through `resample`, and the sampler distinguishes a **shortfall** — the
requested geometry running past what was delivered — from a crop it cannot do at all
([#21](#21-serves-extent-vs-project-crop-ability)). That shortfall branch is the one site where a
padded tail would be filled: `present=False` with `nan` values, over a known count. It is the
mechanical half only; the ambiguity above (a padded tail indistinguishable from measured absence) is
still what gates turning it on, and the reason channel is still the prerequisite.

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

**Declared-edge trim.** A stated request window yields its servable part in one round trip; the
mechanism is [Edge — MCP: Contract](./edge/mcp.md#contract)'s, which owns it. An **edge-side clamp**
is rejected — simulating resolution at the edge reintroduces clock races and per-input ordering
rules. Membership at the **declared** edge is therefore *trim by the winner*, while this concern's
runtime-degraded case is unchanged: a fault after admission still drops the parameter whole with a
reason. Mixed direct and derived requests can still resolve against diverging winner domains; the
producer-economy cause and mitigation options live at
→ [#43: narrow-answering providers](#43-narrow-answering-providers-re-open-mixed-request-run-divergence).

**Three policies stay distinct:** **fallback** (who serves — the reconciler's),
**membership** (what a beyond-boundary request gets — declared edge: trim, above; runtime edge: this
concern), **narration** (what the client is
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
  *independently replaceable* per-Parameter Holdings, so reassembly joins separately-persisted pieces —
  a partially-written or stale Holding is the first payload that can be the wrong length without a bug
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

A **footprint-aware `reconciler`** would rank
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

**The concrete motivating deployment** — regional models expose complex fields (gusts, CAPE, echo top)
that a global model only reaches by derivation:

| Producer | Serves | Footprint |
|---|---|---|
| ICON-D2 | basics **+ `wind_gust` directly** | Europe × 48 h |
| HRRR | basics **+ `wind_gust` directly** | Americas × 36 h |
| GFS | basics only | World × 180 h |
| gust Calculator | `wind_gust` from basics | World × 180 h (contained-in-all over GFS inputs) |

Composition is correct and uneventful: the Calculator dominates, so reach is World × 180 h — the
profile really does serve `wind_gust` everywhere. **What it cannot express is that the answer is
better inside Europe.** The wanted behaviour is per-request: prefer ICON-D2 within its footprint,
HRRR within its own, the Calculator elsewhere — which is this concern's ranking policy over the
now-published geometry, needing the wider interface of
[#28](#28-reconciler-interface-selection-ordering-vs-per-cell-fold). Wholesale `priority` picks one
producer for the whole world and wastes the regionals. Quality varying across a single published
reach is [#7](#7-quality-scoring) / [#29](#29-narrated-reach-what-a-profile-promises).

**Trigger to revisit:** a profile that needs per-request producer *ranking* rather than the wholesale
`priority` fallback — the deployment above is the first one that does. Nothing about the geometry
blocks it now; the reconciler interface does
([#28](#28-reconciler-interface-selection-ordering-vs-per-cell-fold)).

## 33. Reconciler owns domain composition

**Kind:** policy coherence (contract-level) · **Refs:** [ADR-0007](./adr/0007-capability-carries-its-domain.md), [#29](#29-narrated-reach-what-a-profile-promises), [#28](#28-reconciler-interface-selection-ordering-vs-per-cell-fold), [#6](#6-reconciler-catalogue), [#32](#32-footprint-aware-ranking-inside-the-algebra)

Domain composition is a `Reconciler` member, so it moves with the policy and cannot be paired
incoherently ([ADR-0007](./adr/0007-capability-carries-its-domain.md)). Its interface remains open:
`priority` composes by dominance-or-raise; `tile` would
compose a spatial union, `splice` a temporal one. Whether one signature serves all three is unknown
until a second reconciler is built — the same uncertainty
[#28](#28-reconciler-interface-selection-ordering-vs-per-cell-fold) records about `select`, and the
reason a reshape is expected rather than feared.

## 34. Producer-DAG walking is duplicated

**Kind:** room-left (build-time structure) · **Refs:** [ADR-0005](./adr/0005-build-time-composition.md), [ADR-0007](./adr/0007-capability-carries-its-domain.md)

Two build-time passes walk the same producer DAG over `ProfileDef`:

- **`Weaver._weave_calculators`** — memoizes a `Producer` per `CalculatorKey`, with a `visiting` set
  raising `CompositionError("calculator cycle at ...")`. A **backstop**: `validate_calculators` is
  `weave`'s first step and is required to reject every cycle the Weaver cannot build, so this should
  never fire. The two messages differ deliberately — the operator's names the whole cycle — so if it
  ever does fire, which guard caught it is observable.
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

**Kind:** composition policy · **Refs:** [ADR-0007](./adr/0007-capability-carries-its-domain.md), [architecture § Config, binders, Weaver](./architecture.md#config-binders-weaver) (key-absent refuses; no boot-degrade exists)

A Calculator whose input **no producer serves** is a build-time
`CompositionError` naming the calculator + input: declaring a Calculator is an operator **promise**, so
an unwired input must fail loudly at build, not surface as an accidental runtime `capability-mismatch`.
This is strict and correct for v1, where every Calculator input (`wind_u` / `wind_v`) comes from
declared producers and there is no boot-degrade: a keyed offering with an unfilled slot refuses
startup, so the strict check has no optional-provider customer today.

**The collision is a future question.** If a Calculator input were served *only* by an **optional**
provider (one that degrades away on a missing secret — a story that waits on
[#26](#26-provider--calculator-plugin-scaffolding)), the strict rule would fail the build where
optional-plugin degrade intends the server to start without that capability. Two resolutions, undecided:
(a) **fail the build** — force the operator to drop the Calculator or keep the provider; matches
"Calculator = promise". (b) **drop the unsatisfiable Calculator** like a degraded provider and narrate
the reduced set; matches "optional provider = availability". No v1 driver.

**Related, broader:** an operator wants to assert a composition *serves what they expect* — an opt-in
"validate my profile serves {…}" mode, not a hard rule. A product-side want, not v1 → [ideas](./ideas.md).

## 37. Storeless materialized producers and read-back homogenization

**Kind:** deferred seam (placement) · **Refs:** [ADR-0006](./adr/0006-materialization-granularity-and-store-shape.md), [#5](#5-read-time-homogenization-fidelity)

Any producer may wire storeless when retention or call economy adds no value; a materialized
provider must wire storeless so the graph does not mirror data that is already local. Without a
Reservoir, no read-back step homogenizes an off-grid request, while the algebra still requires every
producer's answer to honour `sel.domain`.

Open: whether a storeless producer invokes the shared sampling engine itself or the Weaver applies a
thin non-retentive read-back wrapper; which kernel licenses that sampling; and whether
`EnumerableCapability` remains the right materialization discriminator for enumerable but
unholdable sources. A storeless producer's fidelity floor is its native lattice, while Store presence
remains profile policy → [ADR-0005](./adr/0005-build-time-composition.md),
[architecture §Reservoir](./architecture.md#reservoir).

**Trigger:** the first real storeless producer that must answer off its native lattice.

## 38. Calculator admittance is fixed pointwise-total

**Kind:** deferred seam (per-calculator policy) · **Refs:** [ADR-0007](./adr/0007-capability-carries-its-domain.md), [#12](#12-curvilinear-domains), [#33](#33-reconciler-owns-domain-composition)

`DerivedCapability` hardcodes one admittance for every Calculator: **pointwise-total** — `serves` is
AND-over-inputs and `reach` is contained-in-all. That is correct for v1's kernels (wind from u/v needs
both inputs at every point) but it is a *policy of the kernel*, not a law of derivation: a blend that
degrades gracefully with partial inputs would want OR-serves and a union-shaped reach; a persistence
extrapolator reaches *wider* than its inputs on T.

**The seam is per-calculator, not per-profile.** The Weaver hands one `Reconciler` to every Arbiter, so
reconciler policy is profile-wide — the wrong granularity for a fact that varies with the kernel. When a
non-pointwise calculator arrives, its admittance belongs on the `CalculatorManifest` (the catalogue
knows its kernel's semantics), flowing into the capability form — not on the `Reconciler`, whose
`compose_domains` reconciles competitors for one parameter, while admittance combines *across*
parameters. Note both members encode the same assumption, so they must change together — a second
capability form or a manifest-declared mode, not a flag threaded into one member.

**Trigger to revisit:** the first calculator whose kernel is not pointwise-total (partial-input blend,
temporal extrapolator, subregion-valid downscaler). No v1 driver.

## 46. Composition-failure attribution is paid inside geometry

**Kind:** deferred cleanup (layering) · **Refs:** [ADR-0007](./adr/0007-capability-carries-its-domain.md),
[#12](#12-curvilinear-domains), [#36](#36-unserved-and-uncomparable-are-indistinguishable)

[ADR-0007](./adr/0007-capability-carries-its-domain.md) requires a build-time `CompositionError` to
identify conflicting producers and axes. The current implementation satisfies that operator-facing
contract by pushing identity and prose into geometry helpers:

- `split_extents(left_key: object, …, z_allowance=None) -> str` and
  `first_incomparable(Sequence[tuple[object, Separable]], z_allowance=None)` accept opaque keys and
  render prose inside `manifold/domain.py`, including the allowance sentence
  (`z level … outside allowance […]`, [parameters.md](./parameters.md#sample-level-allowance)). They also compute the
  incomparable pair twice: once to find it and again to describe its axes.
- The shared `require_separable` (`nodes/composition.py`) authors one sentence skeleton with
  caller-supplied identities; parallel `_names` one-liners remain in `nodes/arbiter.py` and
  `nodes/calculator.py`.
- `UnionCapability.members` retains `ProducerKey`s that nothing reads. Both composition folds author
  any failure before constructing their capability, so neither carrier needs identity.

**Why this waits.** The X/Y shear path is still unreachable (current providers are global; the
expected regional/global nesting is described in
[ADR-0007](./adr/0007-capability-carries-its-domain.md#why-per-axis-folding-is-invalid)), and the
separability guard waits on a curvilinear domain ([#12](#12-curvilinear-domains)). The
**sample-level refusal is reachable** — an out-of-band level renders the band sentence
([parameters.md](./parameters.md#sample-level-allowance)) from inside geometry, with tests pinning the
prose — which grows this concern's surface without deciding the diagnostic's shape; the real regional
configuration should still decide it.

**Candidate resolutions** — both replace `UnionCapability.members` with an unkeyed collection:

- **Return a keyless fact.** The geometry fold reports candidate positions and per-axis dominance;
  one shared caller-side renderer adds producer or calculator labels. This preserves the current
  pairwise diagnostic while computing it once.
- **Subtract the pairwise witness.** Drop "which pair, which axis": report that no candidate dominates
  and list every candidate's per-axis extents. This deletes both helpers and avoids a new fact type,
  but weakens the diagnostic when many candidates compete and requires amending ADR-0007.

Until then, ADR-0007's keyed-member statement describes the current structure; its attribution
rationale is the part this concern leaves open. Code and ADR must change together when it resolves.

**Not a resolution:** merging `UnionCapability` into the per-parameter form. Its `serves` delegates to
members (`any(m.serves(…))`) rather than reading its own composed reach, which is what keeps the
resampler-reachability and probed-availability seams open; ADR-0007 lists deriving `serves` from
`reach` as a rejected alternative. The two forms are geometrically equivalent only while `serves` is
pure geometry everywhere.

**Trigger to revisit:** the first configuration that can actually fail composition — a regional
provider whose footprint shears against a global's, or the first curvilinear domain. Decide the
message shape then, against the real case.
