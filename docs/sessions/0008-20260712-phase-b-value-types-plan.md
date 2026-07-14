# 0008 · 2026-07-12 · Phase B — value-type behaviour plan (align session)

Continues [session 0007](./0007-20260711-phase-a-weave-plan.md) (Phase A landed). Grilled Phase B of
[issue 001](../tickets/done/001-walking-skeleton.md) — the six runtime stubs in
`manifold/domain.py` / `coverage.py` — and, along the way, dissolved two of them into simpler shapes
than originally planned. Deliverable: the decisions below + the TDD cycle list.

## Decisions

- **`contains` is extent (reach) containment, for every `Domain` representation.** Per-axis tick-span
  vs tick-span; one shared helper serves `FootprintDomain` and `RegularDomain`. Tick **alignment is
  never `contains`' job** — it belongs to the operations that consume it (the sampling engine's crop,
  006's `quantize`, and eventually the resampler branch of `serves`). Docstring caveat recorded: on an
  enumerable domain `contains` means *reach*, not tick-set membership. Grounding: ADR-0004 — the
  capability filter's `contains` is "only the geometric half"; nothing on any request path asks
  enumerable-vs-enumerable membership as containment.
- **`Axis.extent` = the tick span** `[anchor, anchor + (count−1)·step]`, uniformly — `cellular`
  affects only each `Cell`'s `bounds`, never axis geometry. The horizon-edge question for extensive
  parameters (last cell's accumulation span pokes past the footprint) is **per-parameter, owned by the
  `extent_scaling`-branched `serves`**, not by geometry — an intensive parameter serves to the final
  forecast instant; an extensive one goes `capability-mismatch` (omitted, producible subset), never a
  padded nodata cell. Filed on [issue 002](../tickets/002-core-5-parameters.md) with
  precipitation; not Phase B.
- **Four axes mandatory on every Domain, validated at construction** (`ValueError` in
  `__post_init__`). Absence never has a meaning: a point is a count-1 axis, near-surface is the fat
  Z cell, "anywhere" is a global `ContinuousAxis`. `contains` iterates the four names, total.
- **Enumeration order: X → Y → Z → T, T fastest-varying** (row-major). Permanent wire-format
  convention: `ParameterData.values[i]` is positional to it; a point timeline enumerates in time
  order. **Discipline rule:** index arithmetic lives *only* in the Domain and the sampling engine —
  every other consumer treats `values[i]` as opaque-positional. (ADR-0002's unspecified packing
  survives only as long as this holds.)
- **Spatial lattice tolerance: one module-level absolute constant, `1e-9`°**, applied through a single
  alignment helper. Float-noise scale only — *not* a snapping radius (~100 m coalescing is the store
  step / kernel discussion, 006/007). The time axis needs none (`timedelta` arithmetic is exact).
  With `contains` extents-only, the helper is consumed by the sampling engine's alignment check, not
  by `contains`.
- **`Timeline` the class → `CoverageRecord`** — the one concrete, memory-backed realization of the
  `Coverage` protocol; its fields were never time-specific. **Timeline / Grid become domain-shape
  vocabulary**, not types. Two conventions recorded with it:
  - **Shape ban** — Coverage implementations may vary by **backing** (memory now; file-backed with the
    persisting `Store`; db-backed plausibly with the run-collection layer), **never by domain shape**.
    Shape variety lives in `Domain` representations; the positional coupling of `values` to
    enumeration is the one sanctioned breach, guarded by the discipline rule above.
  - Names weighed: `Tensor`, `GridCoverage` (collides with glossary `Grid`; violates the shape ban),
    `InMemoryCoverage`, `CoverageMemo` (collides with ADR-0004 memoization), `RamCoverage`,
    `CoveragePlate` / `Swatch` / `Reading` / `Imprint` et al. — `CoverageRecord` chosen.
- **One sampling engine behind `project`; no second verb.** ADR-0001 already rules it: "sampling is
  just `project` with an enumerable Selection — no separate `sample` verb." So the public face is
  `Coverage.project` only; `manifold/sampling.py` is the **private** engine module it delegates to
  (`resample(coverage, selection) → CoverageRecord`). Walked every `project` in the system, current
  and roadmap (Arbiter + reconcilers, Calculators + stencils, Reservoir, Store, Providers, station
  network, cross-run collection): **numeric resampling is Coverage-only; composites do composition
  logic and pass the Domain through** — even the interpolating station leaf is "a Coverage on an
  irregular point-set Domain, projected." Engine asymmetry: consumes any `Coverage` (protocol),
  always produces a `CoverageRecord`.
- **v1 engine = the aligned crop; the kernel registry is *not* minted yet.** One kernel needs no
  registry — the selector → implementation lookup (ADR-0004's resampler registry, concern #5) gets
  its shape at 007 when nearest-neighbor becomes the second kernel, with a real case to test.
- **`CoverageRecord.project` strictness** (rules live in the engine): parameter not held →
  `ValueError` (algebra-internal misuse; producible-subset semantics belong to the Arbiter and the
  edge); enumerable aligned sub-lattice → crop (slice `values`/`present` positionally, restrict
  `ranges` + capability parameters, provenance passes through); off-phase or continuous selection →
  `NotImplementedError` (homogenization is the `Reservoir`'s; interpolated fields are deferred —
  concern #5).
- **`store_spatial_step` default → `0.0001`° (~11 m)** — landed during the session (config + test +
  issue 007 note): a **per-point cache** — near-exact values under nearest-neighbor read-back; spatial
  sharing only for repeat coordinates (the agent case). Caveat filed on 007: fidelity is the coarsest
  link — the Open-Meteo source-store lattice guess must be comparably fine.

## Implementation plan (TDD — one test → one implementation, vertical)

`tests/manifold/test_domain.py` (hypothesis for the property cycles):

1. `RegularAxis.__getitem__` / `__len__` — `axis[i].coordinate == anchor + i·step`; `cellular=True` ⇒
   `bounds = [coord, coord + step]`, else `bounds is None`; index bounds-checked. *(Tracer bullet.)*
2. `RegularAxis.extent` — tick span, identical formula for cellular and instants.
3. `RegularDomain` construction — exactly the four axes or `ValueError`.
4. `RegularDomain` enumeration — `len == Π count`; X→Y→Z→T nesting, T fastest; positional round-trip
   `domain[i] == list(domain.enumerate())[i]`; degenerate point-timeline case enumerates in time order.
5. `FootprintDomain.contains` — per-axis extent containment over a `Separable` other; non-separable →
   `False`; `RollingAxis` edges via `StoppedClock` (inside window / one tick past `A + max_lead` /
   before `A`).
6. `RegularDomain.contains` — same shared extent walk (enumerable ⊆ enumerable by span; continuous
   other → per-axis span check; off-span → `False`).
7. **Rename** `Timeline` → `CoverageRecord` (mechanical: `coverage.py`, `__init__` exports, doc
   references; suite stays green).

`tests/manifold/test_sampling.py`:

8. Identity projection — selection == the record's own domain + full parameter set → equal record
   back. *(Engine tracer bullet; `CoverageRecord.project` is the one delegating line.)*
9. Parameter-subset restriction — `ranges` / capability parameters narrowed; provenance intact.
10. Aligned `valid_time` crop — sub-window slices `values` / `present` positionally (uses the
    tolerance helper; off-by-one edges property-tested).
11. Parameter not held → `ValueError`.
12. Off-phase selection → `NotImplementedError`; continuous selection → `NotImplementedError`.

Backfill (owed from 000, `tests/manifold/test_cadence.py` / `test_capability.py`):

13. `CadenceDef` — `anchor` step-function edges (just before / at publication), `expiration =
    A + Δ + L`, `valid_time` window `[A, A + max_lead]`.
14. `Capability` family `serves` — `FootprintCapability` (now over real `contains`),
    `EnumerableCapability`, `UnionCapability` (some member), `DerivedCapability` (all inputs).

Then the refactor pass — shared extent-walk helper, fixture builders (`point_timeline_domain()`),
never while red.

## Modules touched

`manifold/domain.py` (axis/domain behaviour + validation + tolerance constant) ·
`manifold/coverage.py` (rename, delegating `project`) · `manifold/sampling.py` (new, private engine) ·
`manifold/__init__.py` / stray `Timeline` references · `docs/glossary.md` (CoverageRecord entry;
Timeline/Grid as domain shapes) · `tests/manifold/` (4 modules + fixtures).

## Out of scope

The `serves` resampler / extensive-edge branch (002) · kernel registry + nearest-neighbor (007) ·
`quantize` + store-grid representation (006) · numpy/xarray backing (behind `ParameterData`) ·
`intersect`, `PerPoint`, rectilinear / curvilinear (declared seams) · every composite `project`
(Phase C).

## Continuation

- Phase C (the spine) per [issue 001](../tickets/done/001-walking-skeleton.md).
- Extensive `serves` edge → [issue 002](../tickets/002-core-5-parameters.md);
  store-grid representation + kernel registry → issues 006 / 007.
