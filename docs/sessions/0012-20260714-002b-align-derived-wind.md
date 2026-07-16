# 0012 · 2026-07-14 · 002b align — derived wind: multi-output Calculator, Arbiter assembly, provenance propagation

Continues [session 0011](./0011-20260713-002-align-z-carriage.md). Session opened by committing the
**002 implementation** (commit `5af5c95` — Tap table, native Z carriage, edge exposure), then ran an
`align` pass on [ticket 002b](../tickets/002b-derived-wind-calculator.md). Three decisions crystallised,
each reversing or sharpening a prior contract; docs updated inline.

## The decisions

1. **The top Arbiter assembling one Coverage from disjoint single-parameter winners *is* the subject of
   002b** (not an incidental side-effect). A Calculator is a distinct **graph node** from the providers,
   so any response mixing a canonical parameter (won by a provider node) with a derived one (won by the
   Calculator node) spans ≥2 nodes — which the default `forecast_hourly()` does. The disjointness is
   **graph-structural, not data-origin**: even though all v1 data comes from one vendor (Open-Meteo), the
   Calculator sits *beside* the provider under the top Arbiter, which assembles by node identity. 002b is
   the first time the system has more than one node under the top Arbiter, so it is the first time the
   assembly is needed. It stitches via the **`PerParameter`** plane (which already exists for exactly
   this), retiring the current `Arbiter.project` guard that raises when winners are not all one node. The
   assembly machinery therefore lands here; ticket 005 shrinks to a **provider-competition demo** over the
   same path.

2. **One multi-output Calculator for wind** — `{wind_speed, wind_direction}` co-produced from
   `{wind_u, wind_v}` by a single node, resolving `(u, v)` **once**. Reverses ADR-0004's "unary … single
   output parameter." It is the honest model and **symmetric** with how a provider co-produces `u/v` from
   one native field. Consequence: requesting both wind params together is a **single winner** (no
   assembly for the pair); the assembly in (1) is exercised by wind *beside* the canonical params. Type
   ripple (code, settled here, applied in the build pass): `output → outputs` on `Calculator`,
   `DerivedCapability`, `RegisteredCalculator`, `CalculatorDef`; `fn` returns the pair; Weaver memoizes
   one node per derived **output group** (both member params route to it).

3. **Wind propagates the provider's atomic origin — no synthesis.** Because the derivation is **lossless
   and invertible** (it is the inverse of 002's `u/v` normalization — Open-Meteo natively serves wind
   speed/direction), it **preserves its input** and propagates that origin verbatim; the origin is
   literally its wind field. The rule is stated by the *nature of the derivation, not the input count*:
   **synthesis tracks the calculation method.** A `SyntheticOrigin` (kept as a declared seam, option a —
   not deleted) carries **lineage + a calculation-method tag** and is minted by a **method-bearing**
   computation *even over a single shared-origin input*, or by a **multi-origin** blend. v1's only
   Calculator (wind) is lossless, so v1 builds **only atomic origins** and the edge serializer stays on
   the `AtomicOrigin` path.

4. **The combine kernel is `fn: Coverage → Coverage`; the node owns provenance + well-formedness.**
   Rejected a values-only kernel (`Sequence[float]` or per-tick scalar): a flat array is the *timeline
   shape smuggled into the boundary*, blinding any shape-aware calculator (grid gradient, advection,
   vertical integral) to the domain and forcing a boundary widening later. The kernel instead speaks the
   algebra's own exchange unit — it receives the resolved input `Coverage` (ranges **and domain**) and
   returns the output group's ranges on a possibly-transformed domain; this is *membership* in the
   Coverage vocabulary the Arbiter / reconciler / `project` already share, not a data-model *leak*. The
   one real cost of Coverage-level — plugins authoring provenance or malformed output — is neutralised by
   splitting responsibilities: **kernel owns structure/computation; node owns provenance authorship**
   (propagate, or mint `SyntheticOrigin` with the **method tag declared on `CalculatorManifest`**) **and
   output well-formedness validation** (ranges keyed by the declared output group, aligned to the domain).
   So the propagate-vs-synthesize rule lives in exactly one place and cannot drift across plugin authors.

