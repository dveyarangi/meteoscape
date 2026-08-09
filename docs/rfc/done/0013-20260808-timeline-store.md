# RFC 0013 · 2026-08-08, amended 2026-08-09 · The retentive Store (`MemoryStore`) — implementation plan

Implementation plan for [the retentive Store](../../tickets/done/01-0115.0030-timeline-store.md)
(slice 3 of the [retentive store](../../tickets/done/01-0115-retentive-store-freshness.md)). Resolves the
`assimilate` concrete shapes the align left tentative — this RFC is their durable home.

*Amended 2026-08-09 at the slice's own align:* the store-side `report` verb dissolved — the
store's public face is **the Manifold contract + `Writable` + `quantize`**; its `project` is the
holdings query and accepts **raw asks** (translation onto the boxes is internal); `quantize` is a
**store method** — the unit definition (lattices, and the axes a box spans) is constructor state,
never an argument — whose only public job is authoring the **refill fetch-order**; the
serve-vs-refetch gate (freshness + covers-or-refetch-whole) moved to the `Reservoir` as
[RFC 0014](./0014-20260808-reservoir-retention-pipeline.md) policy; the `Store` contract is
**clockless and freshness-blind**; the class is **`MemoryStore`** (substrate-named — the unit
fold is shape-generic, and what distinguishes this store from release-02's persisting siblings is
its substrate, not its timeline).

**Scope in one line:** a unit-granular, clockless `MemoryStore` — `project` answers what it holds
(raw asks), `assimilate` slices the answer, `quantize` authors the fetch-order — plus the
retentive `StoreFactory` wired at all three positions, **inert**: the `Reservoir` stays
pass-through, so no behavior changes.

## Boundaries involved

