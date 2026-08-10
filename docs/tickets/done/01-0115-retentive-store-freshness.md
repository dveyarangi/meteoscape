# Retentive store and freshness

**Legacy id:** 006

- **Status:** Done — 2026-08-09 (all four slices landed). Moved ahead of
  [011 — TWC provider](../01-0120-twc-provider.md) on 2026-08-05 (003c's
  re-stage align): retention is the *mechanism* that collapses the mixed-request double fetch,
  whose divergence [003c](./01-0110-request-shaping.md) accepts for exactly one ticket on the
  strength of this ordering.
- **Depends on:** [002 — Core canonical parameters](./01-0030-core-5-parameters.md)
- **Outcome:** Fresh reuse, refill, and single-origin whole-unit replacement.
- **Split 2026-08-08 into four subtickets** (historical ticket sizes ran 40–230 code lines; this one
  projected ~750–1000 raw). This ticket remains the **decision record** and the union of acceptance
  criteria; each slice carries its own scope, budget, and criteria, lands green, and only the last
  changes observable behavior. **The split follows to-tickets' refactor-subticket rule** ("a
  refactor too large for one RFC splits into subtickets, one RFC per child; the parent's criteria
  state the end-state that only holds when all children land"), not its vertical-slice rule:
  slices 1–2 are refactors in that rule's exact form (behavior unchanged, suite green through the
  reshape, machine-enforced guards, dependents unblocked), slice 3 is the new leaf verifiable by
  its own tests, and slice 4 is the demoable exit that delivers the parent's behavior. A strictly
  vertical decomposition was examined and rejected: a thin end-to-end slice would have to retain
  request-shaped (flattened) units first — the exact per-fetch flatten ADR-0006 rejects — and then
  rework them; one undivided ticket (~750–1000 raw lines) fails the size rule this split was made
  under:
  1. [`ANY` as the boundless snapped member](./01-0115.0010-any-boundless-member.md) — **Done**
  2. [Multi-domain carrier and the timeline rework](./01-0115.0020-multidomain-carrier-timeline.md) — **Done**
  3. [The retentive timeline Store](./01-0115.0030-timeline-store.md) — **Done**
  4. [The Reservoir retention pipeline](./01-0115.0040-reservoir-retention-pipeline.md) — **Done**

## Parent PRD

`docs/v1-requirements.md`

## What to build

Replace the stub `Store` with the real **retentive in-memory `Store`** — a `Writable` Manifold with
**private per-axis lattices** (spatial from `StoreSpec`; T inherited from answers; no public
`domain` — [ADR-0006](../../adr/0006-materialization-granularity-and-store-shape.md)),
**unit-granular** (units `(parameter, per-axis cells, window)`; `assimilate` splits a native answer
into units), wired into **both** positions (each `Source` and the best view). `project` runs the
`Reservoir` pipeline (*amended 2026-08-09: the store-side report verb dissolved — the store's own
`project` is the holdings query over raw asks, and the gate is `Reservoir` policy over what it
returns*): **load holdings** (`store.project` on the raw request — the store translates onto its
boxes internally; held units return with their domains and provenance; unheld parameters omitted,
empty answer normal), gate as policy — a parameter refills when **absent**, **expired**
(`expiration <= now` off the record's provenance `summary` against the `Reservoir`'s injected
clock — fresh while `expiration > now`, [ADR-0003](../../adr/0003-provenance-and-origin.md); no
`is_current` operation exists, [ADR-0001](../../adr/0001-manifold-algebra-and-composition.md)), or — *where the request bounds T; a
boundless ask has no extent to cover, so freshness alone governs* — **not covering** the required
window — **refill the missing/stale parameters** from the child in **one** call
(`child.project(store.quantize(request))` — the store-authored fetch-order, `quantize`'s only
public use), `assimilate` (whole units replaced atomically), reload, then read-back: relabel
matched native cells onto the handed shape and crop to the request (the fact→product boundary).

