# 003a — Profile reach

- **Status:** Ready
- **Depends on:** [002 — Core canonical parameters](./done/002-core-5-parameters.md),
  [002b — Derived wind](./done/002b-derived-wind-calculator.md)
- **Outcome:** A **build-time resolver** that reports the per-parameter `Domain` a profile reaches —
  the fact every surface needs to narrate an envelope or author a default window.

## Parent PRD

`docs/v1-requirements.md`

## What to build

Build-time only — **no surface change and no request-path change**.
[003b](./003b-request-shaping.md) is the consumer. Two methods in a new **`nodes/reach.py`**:

```
validate_calculators(ProfileDef) -> None                     # is it wired?  (raises)
resolve_reach(ProfileDef)        -> Mapping[ParameterId, Domain]   # how far?  (assumes validated)
```

Reach is an **inner bound**: *every point it names is servable*
([ADR-0007](../adr/0007-reach-is-an-inner-bound.md)).

**Reach is profile-level, not a `Capability` facet, and selected rather than folded** — the semantics
(inner bound, the `grid` rule's two site procedures, tie resolution, never-synthesize, liveness) are
**owned entire by [ADR-0007](../adr/0007-reach-is-an-inner-bound.md)**; this ticket builds them, and
the acceptance criteria below encode them as tests.

The **one contract change**: **`Provider` publishes the per-parameter footprint it already declares**,
so the resolver can read it. Nothing is added to `Capability`.

**The graph is one shape all the way down, so the resolution is one mutual recursion.** A Calculator's
inputs are resolved by a **scoped `Arbiter`** ([weaver.py](../../src/meteoscape/nodes/weaver.py)), so
the same two sites repeat at every depth:

```
reach(arbiter, p)    = dominating([ footprint(prod, p) for prod in producers serving p ])   # X/Y first
footprint(source, p) = the provider's declared footprint for p
footprint(calc, p)   = dominated( [ reach(calc.scoped_arbiter, i) for i in calc.inputs ] )  # whole-box
```

Memoized per key. `validate_calculators` owns the `visiting` **cycle guard** and the *wiring* errors
(an input no producer serves — a calculator is an operator promise, so this fails the build explicitly,
never silently at runtime); `resolve_reach` runs after it and handles only *geometry*. Both walk this
DAG — a third walker beside the Weaver, deliberate ~3-line duplication
([#34](../concerns.md#34-producer-dag-walking-is-duplicated)); the strict-calculator vs
graceful-provider tension is [#35](../concerns.md#35-calculator-satisfiability-vs-optional-provider-degrade).

Build notes, each grounded in [ADR-0007](../adr/0007-reach-is-an-inner-bound.md):

- **No new geometry primitive** — see [Geometry: none added](#geometry-none-added).
- **No `ArbiterPolicy` / `build_reconciler` dependency** — `grid` ignores priority
  (→ [#33](../concerns.md#33-reach-rule-and-reconciler-mode-are-coupled) for why that is mode-scoped).
- **`CompositionError` on unresolved dominance**, naming the conflicting producers (by `SourceKey` /
  `CalculatorKey`) and the failing axis — possible because the resolver works over `ProfileDef`.
- **`grid` is a named unit called directly** — no `ReachRule` protocol, no config plumbing, no
  registry ([#28](../concerns.md#28-reconciler-interface-selection-ordering-vs-per-cell-fold)'s
  recorded lesson; the second rule is already known to need a wider interface).

**Wiring is 003b's.** This ticket delivers `resolve_reach` and the `Provider.footprints` accessor;
calling it from `compose()` and handing the map to the surface is [003b](./003b-request-shaping.md),
which already touches composition.

### Geometry: none added

Because reach is always an *existing* `Domain` — never folded, never intersected — the resolver needs
only per-axis **extent containment** to test dominance, and `Interval.contains` already exists.
`Interval` union and intersection both drop out of this ticket; `Domain.intersect` stays the *declared
seam* it is today in [`domain.py`](../../src/meteoscape/manifold/domain.py).

The dominance test should **not** reuse `Domain.matches`. That is the *admission* predicate: it is
request-side, and `VantageAxis` overrides it with **intersection** rather than containment — which
would silently make dominance mean something else. A `VantageAxis` is a request/Coverage axis and never
a capability footprint axis, so this is a hygiene point rather than a live bug. Use explicit extent
containment.

That collapses three standing concerns to **no-ops for this ticket** (session 0014):

- **[#22](../concerns.md#22-lattice-helpers-vs-domain--sampling-module-split)** — **no carve.** The
  ticket adds no geometry to `domain.py` at all, and no consumer of `encode_flat_index` /
  `sub_lattice_offset` / `AXIS_ORDER`.
- **[#23](../concerns.md#23-spatial-vs-temporal-regularaxis-types)** — **no split.** Dominance is
  `Interval.contains`, whose comparisons work on `float` and `datetime` alike, and `Interval` is
  already generic over the *constrained* TypeVar `C: (float, datetime)`. **Zero new `isinstance`
  dispatch.**
- **[#12](../concerns.md#12-curvilinear-domains)** / **[#13](../concerns.md#13-candidate-admission-containment-vs-intersection)**
  — both still want `intersect` eventually; neither is advanced or blocked here.

## Acceptance criteria

- [ ] `Provider` publishes **`footprints: Mapping[ParameterId, Domain]`** — the per-parameter geometry
      it already declares. That is the **only** contract change: nothing added to `Capability`, no
      composite implementation, no `Reservoir` forwarding, nothing on `Coverage`.
- [ ] `validate_calculators(ProfileDef)` exists in **`nodes/reach.py`** (a **separate method** from
      `resolve_reach`), standalone — testable without weaving. A calculator input **no producer serves**
      raises `CompositionError` naming the calculator + input (broken operator promise, not a silent
      runtime miss); a calculator **cycle** raises naming the cycle. Owns the `visiting` cycle guard.
- [ ] `resolve_reach(ProfileDef) -> Mapping[ParameterId, Domain]` exists in the same module, standalone,
      needing no `ArbiterPolicy` / reconciler. **Precondition: a validated `ProfileDef`** — so its only
      raises are *geometry*, never wiring. A **provider** parameter no enabled source serves is
      **absent from the map** (graceful degrade; 003b's `min`-over-parameters fold skips it).
- [ ] The `grid` reach rule exists as a **named unit** (no protocol, no config, no registry), with its
      two site procedures: **Arbiter** — the producer dominating on **X/Y**, then among X/Y ties on the
      remaining axes; **Calculator** — the input contained in **every other input on all axes**
      (whole-box; `{Europe × 10 d, Global × 5 d}` as inputs **raises**, never yields `Europe × 10 d`).
- [ ] **An equal-extent tie returns one of the inputs** — the test asserts identity ∈ inputs, not
      *which* (unobservable). Two equal `Global × 10 d` footprints never raise (the derived-wind case);
      no sort is imposed.
- [ ] **No `Domain` is ever synthesized** — every reach returned is an existing declared footprint. No
      `Interval` union or intersection is added; `Domain.intersect` stays a declared seam.
- [ ] `grid` **ignores producer priority**: `{Global × 10 d @1, Global × 16 d @2}` → **16 d**.
- [ ] Unresolved dominance/geometry raises **`CompositionError`** naming the conflicting producers (by
      `SourceKey` / `CalculatorKey`) and the axis on which dominance failed.
- [ ] A **Calculator competes at the top level like any producer**; a **`stored` calculator is
      transparent** to reach (the flag is never consulted).
- [ ] `{Europe × 16 d, Global × 10 d}` → `Global × 10 d`; adding `Arctic × 5 d` still yields
      `Global × 10 d`; `{Global × 16 d, Global × 10 d}` → `Global × 16 d`;
      `{Europe × 16 d, Americas × 10 d}` raises.
- [ ] The returned reach is the winner's own `Domain` — a clock-anchored `RollingAxis` stays **live**
      (its T upper bound tracks the clock), not snapshotted at build.
- [ ] Dominance is tested by explicit extent containment, **not** `Domain.matches` (the admission
      predicate, which `VantageAxis` specialises to intersection).
- [ ] `serves` behaviour and the request path are **unchanged** by this ticket.
- [ ] Unit tests only — no surface or Weaver changes; the sole provider change is the `footprints`
      accessor.

## User stories addressed

Enables user story 10 (envelope narration), delivered by
[003b](./003b-request-shaping.md).
