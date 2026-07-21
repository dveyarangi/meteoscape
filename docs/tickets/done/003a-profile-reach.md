# 003a — Profile reach

- **Status:** Done
- **Depends on:** [002 — Core canonical parameters](./002-core-5-parameters.md),
  [002b — Derived wind](./002b-derived-wind-calculator.md)
- **Outcome:** A **build-time resolver** that reports the per-parameter `Domain` a profile reaches —
  the fact every surface needs to narrate an envelope or author a default window.

## Parent PRD

`docs/v1-requirements.md`

## What to build

Build-time only — **no surface change and no request-path change**.
[003b](../003c-request-shaping.md) is the consumer. Two methods in a new **`nodes/reach.py`**:

```
validate_calculators(ProfileDef) -> None                     # is it wired?  (raises)
resolve_reach(ProfileDef)        -> Mapping[ParameterId, Domain]   # how far?  (assumes validated)
```

Reach is an **inner bound**: *every point it names is servable*
([ADR-0007](../../adr/0007-capability-carries-its-domain.md)).

**Reach is profile-level, not a `Capability` facet, and selected rather than folded** — the semantics
(inner bound, the `grid` rule's two site procedures, tie resolution, never-synthesize, liveness) are
**owned entire by [ADR-0007](../../adr/0007-capability-carries-its-domain.md)**; this ticket builds them, and
the acceptance criteria below encode them as tests.

The **one contract change**: **`Provider` publishes the per-parameter footprint it already declares**,
so the resolver can read it. Nothing is added to `Capability`.

**The graph is one shape all the way down, so the resolution is one mutual recursion.** A Calculator's
inputs are resolved by a **scoped `Arbiter`** ([weaver.py](../../../src/meteoscape/nodes/weaver.py)), so
the same two sites repeat at every depth:

```
reach(arbiter, p)    = RULE.reach([ footprint(prod, p) for prod in producers serving p ])
footprint(source, p) = the provider's declared footprint for p
footprint(calc, p)   = contained_in_all([ reach(calc.scoped_arbiter, i) for i in calc.inputs ])
```

**The rule is consulted at the Arbiter site only.** There, alternatives compete and something must
*choose* — that is policy, and it is the rule's whole job. A Calculator has no choice: it serves where
**all** its inputs serve, so `contained_in_all` is **structure in the resolver**, not rule work.

**v1 builds the mechanism, not the judgment.** `reach`'s body is **containment** — the candidate
containing all others; equal-extent tie → any; none contains the rest → raise. ADR-0007's **X/Y-first
preference is deferred**: it only decides *incomparable* candidates, which need a **regional** provider,
and v1 has none (Open-Meteo and TWC are both global, so candidates either tie on X/Y or one contains
the other, where containment and X/Y-first agree).

Memoized per key. `validate_calculators` owns the `visiting` **cycle guard** and the *wiring* errors
(an input no producer serves — a calculator is an operator promise, so this fails the build explicitly,
never silently at runtime); `resolve_reach` runs after it and handles only *geometry*. Both walk this
DAG — a third walker beside the Weaver, deliberate ~3-line duplication
([#34](../../concerns.md#34-producer-dag-walking-is-duplicated)); the strict-calculator vs
graceful-provider tension is [#35](../../concerns.md#35-calculator-satisfiability-vs-optional-provider-degrade).

Build notes, each grounded in [ADR-0007](../../adr/0007-capability-carries-its-domain.md):

- **No new geometry primitive** — see [Geometry: none added](#geometry-none-added).
- **No `ArbiterPolicy` / `build_reconciler` dependency** — `grid` ignores priority
  (→ [#33](../../concerns.md#33-reconciler-owns-domain-composition) for why that is mode-scoped).
- **`CompositionError` when nothing resolves**, naming the conflicting producers (by `SourceKey` /
  `CalculatorKey`) and the failing axis — possible because the resolver works over `ProfileDef`. For
  incomparable candidates the message must also say the X/Y preference is **unbuilt**.
- **`GridReachRule` is a concrete class called directly** — a single `reach`, no `Protocol`, no config
  plumbing, no registry ([#28](../../concerns.md#28-reconciler-interface-selection-ordering-vs-per-cell-fold)'s
  recorded lesson; the contract gets extracted once a second rule exists, and that one is already known
  to need a wider interface).

**Wiring is 003b's.** This ticket delivers `validate_calculators`, `resolve_reach`, and the
`Provider.footprints` accessor; calling them from `compose()` — validate **before** `weave`, reach
after — and handing the map to the surface is [003b](../003c-request-shaping.md), which already touches
composition.

### Geometry: none added

Because reach is always an *existing* `Domain` — never folded, never intersected — the resolver needs
only per-axis **extent containment** to test dominance, and `Interval.contains` already exists.
`Interval` union and intersection both drop out of this ticket; `Domain.intersect` stays the *declared
seam* it is today in [`domain.py`](../../../src/meteoscape/manifold/domain.py).

The dominance test should **not** reuse `Domain.matches`. That is the *admission* predicate: it is
request-side, and `VantageAxis` overrides it with **intersection** rather than containment — which
would silently make dominance mean something else. A `VantageAxis` is a request/Coverage axis and never
a capability footprint axis, so this is a hygiene point rather than a live bug. Use explicit extent
containment.

That collapses three standing concerns to **no-ops for this ticket** (session 0014):

- **[#22](../../concerns.md#22-lattice-helpers-vs-domain--sampling-module-split)** — **no carve.** The
  ticket adds no geometry to `domain.py` at all, and no consumer of `encode_flat_index` /
  `sub_lattice_offset` / `AXIS_ORDER`.
- **[#23](../../concerns.md#23-spatial-vs-temporal-regularaxis-types)** — **no split.** Dominance is
  `Interval.contains`, whose comparisons work on `float` and `datetime` alike, and `Interval` is
  already generic over the *constrained* TypeVar `C: (float, datetime)`. **Zero new `isinstance`
  dispatch.**
- **[#12](../../concerns.md#12-curvilinear-domains)** / **[#13](../../concerns.md#13-candidate-admission-containment-vs-intersection)**
  — both still want `intersect` eventually; neither is advanced or blocked here.

## Acceptance criteria

- [x] `Provider` publishes **`footprints: Mapping[ParameterId, Domain]`** — the per-parameter geometry
      it already declares. That is the **only** contract change: nothing added to `Capability`, no
      composite implementation, no `Reservoir` forwarding, nothing on `Coverage`.
- [x] `validate_calculators(ProfileDef)` exists in **`nodes/reach.py`** (a **separate method** from
      `resolve_reach`), standalone — testable without weaving. A calculator input **no producer serves**
      raises `CompositionError` naming the calculator + input (broken operator promise, not a silent
      runtime miss); a calculator **cycle** raises naming the cycle. Owns the `visiting` cycle guard.
- [x] `resolve_reach(ProfileDef) -> Mapping[ParameterId, Domain]` exists in the same module, standalone,
      needing no `ArbiterPolicy` / reconciler. **Precondition: a validated `ProfileDef`** — so its only
      raises are *geometry*, never wiring. A **provider** parameter no enabled source serves is
      **absent from the map** (graceful degrade; 003b's `min`-over-parameters fold skips it).
- [x] `GridReachRule` exists as a **concrete class with a single `reach(candidates)`** (no `Protocol`,
      no config, no registry), consulted **only at the Arbiter site** — where alternatives compete.
      Its v1 body is **containment only**: the candidate containing all others; **no candidate contains
      the rest → `CompositionError`** stating the X/Y preference is unbuilt. The X/Y-first judgment is
      **not implemented** and no test asserts it (unreachable in v1 — both providers are global).
- [x] The **Calculator combination lives in the resolver, not the rule** — it serves where all inputs
      serve, so `contained_in_all` over its inputs' reaches; sheared inputs raise. No policy involved.
- [x] **An equal-extent tie returns one of the candidates** — the test asserts identity ∈ candidates,
      not *which* (unobservable). Two equal footprints never raise (the derived-wind case); no sort is
      imposed.
- [x] **No `Domain` is ever synthesized** — every reach returned is an existing declared footprint. No
      `Interval` union or intersection is added; `Domain.intersect` stays a declared seam.
- [x] `grid` **ignores producer priority**: `{Global × 10 d @1, Global × 16 d @2}` → **16 d**.
- [x] Unresolved dominance/geometry raises **`CompositionError`** naming the conflicting producers (by
      `SourceKey` / `CalculatorKey`) and the axis on which dominance failed.
- [x] A **Calculator competes at the top level like any producer**; a **`stored` calculator is
      transparent** to reach (the flag is never consulted).
- [x] `{Global × 16 d, Global × 10 d}` → `Global × 16 d` (the 004 shape); incomparable candidates
      raise. **No X/Y-first *judgment* is built or tested** — a regional footprint cannot occur in a v1
      profile, so nothing may depend on how incomparable candidates would be ranked. A regional box
      may still appear as *fixture geometry* for the **raise path**: `{Global × 10 d, Europe × 16 d}`
      is the smallest shape that proves the message names **both** failing axes rather than the first,
      which is mechanism, not judgment.
- [x] The returned reach is the winner's own `Domain` — a clock-anchored `RollingAxis` stays **live**
      (its T upper bound tracks the clock), not snapshotted at build.
- [x] Dominance is tested by explicit extent containment, **not** `Domain.matches` (the admission
      predicate, which `VantageAxis` specialises to intersection).
- [x] `serves` behaviour and the request path are **unchanged** by this ticket.
- [x] Unit tests only — no surface or Weaver changes; the sole provider change is the `footprints`
      accessor.

## User stories addressed

Enables user story 10 (envelope narration), delivered by
[003b](../003c-request-shaping.md).
