# m4 — Snapped request mode (T instantiation)

- **Status:** Ready (maintenance) — **design tentative**: the sketch below awaits its own
  align/RFC before implementation.
- **Depends on:** [003b — Capability carries its domain](./done/003b-capability-domain.md) (reach
  on the `Capability`), [m3](./done/m3-provider-parity-checks.md) (parity harness guards the
  provider change), both done.
- **Blocks:** [003c — Request shaping](./003c-request-shaping.md) — its window semantics ride this
  mode instead of edge-side clamping.
- **Outcome:** the request path supports the **Snapped** mode
  [ADR-0002](../adr/0002-data-model.md) reserves — *"step fixed, anchor/extent open, resolvable
  against a declared grid"* — as **one generic axis member** (coordinate-generic, like
  `RegularAxis`), **instantiated on T only**: "serve whatever you have within these bounds" is
  resolved **at the authority** (the producer, against its live window), not simulated at the
  edge. One mechanism; per-axis enablement is drivers-and-invariants, not new algebra (see Out of
  scope).

## Why

003c's align (2026-07-25) adopted relaxed window semantics: a caller's out-of-range bounds should
yield the servable part, not an error. Three adversarial review passes over the edge-side
implementation (clamping) each found real holes — a clock-race producing spurious
`capability-mismatch`, ordering rules that survived only per input-type, vendor-clamp failure
modes, degenerate folds — and every one of them lived in code *simulating* at the edge what the
algebra already reserves a mode for. The Snapped mode's resolution law
(`snapped → exact = step(request) ⊕ anchor(grid) ⊕ bounds(request)`, ADR-0002) is designed and
unbuilt; [006](./006-retentive-store-freshness.md)'s store `quantize` depends on sibling
machinery ("only a regular axis can be snapped-to"). Building the mode once replaces the
simulation and retires its failure class.

Maintenance, not product: the MCP surface is unchanged until 003c consumes the mode; the
deterministic and parity suites must stay green throughout.

## Open issue (what the align must settle)