5. **Sources and Calculators unify as `Producer{node, key}` — the Arbiter's candidate.** Honours
   ADR-0004's own "a Calculator is just another candidate producer," which the types had betrayed by
   special-casing Sources. `Arbiter(producers, reconciler)` indexes every producer through one path
   (`ProducerKey = SourceKey | CalculatorKey`). The unification lands at the **candidate the Arbiter
   consumes**, *not* at construction: the two binders / registries stay distinct (ADR-0005), and the
   **Weaver** is the convergence point that wraps both built node kinds as `Producer`s. `Producer` carries
   **no priority** — a neutral candidate.

6. **The `Reconciler` becomes a first-class object; the Weaver never ranks.** Caught a real overlap:
   "priority on `Producer`, drop the registry" (an earlier sub-decision, now **reverted**) forced the
   Weaver to assemble ranking inputs — contradicting ADR-0004's "priority is registry data; the reconciler
   interprets it; the Weaver never ranks." Fix (the user's option 3): extract the `Reconciler` from inline
   Arbiter control flow. Priority stays a **recipe field on both registries** (`RegisteredSource.priority`,
   add `RegisteredCalculator.priority`); `build_reconciler(ArbiterPolicy, SourceRegistry,
   CalculatorRegistry)` flattens them into a plain `priority: Mapping[ProducerKey, int]` and returns a
   `PriorityReconciler` holding **that map, not the registries** (bare, testable). The Weaver *invokes the
   factory* and injects the reconciler into every Arbiter (top + scoped) — it orders nothing. The
   priority-data path: **registries → `build_reconciler` → `ProducerKey→int` map → `PriorityReconciler` →
   Arbiter**, joined because the Weaver stamps each `Producer` with the same key its priority is registered
   under.

7. **Calculators are identified by method, keyed like sources.** Output-group-as-identity was rejected —
   it collapses two calculators serving one output by *different methods*, the exact competing-producer
   case ranking exists for. **`CalculatorKey(method, name)`** is the calculator peer of
   `SourceKey(provider, dataset)` (`method = fn_id`; `name` a binder-defaulted variant); the
   `CalculatorRegistry` is **re-keyed by `CalculatorKey`** (was `ParameterId`). **`CalculatorSpec` →
   `CalculatorDef`** (peer of `OfferingDef`), gaining `priority` + `name?` + `outputs`;
   `RegisteredCalculator` gains `key` + `priority`. Net: **both registries keyed by their `ProducerKey`,
   both carrying `priority`, both flattened into `build_reconciler`** — same-output/different-method
   calculators become ordinary competing producers, exactly parallel to competing providers.

