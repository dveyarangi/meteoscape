# 003b — Capability carries its domain

- **Status:** Ready
- **Depends on:** [003a — Profile reach](./done/003a-profile-reach.md) (landed — this reshapes it), [m1](./done/m1-type-contract-hygiene.md)
- **Blocks:** [003c — Request shaping](./003c-request-shaping.md), which consumes the reach it publishes
- **Owning decision:** [ADR-0007 — Capability carries its domain](../adr/0007-capability-carries-its-domain.md)
- **Outcome:** `Capability.reach(parameter)` on the interface; a Manifold's Reach is its capability's
  Domain; the standalone reach resolver and its rule are gone.

## Parent PRD

`docs/v1-requirements.md` — this is the structural precondition for user story 10 (envelope narration),
delivered by [003c](./003c-request-shaping.md).

## Why now

003a landed a **separate build-time pass** that walks the producer DAG to compute geometry the
capability tree already composes, plus a `Provider.footprints` contract extension to feed it. Both are
artifacts of putting Reach outside the algebra. 003c would build the first consumer against that shape
and 004 would add a reconciler beside it, so the correction gets more expensive at every step — and the
current code is a worked example of the entity-and-contract sprawl this stage should be preventing.

**No behaviour changes**, with one deliberate exception. Every profile that composes today composes
to the same geometry; the ADR's tightness argument is that they were always the same set. The
exception: `compose()` gains the `validate_calculators` call the docs already assert (question 3
below), so wiring errors that were dead code become reachable operator-facing build failures.

## What to build

Design and rationale are [ADR-0007](../adr/0007-capability-carries-its-domain.md) entire; this ticket
builds it.

- **`Capability` gains `reach(parameter: ParameterId) -> Domain`**, raising for a parameter it does not
  serve; `parameters` stays the sole membership authority. The member is named **`reach`**, not
  `domain`: `EnumerableCapability.domain` is a parameter-free field `CoverageRecord.domain`
  (result-`Countable`) forwards to, every glossary synonym for that field is `_Avoid_`-listed, and the
  glossary already names the per-parameter published Domain **Reach**. All four forms implement it —
  `FootprintCapability` (its declaration), `EnumerableCapability` (its one domain, after the membership
  check), `UnionCapability` (the dominating member), `DerivedCapability` (contained-in-all over inputs).
  `serves` **stays** and is unchanged.
- **`Reconciler` gains a domain-composition member.** `PriorityReconciler` implements dominance-or-raise
  — `GridReachRule.reach`'s body, moved. **The `Arbiter` invokes it** — `Arbiter.__init__` calls
  `reconciler.compose_domains(...)` and hands the composed result to the `UnionCapability` it
  constructs, symmetric with `project` invoking `reconciler.select`. The reconciler owns the *rule*;
  the capability holds the *result*. `Reconciler`, `Producer`, `PriorityReconciler`, and
  `build_reconciler` all **stay in `nodes/arbiter.py`** — no import into `manifold/`, no cycle.
- **Composite capabilities carry `ProducerKey`s** so composition can name the conflicting producers and
  axis in its `CompositionError`. This is what made the previous "errors can't be actionable" objection
  real; it is resolved by construction, not by message text.
- **Composition is eager at construction**, so an incomparable profile fails at build. `Arbiter.capability`
  stops rebuilding a fresh `UnionCapability` on every access.
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
   binders — it validates the `ProfileDef` defined there, raises the `CompositionError` defined
   there, and its one production caller already imports from there. `nodes/reach.py` is deleted
   entirely (the geometry predicates having moved to `manifold/domain.py`); a surviving module named
   `reach` with no reach in it would invite the logic back. Its tests split by destination:
   predicates → `tests/manifold/test_domain.py`, composition rules → the capability/arbiter tests,
   wiring/cycles → `tests/nodes/test_composition.py`.
   **Corollary — wire the call:** `compose()` does **not** call `validate_calculators` today, though
   `module-layout.md`, concern #34, and this ticket's own criterion all assert it runs before
   `weave`. 003b adds the one-line call in `server.compose()`; until then the operator-facing wiring
   errors are dead code behind the Weaver's terser backstop.
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
   [m2](./m2-dissolve-node-countable.md)'s). Two calls inside the radius:
   - `test_provider_footprints_expose_capability_domains` is **rewritten, not deleted** — its
     same-objects / live-T assertions restate ADR-0007's liveness property at the leaf, through
     `capability.reach(pid)`; dropping it would silently shed leaf-level liveness coverage.
   - **`FootprintCapability.footprints` keeps its name** — it is the leaf's *declaration*
     (per-parameter Footprints in the glossary sense), not the published Reach, so the field stays
     honest and its test construction sites don't churn.

## Coordination with m2

[m2 — Dissolve node-`Countable`](./m2-dissolve-node-countable.md) follows this ticket and removes the
node-`Countable` facet (`Reservoir.domain`, `Store`'s `Countable`, `Weaver._source_grid`,
`CountableFakeProvider`'s independent `domain=`). This ticket must not deepen what m2 deletes: leave
`_source_grid` and the `Countable` isinstance sites untouched, and add no new reader of a node's
`domain`. Result-`Countable` (`Coverage` / `CoverageRecord`) is load-bearing and stays.

## Acceptance criteria

- [ ] `Capability.reach(parameter)` exists on the protocol and on all four forms; raises for an unserved
      parameter; `parameters` remains the only membership authority. `EnumerableCapability.domain`
      keeps its name and shape (result-`Countable` forwards to it).
- [ ] `serves` is unchanged in behaviour and still the sole admission authority.
- [ ] A profile whose producers are incomparable for a parameter fails at **build** with a
      `CompositionError` naming the conflicting producers, the failing axis, **and the parameter** —
      the first two are the message quality 003a's tests already assert; the parameter is new,
      possible because eager composition puts the whole error in the reconciler's hands.
- [ ] Composition returns an **existing** child `Domain`, never a synthesized one, so a clock-anchored
      `RollingAxis` stays live: a reach read after the clock advances reflects the new anchor.
- [ ] Equal-extent ties return one of the candidates without raising (the derived-wind case).
- [ ] `Arbiter.capability` is computed once, not per access.
- [ ] `nodes/reach.py` is deleted and `Provider.footprints` is gone; `validate_calculators` lives in
      `nodes/composition.py`, **is called by `compose()` before `weave`** (new — production never
      called it), and its tests pass unchanged bar the import path.
- [ ] 003a's reach tests survive as composition tests — dominance, ties, incomparability, liveness,
      priority-independence, calculator contained-in-all, sheared inputs.
- [ ] `pyright` clean, `pytest` green, `ruff` clean. No new `# type: ignore`.

## Out of scope

- Any change to what a profile serves. This is a placement change; the ADR's argument is that the two
  representations always described the same set.
- The X/Y-first preference — still decided-but-unbuilt, triggered by the first regional provider.
- `Domain.intersect` — still a declared seam; it is what a future area product needs for cross-parameter
  folding, not this ticket.
- Surface narration and the omitted-`end` default — [003c](./003c-request-shaping.md).
