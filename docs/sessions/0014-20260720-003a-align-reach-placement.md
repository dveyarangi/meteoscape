# 0014 · 2026-07-20 · 003a align — reach: inner bound, selected, and moved off `Capability`

Align session on [ticket 003a](../tickets/done/003a-profile-reach.md). Two **reversals of session 0013**
landed, both driven by the same question — *what is reach actually for?* — and the answers produced a
new ADR, a renamed ticket, a new concern, and a smaller ticket than we started with.

The full rules live in **[ADR-0007](../adr/0007-reach-is-an-inner-bound.md)**; this record carries the
reasoning trail, the rejected positions, and what remains open.

## Starting position

Docs were in unusually good shape — `reach` was already specified across `architecture.md`, ADR-0004's
0013 amendment, concern #29, the glossary, `v1-requirements`, and both tickets. It appeared **nowhere
in `src/`**. So this was not doc repair; it was stress-testing a fully-specified contract before
building it.

The unlock was an early investigation question: **who actually consumes reach?** Answer — the MCP edge,
and only its `valid_time` upper bound (the omitted-`end` default window, and the tool-description
narration). Deferred consumers (introspection tool, backward reach) are also edge. **Nothing inside the
algebra reads it.** Both reversals follow from that fact.

## Reversal 1 — the per-axis fold → selection

0013 joined reach **per axis**: point axes (X/Y/Z) union, extent axis (`valid_time`) intersect —
"spatially an outer bound, temporally a guarantee".

Rejected, for reasons that compounded:

- **The spatial "union" was a convex hull.** Its own motivating example,
  `{Europe × 16 d, Americas × 10 d}`, produced a trans-Atlantic span *neither member serves*. #29
  defended this as *"harmless: it fails as an ordinary `capability-mismatch` at admission"* — a defence
  of **safety**, in the one place where **usefulness** is the entire requirement. A boundary a caller
  must guess inside is not a boundary.
- **The motivating example was a misconfiguration, not a product.** Disjoint regionals with no global
  fallback is a holed deployment. Designing semantics around it optimized for a broken case. The real
  topology is regional + global fallback, whose union collapses to the global footprint.
- **Per-axis folding is itself the error.** It drops inter-axis correlation — the very information that
  makes reach usable. The temporal intersection had the mirror defect: a narrow regional with a short
  horizon **amputated the global product's promise** (`{Europe × 16 d, Global × 10 d, Arctic × 5 d}`
  → 5 d, though every point is served 10 d). 0013 recorded that as *"conservative, accepted, not
  solved"* with a config lever parked as the fix. It was never an accepted cost — just an artifact.

**Replacement:** reach is an **inner bound** (*every point it names is servable*), obtained by
**selecting one producer's own `Domain`** — never synthesising one. Inner-boundedness then holds **by
construction**, and the representation is inherited, so a clock-anchored `RollingAxis` stays live with
no special handling.

### Trail through the intermediate positions (recorded so they are not re-proposed)

1. **`hull` vs `union` naming** — the first framing, treating the imprecision as a naming problem.
   Wrong altitude: the operation itself was wrong.
2. **Containment-supremum + T-intersect over spatially-dominant members** — better, but still described
   as a fold, and the "union over dominant members" claim was **degenerate**: since `S` is the
   supremum, any member ⊇ `S` must *equal* `S`, so the set is a singleton unless footprints tie
   exactly. Correctly called out as *"plain picking the one correct provider's shape"*.
3. **Synthesizing the maximal inscribed box** — rejected: non-unique in the motivating case
   (`Global × 10 d` and `Europe × 16 d` are both maximal), so it still needs a tie-break, and it
   discards the producer's representation for no gain.
4. **Tie-break by measure** (largest box by volume) — rejected: requires commensurating degrees²
   against days, and flips as providers change.

**Landed:** the `grid` reach rule — dominance on **X/Y** first, then the remaining axes, raise if
unresolved. Judging X/Y first is **load-bearing**, not a preference: `Global × 10 d` does not contain
`Europe × 16 d` as a whole box, so an all-axis test raises on the motivating case. That axis preference
is a **product judgment** (*spatial completeness beats forecast length*), which is why it lives inside a
**named rule in a slot** rather than in the composite.

**Corrected in the same session's verification pass: X/Y-first is the Arbiter site's procedure only.**
Once the Calculator case was folded into the same rule (plan-impl), applying X/Y-first there turned out
to **violate the inner bound**: with inputs `{Europe × 10 d, Global × 5 d}` it selects `Europe × 10 d`
though nothing past 5 d is servable — the winner's footprint is only servable where the *other* inputs
also serve, so the Calculator site requires **whole-box containment in every other input** (all axes at
once, no ordering). When that winner exists, it *is* the exact intersection — meaning the product
judgment exists **only at the Arbiter site**; the Calculator side is forced by the definition. The
raise therefore also covers *sheared* inputs, not just disjoint ones. Every example in the docs had
happened to dodge this because the discussed cases were Arbiter-side; the counterexample only appears
when the dominated direction meets asymmetric T horizons.

