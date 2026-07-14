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
   `DerivedCapability`, `RegisteredCalculator`, `CalculatorSpec`; `fn` returns the pair; Weaver memoizes
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
- **`provenance.py`** — module + `SyntheticOrigin` docstrings retagged: synthetic = genuine ≥2-origin
  blend (post-v1 seam); wind propagates atomic.
- **glossary** — `Calculator` entry tightened to a **definition only** (co-produced output group,
  selectable producer, own scoped Arbiter); the provenance rule lives in the ADRs, not here.
- **ticket 002b** — outcome + What-to-build + acceptance criteria reframed around the two deliverables
  (multi-parameter assembly; single multi-output wind Calculator) and provider-origin propagation.
- **ticket 005** — reframed as provider-competition over the assembly that now lands in 002b.

## Open / continuation

- **002b implementation deltas** (for the `/to-tickets` / TDD build pass): the multi-output `Calculator`
  type change (`output → outputs`) across the Calculator / `DerivedCapability` / `RegisteredCalculator` /
  `CalculatorSpec` shapes and `fn`; the top-Arbiter **`PerParameter` assembly** (retire the
  not-all-one-node guard); the `Weaver` Calculator weave (memoize per output group, scoped input Arbiter
  over a subset of source nodes); provenance **propagation** (no `SyntheticOrigin` construction);
  `wind_speed_10m` / `wind_direction_10m` round-trip verified against 002's `u/v` normalizer.
- **Deferred seams named here:** the Weaver **co-production well-formedness assertion** → 004;
  `SyntheticOrigin` behaviour (lineage + method tag) → first synthetic Calculator, method-bearing or
  multi-origin (post-v1).
- **002b align is complete** — ready for the build pass.
