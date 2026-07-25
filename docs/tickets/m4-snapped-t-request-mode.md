# m4 — Snapped request mode (T instantiation)

- **Status:** Ready (maintenance) — **design settled at the 2026-07-25 align** (mode inverted to
  bounds-only; `SnappedAxis` / `SelectionDomain` named; stage 0 deferred).
- **Plan:** [RFC 0009](../rfc/0009-20260725-m4-snapped-t-request-mode.md).
- **Depends on:** [003b — Capability carries its domain](./done/003b-capability-domain.md) (reach
  on the `Capability`), [m3](./done/m3-provider-parity-checks.md) (parity harness guards the
  provider change), both done.
- **Blocks:** [003c — Request shaping](./003c-request-shaping.md) — its window semantics ride this
  mode instead of edge-side clamping.
- **Outcome:** the request path supports the **Snapped** mode
  [ADR-0002](../adr/0002-data-model.md) reserves — *"bounds fixed, lattice open, resolved against
  a declared grid"* (**definition inverted at the 2026-07-25 align**: the request fixes **only
  bounds**; the resolver's grid supplies anchor **and** step — no product case needed the former
  step-carrying form, and the driver product needs this one) — as **one bounds-only axis member**
  (a per-axis pattern), **instantiated on T only**: "serve whatever you have within these bounds"
  is resolved **at the authority** (the producer, against its live window), not simulated at the
  edge. One mechanism; per-axis enablement is drivers-and-invariants, not new algebra (see Out of
  scope).

## Why

003c's align (2026-07-25) adopted relaxed window semantics: a caller's out-of-range bounds should
yield the servable part, not an error. Three adversarial review passes over the edge-side
implementation (clamping) each found real holes — a clock-race producing spurious
`capability-mismatch`, ordering rules that survived only per input-type, vendor-clamp failure
modes, degenerate folds — and every one of them lived in code *simulating* at the edge what the
algebra already reserves a mode for. The Snapped mode's resolution law
(`snapped → exact = anchor(grid) ⊕ step(grid) ⊕ bounds(request)`, ADR-0002 as amended at this
align) is designed and unbuilt; [006](./006-retentive-store-freshness.md)'s store `quantize` depends on sibling
machinery ("only a regular axis can be snapped-to"). Building the mode once replaces the
simulation and retires its failure class.

Maintenance, not product: the MCP surface is unchanged until 003c consumes the mode; the
deterministic and parity suites must stay green throughout.

## ~~Open issue~~ Settled (align 2026-07-25)

~~How a **Snapped-T** request is represented, admitted, and resolved on the request path~~ — all
settled below: representation is `SelectionDomain` carrying a `SnappedAxis`
([#13](../concerns.md#13-candidate-admission-containment-vs-intersection)'s scoped position:
intersective admission, single winner wholesale), lattice authority is the winner's (anchor *and*
step — the mode inverted to bounds-only), and the cadence model owes fetch bounds +
freshness/run identity, never a promised response extent.

## Design (settled at the 2026-07-25 align)