**Assembly mechanics (decision 1's realization, agreed).** Single winner → project once (fast path).
`>1` winning producer → group admitted params by producer, project each **once** on `sel.domain`, merge
into a `CoverageRecord` (unioned `ranges` + `EnumerableCapability` + a `PerParameter` plane, each param's
`Provenance` = its winner's `summary`). Closed projection guarantees the shared domain, so the merge
asserts identity, never resamples.

## Layer distinction that unlocked it (grilling artefact)

Two "sameness" claims had been bleeding together. Separated:

- **Inner — a Calculator resolving its inputs `(u, v)`:** single-node **by construction** (ADR-0004
  co-production: a producer serves the whole component set from one origin or none; component coherence is
  a **build-time** well-formedness property the Weaver *can* assert). In v1 there is one provider, so `u`
  and `v` co-originate trivially — **no merge, ever**. The Weaver co-production assertion is a **seam
  deferred to 004** (second provider), when it first earns its keep.
- **Outer — the top Arbiter assembling the response:** `wind_speed` (Calculator node) beside
  `air_temperature` (provider node) → disjoint winners → **the only genuine multi-node case in 002b**, and
  the thing decision 1 builds.

## Docs updated with this session

- **ADR-0003** — synthetic origin redefined as a composite's **derivation record** (lineage +
  calculation-method tag), minted by a method-bearing *or* multi-origin derivation; a lossless invertible
  transform **propagates** instead. Synthesis tracks the *method, not the input count*. Version-free.
- **ADR-0004** — `DerivedCapability` is an input→output transform over a **co-produced output group
  (1..N)**, not unary single-output; Calculator section notes group routing, single resolve, and
  **provenance propagation**; new bullet + code sketch for the **`fn: Coverage → Coverage`** boundary
  (kernel owns structure; node owns provenance + validation); memoization keyed by **output group**.
- **`catalog/calculators.py`** — `CalculatorManifest.fn` retyped `CombineFn = Callable[[Coverage],
  Coverage]`; method-tag note added.
- **ADR-0004** — `Producer{node, key}` unification; the **assembly** bullet (disjoint winners →
  `PerParameter` `CoverageRecord`); `Priority is registry data` rewritten around a first-class
  `Reconciler` + `build_reconciler`; weave sketch updated to `Arbiter(producers, reconciler)`.
- **ADR-0005** — Weaver builds `Producer`s from both registries and constructs the reconciler via the
  policy-keyed factory; two registries stay distinct, Weaver is the convergence point.
- **glossary** — added `Producer` + `CalculatorKey`; `CalculatorSpec` → `CalculatorDef` (re-keyed by
  `CalculatorKey`). All definition-only.
- **ADR-0005 / architecture / module-layout** — `CalculatorSpec` → `CalculatorDef` (peer of
  `OfferingDef`, +`priority`/`name?`/`outputs`); `CalculatorRegistry` keyed by `CalculatorKey` (peer of
  `SourceKey`); both registries keyed by `ProducerKey`, both carry `priority`.
- **`provenance.py`** — module + `SyntheticOrigin` docstrings retagged: synthetic = a method-bearing
  *or* multi-origin derivation record (post-v1 seam); a lossless invertible transform (wind) propagates
  its input's atomic origin.
- **glossary** — `Calculator` entry tightened to a **definition only** (co-produced output group,
  selectable producer, own scoped Arbiter); the provenance rule lives in the ADRs, not here.
- **ticket 002b** — outcome + What-to-build + acceptance criteria reframed around three deliverables
  (multi-parameter assembly; `Producer` / `Reconciler` unification; single multi-output wind Calculator),
  the `fn: Coverage → Coverage` boundary, and provider-origin propagation.
- **ticket 005** — reframed as provider-competition over the assembly that now lands in 002b.

## Open / continuation

- **002b implementation deltas** (for the `/to-tickets` / TDD build pass):
  - **Producer / Reconciler refactor** (touches shipped 002): introduce `Producer{node, key}` +
    `ProducerKey = SourceKey | CalculatorKey`; extract `Reconciler` (a `PriorityReconciler` holding a
    `ProducerKey → int` map) + `build_reconciler(policy, SourceRegistry, CalculatorRegistry)`; change
    `Arbiter` to `Arbiter(producers, reconciler)`.
  - **Calculator identity + config symmetry**: add `CalculatorKey(method, name)` (in `identity.py`,
    peer of `SourceKey`); rename `CalculatorSpec → CalculatorDef` (peer of `OfferingDef`) with `priority`
    + `name?` + `outputs`; re-key `CalculatorRegistry` by `CalculatorKey`; `RegisteredCalculator` gains
    `key` + `priority`; `CalculatorBinder` + `ProfileConfig` follow.
  - **Multi-output `Calculator`** (`output → outputs`) across `Calculator` / `DerivedCapability` /
    `RegisteredCalculator` / `CalculatorDef`; `fn: Coverage → Coverage` (`CombineFn`), node owns
    provenance stamping + output validation.
  - **Top-Arbiter assembly**: group admitted params by winning producer, project each once, merge into a
    `PerParameter` `CoverageRecord` (retire the not-all-one-node guard).
  - **Weaver Calculator weave**: memoize per output group; scoped input Arbiter over the `Producer` subset
    serving the calc's inputs; wrap both node kinds as `Producer`s; construct the reconciler via factory.
  - **Provenance propagation** (no `SyntheticOrigin` construction); `wind_speed_10m` / `wind_direction_10m`
    round-trip verified against 002's `u/v` normalizer.
- **Deferred seams named here:** the Weaver **co-production well-formedness assertion** → 004;
  `SyntheticOrigin` behaviour (lineage + method tag) → first synthetic Calculator, method-bearing or
  multi-origin (post-v1).
- **002b align is complete** — ready for the build pass.