**`quantize` is `ground`'s store-side sibling** ([RFC 0009](../../rfc/done/0009-20260725-m4-snapped-t-request-mode.md)) —
the same per-axis fold, enclosing where `ground` clips, delegating to `Axis.clip`: a latticed axis
(X/Y) resolves to the pinned **containing cells** (`clip` with a degenerate interval — a cellular
tick owns the span that follows it); an axis the unit defers to the producer (T and Z here) takes
**`ANY`**; anything else passes identity. **Which axes are `ANY` derives from the unit definition,
not hardcoded** — a grid store inverts it (X/Y whole, T celled) — so the `Reservoir` stays generic.
Read the request-side verb before writing this one to keep the siblings from diverging. `quantize`
writes **zero new index arithmetic**, so [#22](../../concerns.md#22-lattice-helpers-vs-domain--sampling-module-split)'s
`lattice.py` carve stands down (if raw index math appears after all, carve on the spot — pure
refactor) and [#23](../../concerns.md#23-spatial-vs-temporal-regularaxis-types)'s type split stays
deferred. What **is** 006's: the spatial snap is the first live float-lattice snap, so
`RegularAxis.clip` gains the float boundary tolerance — applied in **index space** (fraction of a
step), keeping `clip` one branch-free expression for both coordinate kinds — reconciled with
`LATTICE_TOLERANCE` as **one shared policy** (one constant derived from the other; pinned by a
boundary-point test; no second tolerance minted).

**Request vocabulary: `ANY`, as the boundless snapped member.**
`SnappedAxis.interval: Interval[datetime] | None`; the `SelectableAxis` union is unchanged —
bounded and open are one member kind differing only in bounds. The temporal narrowing bites only
when bounds are present (a bounded spatial snapped member stays a type error; a boundless member is
axis-generic and sits on Z). One-sided open bounds are **unrepresentable by construction**
(`Interval` requires both edges) until the "from X onward" form's own author
([011](../01-0120-twc-provider.md) / [004](../01-0121-second-provider-fallback.md))
changes the field type. An open member has no `extent` (clear error; no live caller reads a request
member's extent) and `matches` everything. The MCP edge **keeps its omitted-`end` flip** — that
flip *is* the fold of per-parameter reach ends into one shared answer window
([#30](../../concerns.md#30-response-membership-under-runtime-degraded-fallback)'s one-shape rule) —
and narration is untouched: the `Reservoir` forwards capability unchanged, so the horizon sentence
and the reach read stay honest under retention.

**Refill authors a `SelectionDomain`** — pinned X/Y cells plus boundless T/Z members; it cannot be
enumerable (`ANY` has no coordinate list). No request-side narrowing lands here; after this ticket
both in-tree request authors speak `SelectionDomain` and
[#42](../../concerns.md#42-two-request-representations-so-resolution-cannot-be-a-method)'s remaining
trigger is #39's request-composition helper.

**Native geometry survives the fetch.** `quantize`'s `ANY` on T/Z makes the Provider answer
**multi-domain** — temperature at 2 m beside wind at 10 m — instead of flattening onto one requested
Z, so units land keyed by **native** cells from a **single** vendor fetch. (A fully-enumerable ask
would force the flatten and destroy the cells; per-parameter-group asks would multiply vendor
traffic for data one call returns.)

**The carrier, and the fold beside it.** This ticket mints the multi-domain carrier: a `Manifold`
grouping single-domain Coverages, whose own `project` folds onto a fully enumerable Selection — the
retirement home of `_assemble`, which is how closure is preserved. `agreed_geometry`'s law (records
must agree on every *bounded* axis) is permanent; the licence to differ keys on **boundless**
members, which the fold validates while keeping its single return — records carry their own
domains and the carrier is built from them, so the differing resolutions have no reader. Fold and
carrier names are settled at implementation (both call sites are in the timeline wrapper this
ticket rewrites).

**Retire the eager folds — both facets.** `open_meteo.project`'s eager Z flatten (`_assemble`
applied at fetch) and the parameter crop at answer assembly (`_as_delivered` keeping only
`selection.parameters`) retire together — they are the same eager fold on different facets, and one
law replaces both: *the answer carries the provider's natural shape; the store absorbs it; the
serve crops.* ADR-0006's rejection of per-fetch flattening ("lossy on the data plane; the store
cannot answer availability honestly") becomes live here, because this is the ticket where anything
is retained at all.

**Refill scope: ask narrow, answer natural, store absorbs.** The ask names the missing/stale
*requested* parameters; the answer may carry the provider's **natural fetch unit** — wider than the
ask on the parameter facet, never narrower (ADR-0001's answer discipline gains that sentence when
this lands). Open-Meteo's natural unit is its whole offering — the same single variable-listed call
— so a cold mixed request's first fetch warms `wind_u`/`wind_v` and the Calculator's second
`Selection` hits the store: 003c's accepted divergence dissolves as a **leaf property**, with no
`Reservoir` knob and no config. A narrow-answering (per-variable-billed) provider re-accepts the
divergence for its own parameters as its economy choice →
[#43](../../concerns.md#43-narrow-answering-providers-re-open-mixed-request-run-divergence), decided
at the first billed provider (011). Single-cadence consequence: a source's units age together (one
`CadenceDef` ⇒ one fetch time, one expiration per trip), so per-parameter staleness divergence
never occurs live for Open-Meteo; the freshness check stays per-unit and generic (a future source
may carry per-parameter cadences), exercised with mocked expirations.

**Serve gate: covers-or-refetch-whole.** A unit serves from store only if it is fresh and its
retained window ⊇ the grounded request window; anything less (extension, disjoint, regrow)
refetches the **whole unit** — the refill ask is the store shape, `ANY` on T, so the trip lands the
provider's entire live timeline and the store then holds the full horizon — **replacing it
atomically**, old window discarded. One retained window per `(parameter, spatial-cell)` unit —
never two coexisting windows, never a retained-head + fresh-tail splice — and the serve crops every
parameter to the same grounded request window, so two T ranges in one response is unrepresentable.
Accepted cost: a disjoint-window request discards still-fresh data (requests slide forward with the
clock; the vendor cannot serve the past; splicing is the mixed-run risk this rule kills —
cross-vantage-window reuse stays parked at
[#25](../../concerns.md#25-root-store-holding-reuse-across-vantage-windows)). 0112's day-anchoring is
load-bearing for fresh reuse: a same-day full-horizon repeat grounds to the identical day-anchored
window and serves with no trip.

**`assimilate` consumes the answer, not a pre-sliced record.** The store slices it per parameter,
because only the store holds both halves of each unit `Selection` — `X/Y`+`T` from its private
lattice, the native cell from the answer. Having the `Reservoir` slice would leak the lattice out
of the store. *(Tentative — revisit the concrete shapes when building them here.)*

A separate **configurable retention interval** bounds memory (housekeeping only; the `Arbiter`
never serves stale entries — LRU declined). The store-lattice representation stays the `Store`'s
own business: its retention grid answers `Axis.clip` by materializing from the retention window at
the clock, the way `RollingAxis` does — no new axis kind
([ADR-0006](../../adr/0006-materialization-granularity-and-store-shape.md)). See
`docs/v1-requirements.md` (v1 invariants, Config & secrets) and `docs/architecture.md` (Reservoir,
Store).

The e2e's second-call **re-fetch assertion** (documenting no-retention, session 0010) flips here.

## Acceptance criteria

- [x] The retentive in-memory `Store` is wired into both positions (Source + best view) with its
      private per-axis lattices (identity on Z; unit keys carry the Z cell).
- [x] `quantize` asks **`ANY`** on the axes the unit spans wholly (v1 timeline store: `T` and `Z`),
      and the Provider answers **multi-domain** — units land keyed by **native** Z (2 m, 10 m,
      surface, `[0,TOA]`), not by the request's Z, from a **single** vendor fetch.
- [x] `assimilate` consumes the answer and slices it per parameter inside the store; no other node
      constructs a unit `Selection` or otherwise learns the store's lattice.
- [x] `open_meteo.project` no longer flattens eagerly; a request whose Z differs from a prior one
      **reuses** the stored native units rather than refetching.
- [x] A fully-fresh repeat request is served with **no** provider call.
- [x] Per-unit freshness is honored: a parameter with unexpired provenance serves with no trip while
      an expired one triggers refill (differing expirations **mocked** — a single-cadence source's
      units age together, so the live path never manufactures this state).
- [x] A stone-cold mixed request (direct parameters + calculator inputs) issues **one** vendor
      fetch: the answer carries the provider's natural fetch unit (whole offering for Open-Meteo),
      the store absorbs it, and the Calculator's input `Selection` is served from the store —
      same `issue_time` across all assembled parameters.
- [x] A temporal miss or window-extension refetches the **whole unit** single-origin
      (covers-or-refetch-whole: no `valid_time` splice, old window discarded, the refetched unit
      lands the provider's full live timeline).
- [x] The retention interval is configurable and only bounds memory (never serves stale).
- [x] Unit + mocked-transport integration tests cover fresh-serve, per-parameter refill (mocked
      expirations), and whole-unit single-origin refetch.

## User stories addressed

- User story 5
- User story 14
- User story 15
