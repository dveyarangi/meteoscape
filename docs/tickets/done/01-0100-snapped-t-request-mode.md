# Snapped request mode (T instantiation)

**Legacy id:** m4 · **Kind:** Maintenance

- **Status:** Done (2026-08-04) — mode settled at the 2026-07-25 align (inverted to bounds-only;
  `SnappedAxis` / `SelectionDomain` named); resolution algebra settled at the 2026-07-26 review: one
  verb, `ground`, over one abstract axis operation, `clip`, so a leaf declares its geometry instead of
  carrying mode code — the property that keeps 011's second provider and 006's `quantize` from
  re-deriving the mode; scope widened at the 2026-08-02 align: stages 4–5 became an *extraction* — the
  leaf split into `TimelineProvider` (the shape, owning all algebra) and an injected `TimelineProbe`
  (the vendor, owning one request and one envelope parse) —
  [RFC 0009 decision 12](../../rfc/done/0009-20260725-m4-snapped-t-request-mode.md),
  [edge/provider.md](../../edge/provider.md). Landed with the engine e2e + divergence pin, the Probe
  seam guard (`test_probe_seam_guard.py`), live parity green unchanged, and the docs synchronized
  (ADR-0001/0002/0004, architecture, glossary, the edge record to `Normative`).
- **Plan:** [RFC 0009](../../rfc/done/0009-20260725-m4-snapped-t-request-mode.md).
- **Depends on:** [003b — Capability carries its domain](./01-0060-capability-domain.md) (reach
  on the `Capability`), [m3](./01-0080-provider-parity-checks.md) (parity harness guards the
  provider change), both done.
- **Blocks:** [003c — Request shaping](./01-0110-request-shaping.md) — its window semantics ride this
  mode instead of edge-side clamping.
- **Outcome:** the request path supports the **Snapped** mode
  [ADR-0002](../../adr/0002-data-model.md) reserves — *"bounds fixed, lattice open, resolved against
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
align) is designed and unbuilt; [006](../01-0115-retentive-store-freshness.md)'s store `quantize` depends on the same
axis machinery (restricting a declared lattice to requested bounds). Building the mode once replaces the
simulation and retires its failure class.

Maintenance, not product: the MCP surface is unchanged until 003c consumes the mode; the
deterministic and parity suites must stay green throughout.

## ~~Open issue~~ Settled (align 2026-07-25)

