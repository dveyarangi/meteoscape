# 003b — Capability carries its domain

- **Status:** Done
- **Depends on:** [003a — Profile reach](./003a-profile-reach.md) (landed — this reshapes it), [m1](./m1-type-contract-hygiene.md)
- **Blocks:** [003c — Request shaping](../003c-request-shaping.md), which consumes the reach it publishes
- **Owning decision:** [ADR-0007 — Capability carries its domain](../../adr/0007-capability-carries-its-domain.md)
- **Implementation plan:** [RFC 0005](../../rfc/done/0005-20260722-capability-reach.md)
- **Outcome:** `Capability.reach(parameter)` on the interface; a Manifold's Reach is its capability's
  Domain; the standalone reach resolver and its rule are gone.

## Parent PRD

`docs/v1-requirements.md` — this is the structural precondition for user story 10 (envelope narration),
delivered by [003c](../003c-request-shaping.md).

## Why now

003a landed a **separate build-time pass** that walks the producer DAG to compute geometry the
capability tree already composes, plus a `Provider.footprints` contract extension to feed it. Both are
artifacts of putting Reach outside the algebra. 003c would build the first consumer against that shape
and 004 would add a reconciler beside it, so the correction gets more expensive at every step — and the
current code is a worked example of the entity-and-contract sprawl this stage should be preventing.

**No behaviour changes** for any profile that composes today — the ADR's tightness argument is that
the two representations always described the same set. Three deliberate exceptions, all of which
turn a failure into a success or an unreachable check into a reachable one:

1. `compose()` gains the `validate_calculators` call the docs already assert (question 3 below), so
   wiring errors that were dead code become reachable operator-facing build failures.
