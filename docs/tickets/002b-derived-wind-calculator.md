# 002b — Derived wind calculator

- **Status:** Ready
- **Depends on:** [002 — Core canonical parameters](./done/002-core-5-parameters.md) (done)
- **Outcome:** The first multi-parameter Coverage assembly (top Arbiter stitches disjoint single-parameter
  winners) plus a single wind Calculator serving `wind_speed` / `wind_direction`, provenance propagated
  from the provider (no synthesis).

## Parent PRD

`docs/v1-requirements.md`

## What to build

Three coupled deliverables — this is the **first response the top Arbiter assembles from more than one
node**, and the derived-wind Calculator is the case that forces it.

**1. Top-Arbiter multi-parameter assembly (the real subject).** A Calculator is a distinct graph node
from the providers, so any response mixing a canonical parameter (won by a provider node) with a derived
one (won by the Calculator node) spans ≥2 nodes — which the default `forecast_hourly()` does. The Arbiter
must stitch these **disjoint single-parameter winners**, each serving its own parameters on the **shared
requested domain**, into one Coverage via the **`PerParameter`** provenance plane (which exists for exactly
this). Every winner's slice is single-origin; the Arbiter never folds origins *within* a parameter. This
retires the current `Arbiter.project` guard that raises when winners are not all the same node.

**1a. Unify producers + extract the reconciler (the structure that makes the Calculator a candidate).**
Sources and Calculators become one **`Producer{node, key}`** shape, `ProducerKey = SourceKey |
CalculatorKey`. **`CalculatorKey(method, name)`** is the calculator peer of `SourceKey(provider,
dataset)` (keyed on the *method*, not the output, so same-output/different-method calculators are distinct
producers). **`CalculatorDef`** (rename of `CalculatorSpec`, peer of `OfferingDef`) gains `priority` +
`name?` and `output → outputs`; `CalculatorRegistry` is **re-keyed by `CalculatorKey`** (was
`ParameterId`); `RegisteredCalculator` gains `key` + `priority`. The Arbiter becomes
`Arbiter(producers, reconciler)` and indexes every producer through one path. The **`Reconciler`** is
extracted to a first-class object built by `build_reconciler(ArbiterPolicy, SourceRegistry,
CalculatorRegistry)`, which flattens **both** registries' `priority` recipe fields into its
`ProducerKey → int` lookup — `Producer` carries no priority. The Weaver wraps both node kinds as
`Producer`s and *invokes* the factory; it never ranks. The two binders / registries stay distinct
([ADR-0005](../adr/0005-build-time-composition.md)).

**2. A single wind Calculator (`{wind_speed, wind_direction}` from `{wind_u, wind_v}`).** One
**multi-output** Calculator node — `speed = hypot(u, v)`, `direction = atan2(...)`, both **lossless**
functions of the canonical vector — resolving `(u, v)` **once** and emitting both outputs. It carries its
own **scoped input `Arbiter`** (resolving `wind_u` / `wind_v` and nothing else, so every edge points
downward and the graph stays an acyclic DAG), is woven from the **`CalculatorRegistry`** (bound by
`CalculatorBinder` from `CalculatorDef`s against the `CalculatorCatalog`,
[ADR-0005](../adr/0005-build-time-composition.md)) with **memoization** (one node per derived output
group; both member parameters route to it), and advertises a **`DerivedCapability`** serving the output
group iff all inputs are servable through the scoped resolver. Because the group is co-produced from one
resolve, requesting both wind params together is a **single winner** — the assembly in (1) is exercised
by wind *beside* the canonical parameters, not by the wind pair itself.

**Combine kernel — `fn: Coverage → Coverage`.** The kernel (`CalculatorManifest.fn`, `CombineFn`) receives
the resolved input Coverage (ranges + domain, so it is shape-general: timeline now, grid/station later) and
returns the output group's ranges. The **`Calculator` node**, not the kernel, owns **provenance
authorship** and **output well-formedness** (ranges keyed by the declared output group, aligned to the
domain). The wind kernel is `speed = hypot(u, v)`, `direction = atan2(...)`, with the output present-mask
the elementwise AND of the inputs'.

**Provenance propagates — no synthesis.** The wind outputs carry the **atomic** provider origin of their
`u/v` inputs verbatim: the transform is lossless and single-source, and Open-Meteo natively serves wind
speed/direction (002 converts them *to* `u/v`; here we convert *back*), so the origin is literally its
wind field (the derivation preserves its input, so it propagates rather than mints — see
[ADR-0003](../adr/0003-provenance-and-origin.md)). `SyntheticOrigin` stays a declared seam for a future
**method-bearing or multi-origin** derivation.

`wind_direction` is `circular` (the first non-linear `scale`), but v1's nearest-neighbor read-back never
interpolates it, so no angular kernel is exercised (a future kernel must be angular via u/v, never a
degree average — [concern #5](../concerns.md#5-read-time-homogenization-fidelity)). See
`docs/v1-requirements.md` (Parameters) and
[ADR-0004](../adr/0004-producer-resolution-and-capability.md) (Calculators).

## Acceptance criteria

- [ ] The default `forecast_hourly(lat, lon)` returns canonical parameters (from a provider node) **and**
      `wind_speed` / `wind_direction` (from the Calculator node) in **one Coverage** — i.e. the top
      Arbiter **assembles disjoint single-parameter winners** on the shared domain via `PerParameter`;
      the old "winners not all one node → raise" guard is gone.
- [ ] `wind_speed` and `wind_direction` are served by **one multi-output Calculator** that resolves
      `(wind_u, wind_v)` **once**; the derived values are exact functions of u/v (`speed = hypot`,
      `direction = atan2`) in their canonical units (m/s, degree).
- [ ] The combine kernel is **`fn: Coverage → Coverage`** (`CombineFn`); the **node** (not the kernel)
      stamps provenance and validates output well-formedness (ranges keyed by the declared output group,
      aligned to the domain). The kernel authors no lineage.
- [ ] Sources and Calculators are one **`Producer{node, key}`** shape; the Arbiter is
      `Arbiter(producers, reconciler)`; the **`Reconciler`** is a first-class object holding a
      `ProducerKey → priority` lookup built from both registries by `build_reconciler`. The Weaver wraps
      producers and constructs the reconciler; it never ranks.
- [ ] **`CalculatorKey(method, name)`** identifies a calculator (peer of `SourceKey`); `CalculatorSpec`
      is renamed **`CalculatorDef`** (peer of `OfferingDef`) with `priority` + `name?` + `outputs`;
      `CalculatorRegistry` is keyed by `CalculatorKey`; two same-output/different-method calculators are
      distinct competing producers.
- [ ] Requesting both wind params together routes to a **single winner** (one node), while requesting a
      wind param beside a canonical one exercises the multi-node assembly.
- [ ] Each derived `ParameterData` **propagates the provider's atomic origin** (Open-Meteo) — no
      `SyntheticOrigin` in v1; provenance/freshness match the `u/v` inputs.
- [ ] The `Calculator` resolves its inputs through a **scoped `Arbiter`** (inputs only); the `Weaver`
      memoizes one `Calculator` node per derived **output group**; the graph is acyclic.
- [ ] `wind_u` / `wind_v` stay **internal-only** — not directly requestable via `forecast_hourly`.
- [ ] Unit + mocked-transport integration tests cover the u/v → speed/direction derivation, the
      **provider-origin propagation**, and the **multi-node Coverage assembly** (derived beside canonical).

## User stories addressed

- User story 1
- User story 4