A second verification pass caught the complement: **equal-extent ties were unspecified**, and v1's
derived wind *is* the tie case on every parameter — `wind_u` / `wind_v` footprints are distinct
objects with equal extents (per-tap `FootprintDomain`s sharing X/Y/T axes), so a strict
"raise on non-unique" reading would fail every Calculator-bearing profile at composition. Resolved:
mutual containment means equal extents means the same promise, so **both sites take the first
candidate** on a tie — unlike the rejected `ProducerKey` tie-break, there is no incomparable choice
being hidden.

## Reversal 2 — `Capability` facet → build-time profile value

Triggered by two objections raised together, which turned out to be **one objection**:

- the `CompositionError` from a holed profile gave the operator no actionable hint;
- why carry a facet on every Manifold, with awkward implementations, when only the edge reads it?

The link: `UnionCapability.members` is `Sequence[Capability]`, and **capabilities carry no producer
identity** (`SourceKey` lives on `Producer`, one level up). A raise from inside a composite
**structurally cannot name what conflicts**. The bad error was a symptom of wrong placement.

**Landed:** reach is **profile-level**, resolved once at build —
`resolve_reach(ProfileDef) -> Mapping[ParameterId, Domain]`, called from `compose()`, **not** from
`Weaver.weave` (which stays a pure graph constructor). The **only** contract change is that a **leaf
capability publishes the footprint it interprets**.

What this bought beyond deleting three implementations:

- **The non-admission discipline became a fact.** "No admission path may consult `reach`" was a rule to
  obey; now reach is not reachable from the request path at all. This *restores* ADR-0004's original
  "enforced by omission" instinct, which 0013 abandoned only because no accessor existed.