| Boundary | Owner | What this does to it |
|---|---|---|
| `quantize` (`nodes/store.py` — a `MemoryStore` method) | [ADR-0002 §grid alignment](../../adr/0002-data-model.md), [ADR-0006](../../adr/0006-materialization-granularity-and-store-shape.md) | Minted: the enclosing per-axis fold — `ground`'s sibling in *shape* only. One party (the request against the store's own unit definition), so it lives on the store; `domain.py` gains no lattice-taking export. Zero new index arithmetic ([#22](../../concerns.md#22-lattice-helpers-vs-domain--sampling-module-split) stands down). |
| `Store` protocol / `StubStore` (`nodes/store.py`) | ADR-0006, [ADR-0005](../../adr/0005-build-time-composition.md) | `MemoryStore` minted and wired **inert** — the pass-through `Reservoir` never touches its store, so "not yet serving" stays literally true; `StoreFactory.create(spec, deferred)` rebuilt; **`StubStore` deleted**, its `TODO (temporary)` retiring here. |
| `Weaver` / `wire_source` (`nodes/weaver.py`), factory construction (`server.py`) | [ADR-0005](../../adr/0005-build-time-composition.md) | The three `create` call sites pass their position-derived `deferred`; the factory is constructed with the injected `Clock`. Mechanical — no graph-shape change. |
| `Writable.assimilate` (`nodes/store.py`; moved out of `manifold/core.py` at stage 2, 2026-08-09) | [ADR-0001](../../adr/0001-manifold-algebra-and-composition.md) | Signature becomes `assimilate(answer: CoverageSet)` — the store consumes the natural answer and slices inside. The facet moves beside its sole realization: the `Store` is the only `Writable`, ADR-0006 names the facet as store face, and the move keeps `core.py` read-only with a one-directional import graph (no `TYPE_CHECKING` laundering of `coverage.py`'s name into the algebra). |
| Store `project` semantics | ADR-0006 (amended 2026-08-09) | The holdings query, total over raw asks (translation onto the boxes is internal): stale included, unheld omitted, empty answer normal. |
| Store `capability` | [ADR-0007](../../adr/0007-capability-carries-its-domain.md), [#47](../../concerns.md#47-a-stores-capability-narrates-plural-holdings-truncate-to-one-reach) | Holdings narration — `GranularCapability`, latest-assimilated unit per parameter. |
| Store lattice privacy | ADR-0006 | Guard test: no module outside `store.py` references its private unit or lattice types; no lattice type appears in any public signature. |

## Facts that shape the implementation (verified 2026-08-09)

1. `StoreSpec` is `{spatial_step: float, retention_interval: timedelta}` — **no temporal step**: the
   unit's T lattice is the answer's own; the store never invents one.
2. The vendor point is continuous (whole-globe footprint intervals) — any cell point is servable by
   identity, so the store grid needs no relationship to any provider lattice; it is a coalescing
   floor only.
3. `RegularAxis` fixes `(anchor, step, count)`; a global grid at `spatial_step` has a finite count,
   so the store's lattice materializes as an ordinary cellular `RegularAxis` per spatial axis — no
   new axis kind (parent ticket, store-lattice representation; m4).
4. All six Open-Meteo parameters share one `CadenceDef` → units from one trip share `fetched_at`
   and `expiration`; per-parameter staleness divergence is mock-only (parent, *Refill scope*).
5. **`reach` on a store has no algebraic caller.** The algebra reads `reach` in exactly two places,
   both on producers — the Arbiter's `compose_domains` over its members
   ([arbiter.py](../../../src/meteoscape/nodes/arbiter.py)) and a Calculator's contained-in-all over
   its resolver — plus the MCP edge's narration of the root; a store is never an Arbiter member,
   and the `Reservoir` forwards its *child's* capability upward. This is what makes decision 7's
   narration semantics safe.
6. `CoverageSet` refuses a parameter living on two records
   ([coverage.py](../../../src/meteoscape/manifold/coverage.py) `__post_init__`). Quantized members
   are emitted as **ticks, not fat cells** (decision 1), so **a point ask stays a point through
   every hop**: on the identical lattices v1 configures (source and root both `0.0001°`), a tick
   re-quantizes to itself — a fixed point — and even a coarser downstream lattice maps a point to
   one containing cell. A fat-cell member would instead graze the next cell at every hop (a cell's
   closed upper edge lands exactly on the neighbour's tick), making the single-cell claim false at
   the source position. Plural cells per axis therefore arise only from genuinely span-shaped
   asks — a future grid consumer — which is what decision 6's assert names.

## Design decisions

1. **`quantize(request) -> SelectionDomain`** — a `MemoryStore` **method**, `ground`'s sibling in
   fold shape, enclosing where `ground` restricts. Its context is `self`: the lattices (`_grids`)
   and the axes a box spans wholly (`_deferred`) — **constructor facts, never arguments**
   (2026-08-09 pass 3: the earlier free-function form forced the store to hand its privates
   through a public `domain.py` signature whose only legitimate caller was a store). The
   constructor takes the lattices **prepared** — decision 10: the factory owns `StoreSpec` →
   lattice derivation, so the store hardcodes no axis role and the inverted (T-latticed)
   instantiation is directly constructible in tests:

   ```python
   def quantize(self, request: Domain) -> SelectionDomain:
       """The fetch-order that fills my boxes for `request` — read `ground` first."""
       separable = as_separable(request)
       if separable is None:
           raise ValueError("quantize needs per-axis geometry; the request is not separable")
       axes: dict[AxisName, SelectableAxis] = {}
       for name in AXIS_ORDER:
           member = separable.axis(name)
           if name in self._deferred:                             # a box spans this axis wholly
               axes[name] = SnappedAxis(name, None)               #   → ANY, overriding the ask
           elif (grid := self._grids.get(name)) is not None:      # a box is one cell wide
               cells = grid.clip(member.extent)                   #   containing cell(s); clip owns the math
               if cells is None:
                   raise ValueError(f"request {name.value} is outside the store lattice")
               axes[name] = replace(cells, cellular=False)        #   → the cells' *ticks*, honest points
           else:                                                  # a box is keyed by the ask
               assert isinstance(member, RegularAxis | VantageAxis | SnappedAxis)  # SelectableAxis
               axes[name] = member
       return SelectionDomain(axes=axes)
   ```

   The timeline position constructs the store with X/Y grids and `deferred={T, Z}`; a grid-style
   position inverts the construction — the method hardcodes no axis role, and the ticket's
   inverted-unit criterion is tested **by instantiation**, not by a free function nobody else
   calls.

   **The latticed arm emits ticks, never fat cells** (2026-08-09 pass 2). A cell is two facts, and
   only one may leave the store: *containment* (which cell coalesces this point — the private
   lattice's business) and *the ask* (the representative coordinate the vendor will be asked at,
   the record will carry, and the unit will hold — the tick). A cellular member would claim the
   value holds over the whole span (∃ relabeled as ∀ — data loss), would graze the neighbouring
   cell whenever a downstream store re-quantizes it (fact 6), and would break positional alignment
   against the point-shaped X/Y the provider echoes into records. `replace(cells,
   cellular=False)` keeps the clipped lattice's anchor/step/count and drops only the span
   semantics — zero new arithmetic.
2. **The spatial grid, fully specified.** One cellular `RegularAxis` per spatial axis:
   `anchor = −180.0` (lon) / `−90.0` (lat), `step = spatial_step`,
   `count = floor(span / step) + 1` (span 360 / 180) — cells cover the **closed** domain, and the
   last cell may overhang the upper edge; the overhang is inert because the MCP edge already
   validates coordinates into `[−180, 180] × [−90, 90]`, so `+90` / `+180` land in the last cell
   rather than outside it. **No wraparound in v1**: `−180` and `+180` are distinct cells — the same
   meridian can cache twice, an accepted waste (the vendor treats the coordinate identically);
   wraparound becomes real only with a gridded provider. Poles get no special casing. `spatial_step`
   is validated at `StoreFactory.create`: `0 < step ≤ 90`, else `CompositionError` (build-time —
   ADR-0005's strict-binder posture).
3. **Unit shape.** Key `(ParameterId, x_index, y_index, z_key)` where `x/y_index` are lattice
   indices of the containing cell and `z_key` is the record's **Z axis value object** (`RegularAxis`
   point or `IntervalAxis` column — frozen dataclasses, hashable, equal across fetches of the same
   tap; at a Z-identity position the request's vantage cell arrives as the record's Z and keys the
   unit the same way, no special casing). The *fold* is unit-agnostic, but this key shape is the
   **fixed v1 instantiation** — both wired positions (`{T, Z}` and `{T}` deferred) share it; do not
   build a generically-keyed store nobody instantiates. Value:

   ```python
   @dataclass(frozen=True)
   class _Unit:
       domain: GridDomain            # the record's native geometry for this parameter (T whole)
       data: ParameterData
       definition: ParameterDef
       provenance: Provenance        # the parameter's summary — origin, fetched_at, expiration
   ```

   The unit's window *is* `domain.axis(T).extent` — no second window field to drift. Both types are
   `store.py`-private (the lattice-privacy guard covers them).
4. **`assimilate(answer: CoverageSet)`** — the `Writable` signature narrows to the natural
   answer. For each record, for each parameter: `x/y` indices come from snapping the record's
   point onto the store grid via `grid.clip(Interval(p, p))` (the same containing-cell math as
   `quantize` — no parallel arithmetic), `z_key` from the record's Z cell; the unit is **replaced
   whole** — insert-or-overwrite, never merged. The store's contract is **one type**: a
   single-Coverage answer is normalized by the *caller* into a one-record group
   (`CoverageSet.of`, minted with its caller — [RFC 0014](./0014-20260808-reservoir-retention-pipeline.md)
   d.1) before `assimilate`; the store never branches on answer shape. This slice's tests
   construct groups directly. Retention housekeeping (decision 8) runs here. The narrowed
   protocol lives in `nodes/store.py` beside its sole realization (the boundary-table row above,
   2026-08-09) — `store.py` already imports `coverage.py`, so the signature needs no import
   gymnastics and `core.py` stays read-only.
5. **`project` is the holdings query, total over raw asks** (2026-08-09 pass 3 — the earlier
   pre-quantized precondition made the store the only Manifold whose `project` demanded an ask
   prepared by a sibling verb; the call-order coupling and its assert die here). Given any
   `Selection`, the store **translates the ask onto its boxes internally — the same `quantize`
   fold, self-called** — so lookup boxes and refill boxes agree by determinism: one pure fold
   over the same constructor facts, and a tick is a fixed point. Per asked parameter, the units
   at the translated cell indices (ticks snap via `grid.clip(Interval(tick, tick))` — the same
   containing-cell math as decisions 1/4); a `deferred` axis constrains nothing (every held
   `z_key`, the whole held window); a Z-identity member matches units whose `z_key` equals it
   (frozen value equality). The answer is a `CoverageSet` with **one `CoverageRecord` per unit**
   — no grouping; records may share a domain, since the carrier's only invariant is
   parameter-disjointness — each carrying `Uniform(unit.provenance)`. Asked-but-unheld parameters
   are **omitted**; a cold store answers an **empty `CoverageSet`**; **stale units are returned
   as data** — the store reads no clock for freshness, ever (the reader's policy, ADR-0006).
   Retention housekeeping (decision 8) runs here too, so an evicted unit is never answered.
6. **Plural matches under one ask are asserted away, not handled.** By fact 6 a point ask names
   one cell per spatial axis at every hop, and every v1 tap declares one Z per parameter — so one
   parameter matches at most one unit; two units of one parameter in a single answer would break
   the carrier's disjointness. The assert's comment names both triggers that would make it real:
   a genuinely span-shaped ask (a grid consumer whose member carries several ticks), and a source
   declaring one parameter at two Z cells under an `ANY`-Z ask (then the answer becomes per-cell
   projection or a carrier extension — the `Reservoir`'s side, not the store's).
7. **`capability` narrates holdings** ([#47](../../concerns.md#47-a-stores-capability-narrates-plural-holdings-truncate-to-one-reach),
   this align): a `GranularCapability` — honest parameter membership; per-parameter reach = the
   **latest-assimilated** unit's domain, defined as the held unit with the newest
   `provenance.fetched_at` (ties break arbitrarily but stably; recomputed on read, so eviction
   can never leave the narration pointing at a dropped unit). Plural holdings truncate to one
   geometry — safe by fact 5 (no algebraic reader); the per-ask exact answer is `project`'s
   returned `CoverageSet.capability`. Empty store → empty parameters. No new capability form.
8. **Retention housekeeping**: on every `assimilate` and `project`, drop units whose
   `provenance.fetched_at + retention_interval < now` — the **one clock use**, substrate-private
   (the `MemoryStore` takes a `Clock` at construction for eviction only; the `Store` *contract*
   stays clockless — an archive substrate takes none). Eviction only removes; it never affects
   what `project` would answer for surviving units, which is the "never answers evicted"
   criterion.
9. **`quantize`'s one public job is the refill fetch-order.** `project` translates raw asks
   itself (decision 5), so the only caller who ever *needs* the box shape is the `Reservoir`
   authoring the refill ask for the *child* (next slice) — the ask's `ANY` axes are the mechanism
   that makes the provider answer natively (ADR-0006: "the partition reaches the store because
   the question asks `ANY`"), and only the store knows its boxes. The `Reservoir` hands in a
   request and gets a fetch-order back, never seeing a lattice — no lattice type appears in any
   public signature, which is exactly what the privacy guard checks.
10. **`StoreFactory.create(spec, deferred)` returns
    `MemoryStore(grids, deferred, clock, retention)`, wired for real, inert by construction**
    (2026-08-09 pass 2 — the earlier "StubStore stays wired" contradicted this factory rewrite,
    since the Weaver calls the same factory). The **factory owns `StoreSpec` interpretation**:
    it derives the global X/Y lattices (decision 2) and validates the step, then hands the store
    *prepared* grids — which is what keeps the store role-agnostic and the inverted instantiation
    constructible (pass 4; a store deriving its own grids from `spatial_step` would hardcode the
    spatial roles the genericity criterion forbids).
    `deferred: frozenset[AxisName]` is **position-bounded, producer-decided**
    ([ADR-0006](../../adr/0006-materialization-granularity-and-store-shape.md) as amended
    2026-08-09; the Weaver owns *where*): `{T}` at the root and the stored-Calculator site is
    position-forced (product-shaped children — native cells are gone by relabel below), while
    the source set is the **provider shape's** fact — v1's one shape (point timeline) yields
    `{T, Z}`, kept as `wire_source`'s constant with a comment naming the shape as its owner (a
    second shape moves the value into the provider manifest; this signature doesn't change). The
    three `create` call sites pass it in this slice —
    `{T, Z}` at `wire_source`, `{T}` at the root and at the stored-Calculator site
    ([weaver.py:96](../../../src/meteoscape/nodes/weaver.py) — whose spec binding stays
    [#27](../../concerns.md#27-stored-calculator-store-binding)'s open question, untouched here). The
    factory takes the injected `Clock` at construction (ADR-0005; `server.py` supplies the one it
    already builds). Where `Z` is not deferred, the request's vantage cell passes identity through
    `quantize` and becomes the unit's `z_key`. **`StubStore` is deleted** along with its
    `TODO (temporary)`: the graph carries real `MemoryStore`s that today's pass-through
    `Reservoir.project` never reads or writes — "unit-tested, wired inert", and slice 4 then
    touches only the `Reservoir` and tests. **Known test ripple** (pass 4, so nothing surprises
    the implementer): `StubStore`'s direct construction in
    [test_core.py](../../../tests/deterministic/manifold/test_core.py) switches to `MemoryStore`;
    the `create` call sites in [test_arbiter.py](../../../tests/deterministic/nodes/test_arbiter.py)
    and the e2e fixture gain a `deferred` argument; `RecordingStoreFactory`
    ([fakes.py](../../../tests/deterministic/fakes.py)) records it — becoming the natural weaver
    assertion that each position derives its own `deferred`.

## Stages (each green)

Stages are landing milestones, not single red→green cycles: within each, work proceeds one
observable behavior → minimal implementation at a time per `/tdd`; the structural guards are
to-tickets' machine-enforced-constraint form, not behavior tests.

1. **quantize** — red: timeline-unit asks (ANY T/Z, containing X/Y cells emitted as tick
   members — non-cellular, the fixed-point re-quantize test: a tick quantizes to itself), an
   inverted grid-style store instantiation, outside-lattice decline, non-separable request
   refusal, boundary point reuses `clip`'s tolerance. Green: the method.
2. **assimilate + capability** — red: a `CoverageSet` lands as units keyed by native Z and grid
   cell; re-assimilation replaces whole units (one window per unit, single-origin — a spliced
   `valid_time` unrepresentable); capability narrates latest holdings, empty store → empty.
   Green: store core.
3. **project** — red: raw asks answered (a request and its own fetch-order select the same
   units — the translation-agreement test); held parameters answer on their native domains with
   provenance intact, stale included; unheld omitted; cold store → empty `CoverageSet`. Green:
   the holdings query.
4. **retention + factory + wiring + guard** — red: eviction on write and read, evicted units
   never answered; factory honors `StoreSpec`, validates the step, and builds per-position
   `deferred`; the lattice-privacy guard (static scan that no module outside `store.py` references
   its private unit/lattice types, same mechanism as `test_probe_seam_guard`). Green: the three
   Weaver/`wire_source` call sites pass `deferred`, `server.py` hands the factory its `Clock`,
   `StubStore` deleted — full suite green because the `Reservoir` never touches the store.

## Out of scope / follow-ups

- The `Reservoir` pipeline — the serve-vs-refetch gate (freshness against the `Reservoir`'s
  clock, covers-or-refetch-whole), refill, `CoverageSet.of`, read-back →
  [RFC 0014](./0014-20260808-reservoir-retention-pipeline.md).
- Nearest-neighbor read-back at exact off-grid points → [007](../../tickets/01-0117-off-grid-homogenization.md).
- Cross-window unit reuse → [#25](../../concerns.md#25-root-store-holding-reuse-across-vantage-windows).
- A plural-reach holdings advertisement → [#47](../../concerns.md#47-a-stores-capability-narrates-plural-holdings-truncate-to-one-reach),
  revisited at the first real reader (0195 observability, or #44's persisting/archive substrate —
  deliberately late release 02 or after).
