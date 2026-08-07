# RFC 0013 · 2026-08-08 · The retentive timeline Store — implementation plan

Implementation plan for [the retentive timeline Store](../tickets/01-0115.0030-timeline-store.md)
(slice 3 of the [retentive store](../tickets/01-0115-retentive-store-freshness.md)). Resolves the
`assimilate` concrete shapes the align left tentative — this RFC is their durable home.

**Scope in one line:** `quantize` beside `ground`; a unit-granular `TimelineStore` with
covers-or-refetch-whole reporting and answer-slicing `assimilate`; the retentive `StoreFactory`.
Nothing wired — the `Reservoir` stays pass-through.

## Boundaries involved

| Boundary | Owner | What this does to it |
|---|---|---|
| `quantize` (`manifold/domain.py`, beside `ground`) | [ADR-0002 §grid alignment](../adr/0002-data-model.md), [ADR-0006](../adr/0006-materialization-granularity-and-store-shape.md) | Minted: the enclosing per-axis fold. Zero new index arithmetic ([#22](../concerns.md#22-lattice-helpers-vs-domain--sampling-module-split) stands down). |
| `Store` protocol / `StubStore` (`nodes/store.py`) | ADR-0006, [ADR-0005](../adr/0005-build-time-composition.md) | `TimelineStore` minted; `StoreFactory.create` honors `StoreSpec`; `StubStore` remains until the pipeline slice unwires it. |
| `Writable.assimilate` (`manifold/core.py`) | [ADR-0001](../adr/0001-manifold-algebra-and-composition.md) | Signature becomes `assimilate(answer: CoverageGroup)` — the store consumes the natural answer and slices inside. |
| Store lattice privacy | ADR-0006 | Guard test: no module outside `store.py` constructs a unit `Selection` or imports the lattice/unit types. |

## Facts that shape the implementation (verified 2026-08-08)

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

## Design decisions

1. **`quantize(request, onto, whole) -> SelectionDomain`**, beside `ground` — the same fold shape,
   enclosing where `ground` restricts:

   ```python
   def quantize(
       request: Domain,
       onto: Mapping[AxisName, Axis],      # the store's lattices (X/Y here); absent = no lattice
       whole: frozenset[AxisName],         # axes the unit defers to the producer (T, Z here)
   ) -> SelectionDomain:
       axes: dict[AxisName, SelectableAxis] = {}
       for name in AXIS_ORDER:
           member = request.axes[name]
           if name in whole:
               axes[name] = SnappedAxis(name, None)               # ANY
           elif (lattice := onto.get(name)) is not None:
               cells = lattice.clip(member.extent)                # containing cell(s); clip owns the math
               if cells is None:
                   raise ValueError(f"request {name.value} is outside the store lattice")
               axes[name] = cells                                 # pinned RegularAxis member
           else:
               axes[name] = member                                # identity
       return SelectionDomain(axes=axes)
   ```

   The timeline store calls it with `onto={X: grid, Y: grid}`, `whole={T, Z}`; a grid store would
   invert the arguments — the fold itself is unit-agnostic (ticket criterion).
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
   indices of the quantized cell and `z_key` is the record's native Z cell (coordinate + bounds —
   hashable value identity). Value:

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
4. **`assimilate(answer: CoverageGroup)`** — the `Writable` signature narrows to the natural
   answer. For each record, for each parameter: `x/y` indices come from snapping the record's
   point onto the store grid via `grid.clip(Interval(p, p))` (the same containing-cell math as
   `quantize` — no parallel arithmetic), `z_key` from the record's Z cell; the unit is **replaced
   whole** — insert-or-overwrite, never merged. The store's contract is **one type**: a
   single-Coverage answer (the root's child, an Arbiter, answers single-domain) is normalized by
   the *caller* into a one-record group — `CoverageGroup.of(answer)`, a classmethod minted with the
   carrier — before `assimilate`; the store never branches on answer shape.
5. **The report is covers-or-refetch-whole made mechanical.**

   ```python
   def report(
       self,
       shape: SelectionDomain,
       over: Mapping[ParameterId, Interval[datetime]],   # required T coverage per parameter
   ) -> Mapping[ParameterId, _Unit | None]:
   ```

   `over[p]` is **`request T bounds ∩ child reach(p)`** — computed by the *caller* (the
   `Reservoir`, next slice, is the only node holding both the request and `source.capability`);
   raw request bounds would be wrong (a request reaching past the child's current availability
   would report refetch forever, refetch, and still not cover). The store never reads a
   capability. Per requested parameter, over the quantized cell: the retained unit qualifies iff
   it exists, `provenance.expiration > now` (the store's own injected `Clock` — no `now`
   parameter), and its T extent ⊇ `over[p]`. Anything less → `None` → the parameter joins the
   refill set. No partial serve state exists — a unit is servable or refetched-whole, which is
   what makes a `valid_time` splice unrepresentable.
6. **`capability` = what it holds**: per-parameter reach assembled from qualifying units' domains
   (ADR-0007 shape); empty store → empty parameters (the `Reservoir`, next slice, treats that as
   all-miss — no special case here).
7. **Retention housekeeping**: on every `assimilate` and `report`, drop units whose
   `provenance.fetched_at + retention_interval < now`. Eviction only removes — it never affects
   what `report` would qualify (an evictable unit is stale-beyond-retention and would fail the
   freshness gate anyway), which is the "eviction never widens servability" criterion.
8. **The store's public face binds its privates.** The generic `quantize` fold lives beside
   `ground`, but the *store* exposes `quantize(request: Domain) -> SelectionDomain`, calling the
   fold with its private lattices and deferred axes — the `Reservoir` (next slice) hands in a
   request and gets a store shape back, never seeing a lattice. Same for `report`. This is what
   the lattice-privacy guard enforces.
9. **`StoreFactory.create(spec, deferred)` returns `TimelineStore(spec, clock, deferred)`** —
   `deferred: frozenset[AxisName]` is the position-derived unit fact
   ([ADR-0006](../adr/0006-materialization-granularity-and-store-shape.md), the fact→product
   boundary; the Weaver owns *where*): `{T, Z}` at a Source; `{T}` at the root **and at a stored
   Calculator's store** ([weaver.py:96](../../src/meteoscape/nodes/weaver.py) — the third call
   site, whose child likewise answers product-shaped views; its spec binding stays
   [#27](../concerns.md#27-stored-calculator-store-binding)'s open question, untouched here). The
   factory gains the injected `Clock` at construction (ADR-0005). Where `Z` is not deferred, the
   request's vantage cell passes identity through `quantize` and becomes the unit's `z_key`.
   `StubStore` stays in place for the wired graph until the pipeline slice.

## Stages (each green)

Stages are landing milestones, not single red→green cycles: within each, work proceeds one
observable behavior → minimal implementation at a time per `/tdd`; the structural guards are
to-tickets' machine-enforced-constraint form, not behavior tests.

1. **quantize** — red: timeline-unit asks (ANY T/Z, pinned containing X/Y), inverted grid-style
   unit, outside-lattice decline, boundary point reuses `clip`'s tolerance. Green: the fold.
2. **assimilate + capability** — red: a `CoverageGroup` lands as units keyed by native Z and grid
   cell; re-assimilation replaces whole units; capability reflects holdings. Green: store core.
3. **report** — red: fresh serve / stale refetch (mocked expirations), covers vs extension vs
   disjoint, no-splice invariant (post-refetch single window). Green: the gate.
4. **retention + factory + guard** — red: eviction semantics; factory honors `StoreSpec`; the
   lattice-privacy guard (static import/constructor scan, same mechanism as
   `test_probe_seam_guard`). Green: close out.

## Out of scope / follow-ups

- Serving through `Reservoir.project`, wiring, and the read-back relabel → RFC 0014.
- Nearest-neighbor read-back at exact off-grid points → [007](../tickets/01-0117-off-grid-homogenization.md).
- Cross-window unit reuse → [#25](../concerns.md#25-root-store-unit-reuse-across-vantage-windows).