~~How a **Snapped-T** request is represented, admitted, and resolved on the request path~~ — all
settled below: representation is `SelectionDomain` carrying a `SnappedAxis`
([#13](../../concerns.md#13-candidate-admission-containment-vs-intersection)'s scoped position:
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
  [#30](../../concerns.md#30-response-membership-under-runtime-degraded-fallback)'s diverging-reach
  trigger, where an open end would serve the winner's own window instead of the reach-min fold.
  **No `step`, no anchor, no count**: the resolver's grid supplies
  anchor and step, so **cell-containment is the resolver's duty** — the tick whose cell contains a
  stated bound survives because the resolver floors the lower bound on *its own* lattice, and
  "last tick ≤ end" makes end-inclusivity fall out. ~~The edge pre-floors the lower bound~~ (dead
  with the inversion — it existed only because the request carried a step). **Hierarchy (decided
  2026-07-25; refined 2026-07-26):** non-enumerable, request-side, ~~a sibling of~~ **a subclass
  of** `ContinuousAxis` overriding only `matches` — **not** an
  `IntervalAxis` (it must never claim enumerability: no cells until resolved) and not a vantage
  (vantage answers on the asker's own cell; snapped on the resolver's lattice — they share only
  intersective `matches`). The refinement satisfies every constraint the align stated and adds
  none: `ContinuousAxis` is itself non-enumerable, so "never claims enumerability" is *inherited*
  rather than restated. It also makes the pair the documented dual of the one ADR-0002 already
  describes — *"`IntervalAxis` … the base of the request `VantageAxis` (which only overrides
  `matches`)"* — so the request-side aperture types are one family, cell-shaped and span-shaped,
  instead of two unrelated mintings. Consequences: the field is the inherited **`interval`**
  (a frozen subclass cannot rename one; "bounds" stays the prose term, as "aperture" does for
  `VantageAxis`), and `isinstance(x, ContinuousAxis)` is now true for a snapped axis — verified
  harmless, no production code dispatches on it. Minted **temporal-only**, and the subclass makes
  that **statically** enforced (`interval: Interval[datetime]` narrows the base field; verified
  under the project's `pyright`) rather than a runtime check; the spatial sibling is a missing type
  for the Grid-realization driver. Named **`SnappedAxis`** (decided 2026-07-25).
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
- **Resolution is one verb, not a mode branch (settled 2026-07-26).** A request resolves against a
  node's geometry by **`ground`ing** on it: pinned axes pass through, a snapped axis adopts the
  answering lattice clipped to its bounds (`snapped → exact = anchor(grid) ⊕ step(grid) ⊕
  bounds(request)`). The clipping itself is the answering axis's own business — **`Axis.clip(bounds)`,
  abstract on the base** (revised 2026-08-02), so `ground` asks one question and reads one answer. A
  leaf therefore **declares** a T that clips to a lattice — its rolling window at its native series
  step — and calls `ground` twice: against that declaration for fetch bounds, against the
  delivered records for the answer geometry, with the sampler cropping values to the result. Three
  consequences, each a decision:
  - **The vendor is the authority on what exists, never on whether the answer is well-formed.**
    Fewer ticks than the bounds asked for is an honest shorter answer; more is trimmed. Neither is an
    error, and no validation of the response's *own claim* exists — clipping settles the geometry,
    cropping settles the values. Garbage (gapped or non-hourly series, inconsistent array lengths)
    stays the normalizer's loud `RuntimeFailure`.
  - **Enumerable requests take the same path**, because grounding an exact request is the identity.
    The length assertion that guarded them becomes the crop's alignment check — the same fact, owned
    by the component doing the index math
    ([#31](../../concerns.md#31-positional-alignment-is-asserted-never-checked) re-aimed at the answer).
    006's store refill keeps handing the leaf enumerable shapes and keeps getting exact answers.
  - **`clip` joins the universal axis surface** (the ADR-0002 amendment; that base was set-algebra
    only), and **`ground` is a function over it** — callers hold a base `Domain` and must not branch on
    representation to learn whether resolution is needed, while *being a request* is a property of some
    representations only, so the one dispatch lives with the representations
    ([#42](../../concerns.md#42-two-request-representations-so-resolution-cannot-be-a-method) owns the
    end-state where the request side narrows to one type and this becomes a method again). Both of
    `ground`'s arguments are a `Domain` and its result an `EnumerableDomain`, so the same call serves a
    footprint, a delivered Coverage, and — at 006 —
    a store lattice. `clip` returns whatever the restriction leaves, and **`ground` is what requires
    cells**: a snapped member against an axis that clips to a span is the decline. That
    makes *"only a regular axis can be snapped-to"* a consequence of declarations rather than a rule
    the machinery enforces — and v1 serves no snapped X/Y for a narrower reason still, that
    `SnappedAxis` is temporal by type, so its bounds never meet a spatial axis (a *disjoint* decline,
    both at admission and at `ground`).
- **Empty intersection:** no producer intersects → `capability-mismatch` (admission's answer, as
  today). A **raced-empty** intersection at fetch — admission passed, then the window rolled past
  `bounds.upper` before the leaf computed fetch bounds — resolves as `capability-mismatch` too
  (the request *is* unservable now; same category, one guard).
- **Divergent winner domains (found at the 2026-07-26 `/plan-impl` pass; decided: record + pin).**
  The shipped profile already answers a mixed request from **two** winners — the Provider directly
  and the wind `Calculator`, which resolves through its own scoped Arbiter and issues a **second
  independent vendor fetch**. Enumerable requests cannot diverge (both assemble onto
  `selection.domain`); snapped ones can, because each answer's T axis derives from its own vendor
  response — so a window roll between the fetches, or a vendor length change, trips the Arbiter's
  closed-projection equality check and fails the whole request with `RuntimeFailure`. **This is not
  the deferred "second provider with diverging reach" case** — it is live today. m4 changes no
  Arbiter code and adds no per-cell fold: it pins the loud failure with a test, classifies it
  **Race** at [#40](../../concerns.md#40-composing-servable-requests-at-the-embedding-edge), and hands
  the judgement to [003c](./01-0110-request-shaping.md)'s landing, where the mode first becomes
  reachable from the edge ([006](../01-0115-retentive-store-freshness.md)'s retention collapses the
  second fetch and dissolves the common case).
- **Shape-correspondence** (ADR-0001) already states the contract: the answer mirrors the
  question's mode — an enumerable answer to a snapped question, on the resolver's lattice.
- **Non-duplication constraints (clarified 2026-07-25)** — what keeps the X/Y instantiation a
  wiring change:
  1. *One snap operation, in one place; still no stage 0* (revised 2026-07-26 — the align said "no
     new snap arithmetic at all"). The arithmetic does exist: it is `RegularAxis.clip`, and it is the
     **only** site with any — leaves, Arbiter, and admission have none, and admission stays interval
     intersection on `.extent`. It does **not** narrow on coordinate kind (revised 2026-08-02, when
     the arithmetic moved from the temporal-only `SnappedAxis` onto `RegularAxis`):
     `(bound − anchor) / step` is a `float` for `timedelta`s and floats alike, so one expression
     serves both. [#23](../../concerns.md#23-spatial-vs-temporal-regularaxis-types) is therefore left
     where it was; what a spatial user must settle is **float phase tolerance**, which m4's exact
     `timedelta` path never meets. It stays deferred for the reason that deferred it — as public
     sibling types it would double every request-facing axis kind, an embedding-vocabulary cost to
     settle first (kept internal via construction autodetection, or absorbed by facade builders —
     recorded at #23 / [#39](../../concerns.md#39-python-embedding-surface-and-public-failures)).
     [006](../01-0115-retentive-store-freshness.md)'s `quantize` remains the expected toucher of
     [#22](../../concerns.md#22-lattice-helpers-vs-domain--sampling-module-split) — untriggered, but now
     one site away, since `clip` joins `sub_lattice_offset` as lattice arithmetic in `domain.py`.
  2. *Admission and resolution are per-axis folds, mode-dispatched by axis kind* — the existing
     `matches` per-axis-gate pattern (`VantageAxis` precedent) mirrored on the resolution side by
     `ground`: enumerable axes pass through, snapped axes clip, vantage as today, and 006's `ANY`
     takes the answering axis whole. Mode combinations are never code paths — they are axes taking
     branches of one loop. Intersection reads only `.extent`, so rolling (T) vs static (X/Y) declared
     windows cost zero branches.
  3. *Resolution is one operation, not a check per shape* — the same per-axis fold serves vendor
     times now and vendor grid coordinates later, so a new provider adds a **declaration**, never a
     branch. What the align called "one generic coherence check" is dissolved rather than shared:
     once the answer is clipped and cropped, there is nothing left to check.
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
  [006](../01-0115-retentive-store-freshness.md) lands, its `quantize` — designed to consume snapped
  requests against the store lattice — inserts the store-side half between the same two points.
  This mode is the request-side counterpart of machinery 006 needs anyway; nothing temporary.

## Docs to sync (at landing, per the align's resolutions)

- [ADR-0002](../../adr/0002-data-model.md) — ~~clarify snapped resolution keeps
  `bounds(request) ∩ declared extent` (the intersective reading) and the open-ended-bounds form.~~
  **Done at the align (2026-07-25):** the mode definition inverted to bounds-only (grid supplies
  anchor + step; law `snapped → exact = anchor(grid) ⊕ step(grid) ⊕ bounds(request)`;
  resolver-side cell containment), the "internal nodes are never handed Snapped" rule narrowed to
  store-refill Selections, and the stale step-carrying wording swept from v1-requirements, 003c,
  concerns #23/#30, ADR-0006, and the glossary (new *Snapped* entry). Remaining at landing: the
  `SelectionDomain` / `SelectableAxis` representation (answers grounded from requests, never the
  request object reused), **the axis-paragraph clause** pairing `ContinuousAxis` → `SnappedAxis`
  beside the existing `IntervalAxis` → `VantageAxis` one, **`clip` in the universal axis surface**
  (that base was set-algebra only — the recorded-decision amendment this ticket carries) with `ground`
  as the function over it and
  [#42](../../concerns.md#42-two-request-representations-so-resolution-cannot-be-a-method) as the
  condition for making it a method, and *"only a regular axis can be snapped-to"*
  **restated as a consequence** of what an axis clips to (same restatement in
  [architecture §Request modes](../../architecture.md#request-modes)'s Z bullet: no axis kind declares
  irregular native levels, so nothing there clips to cells).
  Open-ended bounds are **deferred** (#30's diverging-reach trigger), not part of this landing.
- [ADR-0001](../../adr/0001-manifold-algebra-and-composition.md) — the shape-correspondence paragraph
  names the operation that computes it (`ground`). **At landing.**
- [006](../01-0115-retentive-store-freshness.md) — its open store-lattice question closes on
  `Axis.clip` (*narrow what `quantize` requires*: one bounds question the retention grid answers,
  never enumeration), and `quantize` is restated as `ground`'s store-side sibling. **At landing.**
- [#21](../../concerns.md#21-serves-extent-vs-project-crop-ability) narrows to the off-phase case alone
  (the sampler now distinguishes a shortfall from an unimplementable crop);
  [#30](../../concerns.md#30-response-membership-under-runtime-degraded-fallback) gains the named
  padding site (the shortfall tail, as `present=False` with `nan` values);
  [#23](../../concerns.md#23-spatial-vs-temporal-regularaxis-types) records that this ticket adds **no**
  coordinate-kind narrowing and that the spatial case costs a float phase-tolerance decision.
  **At landing.**
- [#42](../../concerns.md#42-two-request-representations-so-resolution-cannot-be-a-method) — **opened
  2026-08-03:** the request side has two representations, which is why `ground` takes the request
  instead of being a method on it; the end-state and its triggers (006, 003c, an embedder-facing
  builder) live there, and both those tickets carry the pointer. Nothing further at landing.
- [glossary](../../glossary.md) — *Ground* (disambiguated from the vertical datum) and *Clip*.
  **At landing.**
- [ADR-0004](../../adr/0004-producer-resolution-and-capability.md) — admission language becomes
  mode-dependent (containment for enumerable, intersection for snapped). **At landing.**
- [#13](../../concerns.md#13-candidate-admission-containment-vs-intersection) — record the scoped v1
  position; the general per-cell-fold widening stays open. **At landing.**
- [v1-requirements §Time axis](../../v1-requirements.md) and
  [003c](./01-0110-request-shaping.md) — **done at the align (2026-07-25):** bounds-only wording,
  raw-instant bounds, resolver-side cell containment, reach-filled default `end`.
- [architecture.md](../../architecture.md) — ~~the Selection/mode sentence gains the snapped request
  example if needed.~~ **Done at the align (2026-07-25):** a §Request modes section (mode = the
  caller's knowledge of the answering lattice; per-axis use-case registry — snapped X/Y reserved
  for Grid realization, snapped Z structurally inapplicable), and the two stale
  "snapped requires a storing target" lines corrected to "the resolver's own private lattice".
  Glossary *Selection mode* carries the knowledge-state framing.

## Acceptance criteria (firmed at the 2026-07-25 align)

- [x] A Snapped-T Selection is representable, admitted by intersection, and resolved by the
      Open-Meteo leaf onto its own lattice from the live response.
- [x] Enumerable requests behave exactly as before (mode coexistence; deterministic suite green
      unchanged).
- [x] The parity check still passes against the live vendor **unchanged** (m4 is
      product-invisible: the MCP edge issues enumerable requests until 003c, and parity compares
      at the MCP payload — the engine is never a parity boundary, RFC 0007). The live snapped
      end-to-end validation is **003c's** landing run.
- [x] No `valid_time` splicing: one winner serves the whole (possibly shorter) window,
      single-origin.
- [x] **The leaf carries no snapped-mode code** — no mode branch, no lattice arithmetic, no
      `SnappedAxis` import: a geometry declaration and `ground` calls. This is the property
      [011](../01-0120-twc-provider.md) and [006](../01-0115-retentive-store-freshness.md) inherit;
      if it is false, the algebra is in the wrong place.
- [x] **Non-duplication guard:** the design document can truthfully state — *"enabling snapped
      X/Y is: declare an enumerable X/Y geometry, settle float phase tolerance in `RegularAxis.clip`,
      and lift the Timeline-only invariant; zero new methods in providers, Arbiter, or resolution."* If that sentence is false, the shape is wrong and the align is not
      done.

## Out of scope

- 003c's surface work (parsing, narration, defaults) — rides this ticket, stays there.
- **Snapped X/Y — same pattern (a spatial sibling type), deliberately not minted**: its answer is
  a spatial **Grid**, and the v1 invariant is *"Timeline realization, no Grid output"*
  ([v1-requirements](../../v1-requirements.md)) — off-grid points are answered at the requested point
  by read-time homogenization ([007](../01-0117-off-grid-homogenization.md)), never by emitting the
  provider's grid. When the Grid-realization driver arrives (roadmap), enabling X/Y should be
  the sibling type plus edge wiring over this ticket's pattern, not new algebra.
- Snapped Z — Z already has its own request modes (vantage / cell-addressing, ADR-0002).
- Store-lattice snapping (`quantize`) — [006](../01-0115-retentive-store-freshness.md)'s.
- Coverage reconcilers / per-cell folds (#28) — untouched by the scoped #13 position.
- **A second provider *shape*** — the `TimelineProvider` / `TimelineProbe` split lands for the
  timeline family only. Gridded NWP and soundings stay the deferred seam `timeline.py` already names;
  they add a wrapper, not a Probe.
- **Elevating parity's `ReferenceTimeline` into `src`** — deliberately not done: `parity.comparison`
  imports no Meteoscape code so readers stay guard-clean, and `TimelineDelivery` is its structural
  twin by design, never its shared type.