How a **Snapped-T** request is represented, admitted, and resolved on the request path — and the
consequences for admission semantics ([#13](../concerns.md#13-candidate-admission-containment-vs-intersection):
intersection on a snapped axis vs the containment rule the enumerable mode keeps), for the
response's lattice authority (the winner's anchor, not the edge's), and for what the cadence model
still owes (fetch bounds + freshness/run identity — no longer a promised response extent).

## Tentative sketch (awaiting revision — not a plan)

- **Axis member:** one **generic** snapped axis carrying `step` and caller `bounds`, the **upper
  end optionally open** (an omitted `end` → unbounded: "as far as you go"). An omitted `start` is
  **not** open — the edge authors it at `floor(now)` (003c's "begin now" default is surface
  policy, not mode semantics; an open lower bound would silently serve from the run anchor).
  **Bounds carry cell-containment pre-applied on the lower side**: the edge floors the `start`
  bound to the step (so the tick whose cell contains the stated instant survives resolution, even
  against a foreign anchor), while the `end` bound stays the raw instant ("last tick ≤ end" makes
  end-inclusivity fall out at resolution). Anchor and count deliberately absent; coordinate-generic
  like `RegularAxis` (`float | datetime` — the
  [#23](../concerns.md#23-spatial-vs-temporal-regularaxis-types) split pressure applies to it
  equally). Name and exact shape open.
- **Admission:** mode-dependent `matches` — a snapped axis admits by **non-empty intersection**
  with the declared window (`VantageAxis` precedent for intersective `matches`); enumerable
  requests keep containment. A scoped, mode-local v1 position on #13 — single winner, wholesale,
  no per-cell fold, no `valid_time` splicing.
- **Resolution:** the winning producer resolves `bounds ∩ its live window` onto **its own** hourly
  anchor and derives the answer lattice **from the vendor response** (no promised count — shorter
  vendor data is an honest shorter answer; the vendor is the authority on what exists).
  **Mode-scoped, per shape-correspondence (clarified 2026-07-25):** the leaf's assembly branches
  on the request mode, both branches strict. *Enumerable* requests keep the existing length
  assertion against `sel.domain` unchanged — that path stays load-bearing (006's store refill
  hands the leaf enumerable store shapes; tests and future surfaces likewise), and closed
  projection for enumerable selections is untouched. *Snapped* requests replace it with coherence
  validation of the response's own claim: regular hourly ticks on one anchor, within the requested
  bounds, arrays consistent (the [#31](../concerns.md#31-positional-alignment-is-asserted-never-checked)
  check class re-aimed at the answer) — the vendor decides what exists, never whether the answer
  is well-formed; garbage or gapped series stay a loud `RuntimeFailure`.
- **Empty intersection:** no producer intersects → `capability-mismatch` (admission's answer, as
  today).
- **Shape-correspondence** (ADR-0001) already states the contract: the answer mirrors the
  question's mode — an enumerable answer to a snapped question, on the resolver's lattice.
- **Non-duplication constraints (clarified 2026-07-25)** — what keeps the X/Y instantiation a
  wiring change:
  1. *Snap arithmetic has one home*: the thin `lattice.py`
     [#22](../concerns.md#22-lattice-helpers-vs-domain--sampling-module-split) reserved for its
     "third consumer" — snapped resolution is that consumer. Align-to-step, offset, and count
     live there once. **[#23](../concerns.md#23-spatial-vs-temporal-regularaxis-types) resolves as
     this ticket's stage 0** (decided 2026-07-25): its recorded trigger — "additive when the axis
     surface is next touched" — is firing, so the spatial/temporal axis-type split lands as a
     pure suite-green refactor *before* the snapped member is minted. Consequences: dispatch is
     structural (no `isinstance` crawl), the carved helpers land on their final foundation once,
     and m4 builds **only exact temporal math** — the float-tolerance spatial-snap half is
     deferred to the X/Y driver as a *missing type*, not dead branches.
  2. *Admission and resolution are per-axis folds, mode-dispatched by axis kind* — the existing
     `matches` per-axis-gate pattern (`VantageAxis` precedent) mirrored on the resolution side:
     enumerable axes pass through, snapped axes resolve, vantage as today. Mode combinations are
     never code paths — they are axes taking branches of one loop. Intersection reads only
     `.extent`, so rolling (T) vs static (X/Y) declared windows cost zero branches.
  3. *Response coherence is one generic per-axis check* — "coordinates form a regular
     step-lattice within the requested bounds" is the same predicate for vendor times and,
     later, vendor grid coordinates; the leaf's parser feeds it per-axis.
- **Cadence retreat:** `CadenceDef` keeps run identity, freshness, and fetch bounds; it stops
  implying an exact servable extent the edge must pre-compute.
- **No store dependency, no temporary bend (clarified 2026-07-25).** Snapped resolution targets
  *the resolver's own grid*, whichever node resolves — ADR-0002's snap law names "a declared
  grid", and store lattices are "private to the Store and **emergent per node**" (one instance,
  not the definition). Pre-006 the resolver is the **leaf**: a snapped request asks the provider
  to *resolve onto* its private vendor lattice, never to *declare* it — the lattice surfaces only
  in the answer's `Coverage.domain`, exactly ADR-0006's "domain lives only on the Coverage" (m2's
  closure of the declaration channel is untouched). Admission needs no lattice either
  (bounds ∩ continuous footprint window). The pass-through Reservoir forwards; when
  [006](./006-retentive-store-freshness.md) lands, its `quantize` — designed to consume snapped
  requests against the store lattice — inserts the store-side half between the same two points.
  This mode is the request-side counterpart of machinery 006 needs anyway; nothing temporary.

## Docs to sync (at landing, per the align's resolutions)

- [ADR-0002](../adr/0002-data-model.md) — clarify snapped resolution keeps
  `bounds(request) ∩ declared extent` (the intersective reading) and the open-ended-bounds form.
- [ADR-0004](../adr/0004-producer-resolution-and-capability.md) — admission language becomes
  mode-dependent (containment for enumerable, intersection for snapped).
- [#13](../concerns.md#13-candidate-admission-containment-vs-intersection) — record the scoped v1
  position; the general per-cell-fold widening stays open.
- [v1-requirements §Time axis](../v1-requirements.md) and
  [003c](./003c-request-shaping.md) — already carry the direction; firm the wording.
- [architecture.md](../architecture.md) — the Selection/mode sentence gains the snapped request
  example if needed.

## Acceptance criteria (draft — to be firmed at the align)

- [ ] Stage 0: the [#23](../concerns.md#23-spatial-vs-temporal-regularaxis-types) spatial/temporal
      axis-type split lands as a pure refactor — suite green, no design contract weakened (the m1
      bar) — before the snapped member exists.
- [ ] A Snapped-T Selection is representable, admitted by intersection, and resolved by the
      Open-Meteo leaf onto its own lattice from the live response.
- [ ] Enumerable requests behave exactly as before (mode coexistence; deterministic suite green
      unchanged).
- [ ] The parity check still passes against the live vendor **unchanged** (m4 is
      product-invisible: the MCP edge issues enumerable requests until 003c, and parity compares
      at the MCP payload — the engine is never a parity boundary, RFC 0007). The live snapped
      end-to-end validation is **003c's** landing run.
- [ ] No `valid_time` splicing: one winner serves the whole (possibly shorter) window,
      single-origin.
- [ ] **Non-duplication guard:** the design document can truthfully state — *"enabling snapped
      X/Y is: the edge constructs a snapped X/Y axis, and the Timeline-only invariant is lifted;
      zero new methods in providers, Arbiter, or resolution."* If that sentence is false, the
      shape is wrong and the align is not done.

## Out of scope

- 003c's surface work (parsing, narration, defaults) — rides this ticket, stays there.
- **Snapped X/Y — same member, deliberately not enabled**: its answer is a spatial **Grid**, and
  the v1 invariant is *"Timeline realization, no Grid output"*
  ([v1-requirements](../v1-requirements.md)) — off-grid points are answered at the requested point
  by read-time homogenization ([007](./007-off-grid-homogenization.md)), never by emitting the
  provider's grid. When the Grid-realization driver arrives (roadmap), enabling X/Y should be
  wiring over this ticket's generic member, not new algebra.
- Snapped Z — Z already has its own request modes (vantage / cell-addressing, ADR-0002).
- Store-lattice snapping (`quantize`) — [006](./006-retentive-store-freshness.md)'s.
- Coverage reconcilers / per-cell folds (#28) — untouched by the scoped #13 position.