2. A **single** producer whose footprint is non-separable (curvilinear) no longer fails the build.
   Separability is a precondition of *comparing* footprints per axis, and one candidate compares
   against nothing; the old rule checked it only because it had no better home for the guard. It also
   restores consistency — `serves` already admits such a leaf, so refusing to publish its reach would
   break the reach-equals-`serves` claim on day one. Two non-separable candidates still fail.
   Curvilinear geometry in the source role is a live seam
   ([#12](../../concerns.md#12-curvilinear-domains)).
3. Scoped resolvers stop composing parameters their Calculator does not consume (see the scoped-Arbiter
   bullet), so a profile the top-level Arbiter resolves is no longer rejected by a sub-graph.

## What to build

Design and rationale are [ADR-0007](../../adr/0007-capability-carries-its-domain.md) entire; this ticket
builds it.

- **`Capability` gains `reach(parameter: ParameterId) -> Domain`**, raising for a parameter it does not
  serve; `parameters` stays the sole membership authority. The member is named **`reach`**, not
  `domain`: `EnumerableCapability.domain` is a parameter-free field `CoverageRecord.domain`
  (result-`Countable`) forwards to, every glossary synonym for that field is `_Avoid_`-listed, and the
  glossary already names the per-parameter published Domain **Reach**. All four forms implement it —
  `FootprintCapability` (its declaration), `EnumerableCapability` (its one domain, after the membership
  check), `UnionCapability` (the dominating member), `DerivedCapability` (contained-in-all over inputs).
  `serves` **stays** and is unchanged. `EnumerableCapability.reach` **narrows covariantly** to
  `EnumerableDomain` — that form's reach *is* enumerable, `CoverageRecord.domain` already returns the
  narrow type, and the narrowing puts "materialized ⇒ enumerable reach" in the type where
  [m2](../m2-dissolve-node-countable.md)'s materialized-provider discriminator relies on it.
- **`Reconciler` gains a domain-composition member.** `PriorityReconciler` implements dominance-or-raise
  — `GridReachRule.reach`'s body, moved. **The `Arbiter` invokes it** — `Arbiter.__init__` calls
  `reconciler.compose_domains(...)` and hands the composed result to the `UnionCapability` it
  constructs, symmetric with `project` invoking `reconciler.select`. The reconciler owns the *rule*;
  the capability holds the *result*. `Reconciler`, `Producer`, `PriorityReconciler`, and
  `build_reconciler` all **stay in `nodes/arbiter.py`** — no import into `manifold/`, no cycle.
- **Composite capabilities carry `ProducerKey`s** so composition can name the conflicting producers and
  axis in its `CompositionError`. This is what made the previous "errors can't be actionable" objection
  real; it is resolved by construction, not by message text. `UnionCapability` keys its **members**;
  `DerivedCapability` carries the `CalculatorKey` it **is**, so the sheared-inputs message keeps naming
  its calculator (003a's `_contained_in_all` took that key as an argument; the capability has no other
  way to know it). `Calculator.__init__` widens to accept the key — the Weaver has `reg.key` at hand.
- **Composition is eager at construction**, so an incomparable profile fails at build. `Arbiter.capability`
  stops rebuilding a fresh `UnionCapability` on every access.
- **A scoped Arbiter declares its scope.** The Weaver passes the Calculator's input parameter set to
  the scoped `Arbiter`, which restricts both its index and its capability to it. Without this,
  eager composition composes parameters the Calculator never consumes — debris from taking whole
  producers — and a realistic profile fails to build: two disjoint regionals serving a complex
  parameter directly (ICON-D2 gusts over Europe, HRRR over the Americas) plus a Calculator deriving
  it from a global's basics. The top Arbiter resolves it (the Calculator dominates worldwide); the
  scoped resolver sees only the two regionals and raises, because **a Calculator is never in its own
  scope**. Restricting also restores the invariant that a Capability can answer `reach` for every
  parameter in `parameters`. The over-declaration is wrong today; 003b's eagerness is what exposes it.
- **Delete** `nodes/reach.py`'s `GridReachRule` and `resolve_reach`, and `Provider.footprints` (with
  its Open-Meteo and fake implementations). The geometry predicates — `_contains`, `_split`,
  `_incomparable`, and the separability precondition — are a **move, not a delete**: they land in
  `manifold/domain.py` beside `AXIS_ORDER`, where both consumers reach them downward
  (`DerivedCapability`'s contained-in-all in `manifold/capability.py`, dominance in
  `nodes/arbiter.py`'s `PriorityReconciler`). Their tests move with them.
- **Keep** `validate_calculators` — wiring and cycles, not geometry. It moves to
  `nodes/composition.py` and `compose()` gains the call to it before `weave` (question 3 below).

## Implementation questions

All five were opened as deliberately-unsettled placement questions (the ADR does not bind them) and
resolved in the 003b align session (0016):

1. ~~**Where `Reconciler` lives.**~~ **Resolved:** it stays in `nodes/arbiter.py`. The question assumed
   `UnionCapability` holds the reconciler and composes lazily; instead the **`Arbiter` invokes
   `compose_domains` at construction** and passes the result in — no `manifold → nodes` import, no
   `TYPE_CHECKING` escape, and `manifold/capability.py` stays pure algebra.
2. ~~**Where `build_reconciler` stays.**~~ **Resolved by the same decision:** protocol, factory, and
   `PriorityReconciler` all remain together in `nodes/arbiter.py`.
3. ~~**Where `validate_calculators` lives**~~ **Resolved: `nodes/composition.py`**, beside the
   binders — it validates the `ProfileDef` defined there and its one production caller already
   imports from there. (`CompositionError` itself moved to `errors.py` in implementation — a Tier-0
   leaf so `DerivedCapability` in `manifold/` can author its own sheared-inputs error; ratified in
   the post-implementation review, recorded in ADR-0007's consequences.) `nodes/reach.py` is deleted
   entirely (the geometry predicates having moved to `manifold/domain.py`); a surviving module named
   `reach` with no reach in it would invite the logic back. Its tests split by destination:
   predicates → `tests/manifold/test_domain.py`, composition rules → the capability/arbiter tests,
   wiring/cycles → `tests/nodes/test_composition.py`.
   **Corollary — wire the call:** `compose()` did **not** call `validate_calculators`, though
   `module-layout.md`, concern #34, and this ticket's own criterion all asserted it runs before
   `weave`. ~~003b adds the one-line call in `server.compose()`~~ **Amended in implementation,
   ratified in the post-implementation review:** the call is `weave`'s first step instead. The
   "Weaver stays a pure graph constructor" rationale for keeping it beside `weave` was already
   false — the Weaver owns the backstop cycle guard and raises `CompositionError` itself — while
   making it `weave`'s precondition guarantees no caller (production or test) can forget it.
4. ~~**Whether the domain composition member takes `parameter`.**~~ **Resolved: yes** —
   `compose_domains(parameter, candidates)`. Not for symmetry with `select`: composition is eager and
   per-parameter, so the raise site inside the reconciler is the only author of the whole error, and
   the operator needs to know *which parameter* sheared (`{icon, gfs}` can be incomparable for
   `precipitation` and fine for `temperature`). The argument is used, so the dilemma dissolves; it
   also leaves room for a `splice` reconciler whose composition legitimately reads the parameter.
5. ~~**`Provider.footprints` removal blast radius**~~ **Resolved — enumerated:** the abstract
   property on `Provider`, the Open-Meteo property (its `_build_footprints` **stays** — it builds the
   `FootprintCapability` declaration), and `FakeProvider.footprints` all go; readers switch to
   `capability.reach(pid)`; `CountableFakeProvider` merely inherits it (its reshaping is
   [m2](../m2-dissolve-node-countable.md)'s). Two calls inside the radius:
   - `test_provider_footprints_expose_capability_domains` is **rewritten, not deleted** — its
     same-objects / live-T assertions restate ADR-0007's liveness property at the leaf, through
     `capability.reach(pid)`; dropping it would silently shed leaf-level liveness coverage.
   - **`FootprintCapability.footprints` keeps its name** — it is the leaf's *declaration*
     (per-parameter Footprints in the glossary sense), not the published Reach, so the field stays
     honest and its test construction sites don't churn.

## Coordination with m2

[m2 — Dissolve node-`Countable`](../m2-dissolve-node-countable.md) follows this ticket and removes the
node-`Countable` facet (`Reservoir.domain`, `Store`'s `Countable`, `Weaver._source_grid`,
`CountableFakeProvider`'s independent `domain=`). This ticket must not deepen what m2 deletes: leave
`_source_grid` and the `Countable` isinstance sites untouched, and add no new reader of a node's
`domain`. Result-`Countable` (`Coverage` / `CoverageRecord`) is load-bearing and stays.

**The order is load-bearing, not just convenient.** `FakeProvider.footprints` asserts its capability is
a `FootprintCapability`, and `CountableFakeProvider` inherits that accessor. m2 makes that fake declare
an `EnumerableCapability`, which would break the inherited assert — so running m2 first creates a fake
whose capability form contradicts its own accessor. 003b deletes the accessor, so the contradiction
never exists. (Latent today: no test calls `.footprints` on a countable fake.)

**Why the two do not need co-designing:** `Reservoir.capability` forwards its child's, so when m2 stops
wrapping a materialized provider in a `Reservoir`, the Arbiter composes over the *same* capability
object either way. Every composition decision here — eager construction, scoped Arbiters, dominance —
is unaffected by m2's rewiring.

## Acceptance criteria

- [x] `Capability.reach(parameter)` exists on the protocol and on all four forms; raises for an unserved
      parameter; `parameters` remains the only membership authority. `EnumerableCapability.domain`
      keeps its name and shape (result-`Countable` forwards to it).
- [x] `serves` is unchanged in behaviour and still the sole admission authority.
- [x] A profile whose producers are incomparable for a parameter fails at **build** with a
      `CompositionError` naming the conflicting producers, the failing axis, **and the parameter** —
      the first two are the message quality 003a's tests already assert; the parameter is new,
      possible because eager composition puts the whole error in the reconciler's hands.
- [x] Composition returns an **existing** child `Domain`, never a synthesized one, so a clock-anchored
      `RollingAxis` stays live: a reach read after the clock advances reflects the new anchor.
- [x] Equal-extent ties return one of the candidates without raising (the derived-wind case).
- [x] `Arbiter.capability` is computed once, not per access.
- [x] A scoped Arbiter's `capability.parameters` is exactly its Calculator's inputs, and it composes
      reaches for exactly those — a profile whose producers are incomparable on a parameter the
      Calculator does not consume still **builds**, provided the top-level Arbiter resolves it.
- [x] Every `Capability` can answer `reach(p)` for every `p` in its `parameters` — no form declares a
      parameter whose reach it cannot publish. `UnionCapability` derives `parameters` from its
      composed domains so the two cannot disagree.
- [x] **End-to-end:** `compose()` a profile, then read `capability.reach(p)` off the woven root — for
      a provider-served parameter and for a derived one — getting the declared domain, still live
      after the clock advances. Reach has never had integration coverage; this is where it starts.
- [x] `nodes/reach.py` is deleted and `Provider.footprints` is gone; `validate_calculators` lives in
      `nodes/composition.py` and is `weave`'s precondition (its first step), reached on the production
      path from `compose()` (new — production never called it); its tests pass unchanged bar the import.
- [x] 003a's reach tests survive as composition tests — dominance, ties, incomparability, liveness,
      priority-independence, calculator contained-in-all, sheared inputs. One **inverts** by design:
      `test_reach_rejects_lone_non_separable_candidate` becomes "a lone non-separable footprint is
      returned unchanged" (exception 2 above). The multi-candidate separability test is unchanged.
- [x] The sheared-inputs `CompositionError` still names its calculator, sourced from the
      `CalculatorKey` on `DerivedCapability`.
- [x] `pyright` clean, `pytest` green, `ruff` clean. No new `# type: ignore`.

## Out of scope

- Any change to what a profile serves. This is a placement change; the ADR's argument is that the two
  representations always described the same set.
- The X/Y-first preference — still decided-but-unbuilt, triggered by the first regional provider.
- `Domain.intersect` — still a declared seam; it is what a future area product needs for cross-parameter
  folding, not this ticket.
- Surface narration and the omitted-`end` default — [003c](../003c-request-shaping.md).