- **Errors became actionable** — the resolver holds every candidate's `SourceKey` / `CalculatorKey`.
- **Build-time validation became a proof, not a smoke test.** An earlier draft had `weave` force
  `reach` per parameter, which was only a smoke test because T dominance is clock-anchored. Freezing
  the *selection* at build (while handing over the winner's live `Domain` object) removes that
  residual entirely.

## Terminology repair

0013 conflated two concepts under one word. Split, and both terms already existed:

- **Reach** — the *profile-level promise* the surface narrates. Selected from footprints.
- **Footprint** — a *producer's declaration*. The internal notion; what a runtime client would want.

`Footprint`'s glossary entry was circular ("a producer's declared … reach") and is fixed. **Reach rule**
added.

## Holes — the taxonomy pass

Established that a profile **is** allowed holes, but v1 provably cannot produce one:

- reach is **per-parameter**, so a `2 m` / `10 m` Z divergence is two single-cell reaches, not a gap;
- every v1 source is a **forecast grid** — holes come from observation- and archive-shaped sources;
- a footprint declares **reach, not resolution**, so anything the homogenization kernel fills
  ([#5](../concerns.md#5-read-time-homogenization-fidelity)) was never a hole.

Real holing products (all named extension points): station networks (X/Y point set + irregular T),
gapped grid archives (T), radar mosaics (X/Y edges), polar swaths (curvilinear X/Y, no Z hole).
**Disjoint regionals with no fallback** is a misconfiguration, not a product. `{Global × [0,16 d],
Global × [−2 d,10 d]}` (obs + forecast) raises under `grid` — **correctly**; it needs its own rule, and
one that handled it would be wrong for grids. That validated the slot as real rather than speculative.

**`dense_axes` rejected** as the config lever's shape: density is neither a per-axis boolean nor
independent of the request — a polar swath's X/Y is *curvilinear*, not sparse, and its answerability
depends on the caller issuing a **"fat" T request** spanning revisits. The lever's shape is left
deliberately unspecified in [#29](../concerns.md#29-narrated-reach-inner-bound-by-producer-selection);
its only permitted job is to **narrow candidates or assert an invariant**, never to declare reach
(a second source of truth that can drift from the members and lie to callers).

## Scope consequences for 003a

- **No geometry primitive at all** — this shrank in two steps. First union fell (selection replaced
  the fold), leaving `Interval.intersect -> Interval | None` for the Calculator case; then during
  plan-impl the Calculator case became **dominated-input selection** too (intersecting would
  synthesize a `Domain` and freeze its `RollingAxis` at build — a live defect for derived wind), and
  intersection fell as well. The resolver needs only extent *containment*, which `Interval.contains`
  already provides; `Domain.intersect` stays a declared seam.
- **[#22](../concerns.md#22-lattice-helpers-vs-domain--sampling-module-split) — no carve.** The ticket
  adds no geometry to `domain.py` and no consumer of the index arithmetic. Trigger untouched.
- **[#23](../concerns.md#23-spatial-vs-temporal-regularaxis-types) — no split.** Dominance is
  `contains`, which works on `float` and `datetime` without dispatch, and `Interval` is already
  generic over the constrained TypeVar `C: (float, datetime)`. **Zero new `isinstance` dispatch**, so
  #23 is neither compounded nor earned.
- **Dominance must not reuse `Domain.matches`** — that is the request-side *admission* predicate, which
  `VantageAxis` specialises to intersection. Hygiene, not a live bug (a `VantageAxis` is never a
  capability footprint axis).

## Docs updated

- **New:** [ADR-0007](../adr/0007-reach-is-an-inner-bound.md) — the rule, placement, slot, actionable-
  error constraint, consequences, and five rejected alternatives.
- **New:** [#32](../concerns.md#32-runtime-footprint-awareness-inside-the-algebra) — runtime
  footprint-awareness; [#33](../concerns.md#33-reach-rule-and-reconciler-mode-are-coupled) — reach rule
  ↔ reconciler coupling; [#34](../concerns.md#34-producer-dag-walking-is-duplicated) — duplicated
  producer-DAG walk.
- **ADR-0004** — 0013's reach amendment replaced by a pointer; Capability carries no reach, a leaf
  publishes its footprint.
- **`architecture.md`** — Capability contract surface split into **Capability** + a new **Reach**
  bullet; composition root gains `resolve_reach`; ADR + concern indexes.
- **`concerns.md` #29** — retitled *"Narrated reach: inner bound by producer selection"* (anchor
  repointed in 9 places); per-axis join and the conservative-T concession removed; config-lever shape
  and hole taxonomy added as open parts.
- **`glossary.md`** — **Reach** rewritten (profile-level), **Footprint** decircularised, **Reach rule**
  added, **Capability** no longer advertises reach.
- **`v1-requirements.md`**, **tickets/README.md**.
- **ticket 003a** — renamed `003a-capability-reach.md` → **`003a-profile-reach.md`**, retitled
  *"Profile reach"*; What-to-build and every AC rewritten.
- **ticket 003b** — consumes the build-time map; `compose()` wiring replaces the earlier weave-forcing
  draft.
- **`docs/sessions/0013-*`** left intact as history (links repointed only); ADR-0007 supersedes it.

## Open / continuation

- **The config lever's shape** — narrowing the candidate set (so a `Global × 10 d` fallback cannot cap a
  `Global-minus-poles × 16 d` primary). Deliberately unspecified;
  [#29](../concerns.md#29-narrated-reach-inner-bound-by-producer-selection) holds the constraints.
  No v1 driver.
- **A second reach rule** — obs+forecast and polar-swath compositions each need one, and the swath case
  is already known to constrain the **request's shape**, not merely axis dominance. That is why v1
  ships `grid` as a named unit with **no `ReachRule` protocol, no config, no registry** — freezing an
  interface on one implementation is [#28](../concerns.md#28-reconciler-interface-selection-ordering-vs-per-cell-fold)'s
  recorded mistake.
- **Reach rule ↔ reconciler coupling** ([#33](../concerns.md#33-reach-rule-and-reconciler-mode-are-coupled))
  — surfaced late in the session, from the question *"does reach follow priority?"*. It does not, but
  that is **`grid`'s choice, not a law**: the reconciler **bounds** what any reach rule may truthfully
  claim (a splicing reconciler serves what no single producer covers, so its reach is wider than
  selection can express — the same reason obs+forecast raises under `grid`), while the residual product
  judgment stays with the mode. Open whether the two collapse into one profile-mode declaration or the
  reach rule is derived from the reconciler. Same trigger as #28; no v1 pressure, since `priority` +
  `grid` agree by construction.
- **Runtime footprint-awareness** ([#32](../concerns.md#32-runtime-footprint-awareness-inside-the-algebra))
  — assessed this session as a **separate mechanism** from reach (one `Domain` vs an ordering; build-time
  vs per-request; raises vs ranks). Revisit putting footprint on `Capability` only when a real runtime
  consumer appears.
- **Location-blindness** — a static description states one number, but reach is a `Domain`. Selecting
  the spatially-dominant producer keeps this *safe* while understating where coverage is better (a
  Europe caller narrated 10 d may ask for and be served 16 d). The trigger for the deferred
  **capabilities-introspection tool**.
- **Not re-litigated, still standing from 0013:** one reach and no quality ladder (quality is a policy
  outcome the response reports via provenance, not a capability); per-parameter reach is never a
  request axis; membership past the edge is
  [#30](../concerns.md#30-response-membership-under-runtime-degraded-fallback).

**Next:** implement [003a](../tickets/done/003a-profile-reach.md) — now a smaller ticket than at session
start (one build-time function, one leaf accessor, `Interval.intersect`; no node changes), then
[003b](../tickets/003b-request-shaping.md) on top of it.