- **Axis member (inverted, decided 2026-07-25):** one **bounds-only** snapped axis carrying caller
  `bounds` as **raw instants** — a closed `Interval[datetime]`, **no open ends** (decided
  2026-07-25): an omitted `end` is **edge policy, filled from the folded reach end** read live — a
  default *hint*, safe under staleness because resolution intersects (a stale hint trims, never
  faults — unlike the retired clamp, nothing depends on the read being exact); an omitted `start`
  is filled at `now` (003c's "begin now" default is likewise surface policy, not mode semantics).
  Open-endedness (`upper = None`, "as far as you go") is a **deferred additive form**; its hour is
  [#30](../concerns.md#30-response-membership-under-runtime-degraded-fallback)'s diverging-reach
  trigger, where an open end would serve the winner's own window instead of the reach-min fold.
  **No `step`, no anchor, no count**: the resolver's grid supplies
  anchor and step, so **cell-containment is the resolver's duty** — the tick whose cell contains a
  stated bound survives because the resolver floors the lower bound on *its own* lattice, and
  "last tick ≤ end" makes end-inclusivity fall out. ~~The edge pre-floors the lower bound~~ (dead
  with the inversion — it existed only because the request carried a step). **Hierarchy (decided
  2026-07-25):** non-enumerable, request-side, a sibling of `ContinuousAxis` — **not** an
  `IntervalAxis` (it must never claim enumerability: no cells until resolved) and not a vantage
  (vantage answers on the asker's own cell; snapped on the resolver's lattice — they share only
  intersective `matches`). Minted **temporal-only** (`Interval[datetime]` bounds); the spatial
  sibling is a missing type for the Grid-realization driver. Named **`SnappedAxis`** (decided
  2026-07-25).
- **Request Domain representation (decided 2026-07-25): `SelectionDomain`.** The request-side
  representation a surface or embedder composes from **`SelectableAxis`** members
  (`RegularAxis | VantageAxis | SnappedAxis`) — *structurally* separable (it exposes `axis()`,
  which is all admission's per-axis gate reads) but **never nominally narrowed**:
  `Selection.domain` stays the base `Domain` (ADR-0002 / #12 — a future non-separable request
  composition, e.g. a station list, arrives as a sibling representation or a widened
  `SelectionDomain` family, and total `matches` keeps uncomparable pairs a survivable `False`).
  Never enumerable as a type. The answer is **realized from** the request, not the request object
  reused: enumerable request axes pass through into the answer's `GridDomain` (the vantage Z cell
  exactly as today), a snapped T is replaced by the vendor-derived axis. `GridDomain` remains a
  legal *internal* Selection domain — 006's store refill hands the leaf enumerable store shapes —
  while `SelectionDomain` is the edge-authored form; the MCP edge migrates to it at 003c (m4 stays
  product-invisible).
- **Admission:** mode-dependent `matches` — a snapped axis admits by **non-empty intersection**
  with the declared window (`VantageAxis` precedent for intersective `matches`); enumerable
  requests keep containment. A scoped, mode-local v1 position on #13 — single winner, wholesale,
  no per-cell fold, no `valid_time` splicing.
- **Resolution:** the winning producer resolves `bounds ∩ its live window` onto **its own** hourly
  lattice (its anchor *and* step) and derives the answer lattice **from the vendor response** (no promised count — shorter
  vendor data is an honest shorter answer; the vendor is the authority on what exists).
  **Mode-scoped, per shape-correspondence (clarified 2026-07-25):** the leaf's assembly branches
  on the request mode, both branches strict. *Enumerable* requests keep the existing length
  assertion against `sel.domain` unchanged — that path stays load-bearing (006's store refill
  hands the leaf enumerable store shapes; tests and future surfaces likewise), and closed
  projection for enumerable selections is untouched. *Snapped* requests replace it with coherence
  validation of the response's own claim: ticks on one regular lattice — the winner's own (hourly
  for Open-Meteo, validated against its own claimed cadence, never a request step) — within the
  requested bounds, arrays consistent (the
  [#31](../concerns.md#31-positional-alignment-is-asserted-never-checked)
  check class re-aimed at the answer) — the vendor decides what exists, never whether the answer
  is well-formed; garbage or gapped series stay a loud `RuntimeFailure`.
- **Empty intersection:** no producer intersects → `capability-mismatch` (admission's answer, as
  today). A **raced-empty** intersection at fetch — admission passed, then the window rolled past
  `bounds.upper` before the leaf computed fetch bounds — resolves as `capability-mismatch` too
  (the request *is* unservable now; same category, one guard).
- **Shape-correspondence** (ADR-0001) already states the contract: the answer mirrors the
  question's mode — an enumerable answer to a snapped question, on the resolver's lattice.
- **Non-duplication constraints (clarified 2026-07-25)** — what keeps the X/Y instantiation a
  wiring change:
  1. *No new snap arithmetic, no stage 0* (final, 2026-07-25): the bounds-only member means
     admission is interval intersection on `.extent` and the answer lattice derives from the
     vendor response (the normalizer's existing regularity validation) — m4 adds **no
     align-to-step math** and never dispatches on coordinate kind. The
     [#23](../concerns.md#23-spatial-vs-temporal-regularaxis-types) spatial/temporal split was
     weighed as a stage 0 and **deferred**: as public sibling types it would double every
     request-facing axis kind — an embedding-vocabulary cost that must be settled first (split
     kept internal via construction autodetection, or absorbed by facade builders — recorded at
     #23 / [#39](../concerns.md#39-python-embedding-surface-and-public-failures)).
     [006](./006-retentive-store-freshness.md)'s `quantize` remains the expected toucher;
     [#22](../concerns.md#22-lattice-helpers-vs-domain--sampling-module-split) stays untriggered.
  2. *Admission and resolution are per-axis folds, mode-dispatched by axis kind* — the existing
     `matches` per-axis-gate pattern (`VantageAxis` precedent) mirrored on the resolution side:
     enumerable axes pass through, snapped axes resolve, vantage as today. Mode combinations are
     never code paths — they are axes taking branches of one loop. Intersection reads only
     `.extent`, so rolling (T) vs static (X/Y) declared windows cost zero branches.
  3. *Response coherence is one generic per-axis check* — "coordinates form a regular
     step-lattice within the requested bounds" is the same predicate for vendor times and,
     later, vendor grid coordinates; the leaf's parser feeds it per-axis.
- **Cadence retreat:** `CadenceDef` keeps run identity, freshness, and fetch bounds; it stops
  implying an exact servable extent the edge must pre-compute (the edge may still fill a default
  `end` from the live reach — a hint resolution trims, never a promised extent).
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

- [ADR-0002](../adr/0002-data-model.md) — ~~clarify snapped resolution keeps
  `bounds(request) ∩ declared extent` (the intersective reading) and the open-ended-bounds form.~~
  **Done at the align (2026-07-25):** the mode definition inverted to bounds-only (grid supplies
  anchor + step; law `snapped → exact = anchor(grid) ⊕ step(grid) ⊕ bounds(request)`;
  resolver-side cell containment), the "internal nodes are never handed Snapped" rule narrowed to
  store-refill Selections, and the stale step-carrying wording swept from v1-requirements, 003c,
  concerns #23/#30, ADR-0006, and the glossary (new *Snapped* entry). Remaining at landing: the
  `SelectionDomain` / `SelectableAxis` representation (answers realized from requests, never the
  request object reused); open-ended bounds are **deferred** (#30's diverging-reach trigger), not
  part of this landing.
- [ADR-0004](../adr/0004-producer-resolution-and-capability.md) — admission language becomes
  mode-dependent (containment for enumerable, intersection for snapped). **At landing.**
- [#13](../concerns.md#13-candidate-admission-containment-vs-intersection) — record the scoped v1
  position; the general per-cell-fold widening stays open. **At landing.**
- [v1-requirements §Time axis](../v1-requirements.md) and
  [003c](./003c-request-shaping.md) — **done at the align (2026-07-25):** bounds-only wording,
  raw-instant bounds, resolver-side cell containment, reach-filled default `end`.
- [architecture.md](../architecture.md) — ~~the Selection/mode sentence gains the snapped request
  example if needed.~~ **Done at the align (2026-07-25):** a §Request modes section (mode = the
  caller's knowledge of the answering lattice; per-axis use-case registry — snapped X/Y reserved
  for Grid realization, snapped Z structurally inapplicable), and the two stale
  "snapped requires a storing target" lines corrected to "the resolver's own private lattice".
  Glossary *Selection mode* carries the knowledge-state framing.

## Acceptance criteria (firmed at the 2026-07-25 align)

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
      X/Y is: mint the spatial sibling type, the edge constructs it, and the Timeline-only
      invariant is lifted; zero new methods in providers, Arbiter, or resolution."* If that
      sentence is false, the shape is wrong and the align is not done.

## Out of scope

- 003c's surface work (parsing, narration, defaults) — rides this ticket, stays there.
- **Snapped X/Y — same pattern (a spatial sibling type), deliberately not minted**: its answer is
  a spatial **Grid**, and the v1 invariant is *"Timeline realization, no Grid output"*
  ([v1-requirements](../v1-requirements.md)) — off-grid points are answered at the requested point
  by read-time homogenization ([007](./007-off-grid-homogenization.md)), never by emitting the
  provider's grid. When the Grid-realization driver arrives (roadmap), enabling X/Y should be
  the sibling type plus edge wiring over this ticket's pattern, not new algebra.
- Snapped Z — Z already has its own request modes (vantage / cell-addressing, ADR-0002).
- Store-lattice snapping (`quantize`) — [006](./006-retentive-store-freshness.md)'s.
- Coverage reconcilers / per-cell folds (#28) — untouched by the scoped #13 position.
