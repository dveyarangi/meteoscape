# 003b — Capability carries its domain

- **Status:** Ready
- **Depends on:** [003a — Profile reach](./done/003a-profile-reach.md) (landed — this reshapes it), [m1](./done/m1-type-contract-hygiene.md)
- **Blocks:** [003c — Request shaping](./003c-request-shaping.md), which consumes the reach it publishes
- **Owning decision:** [ADR-0007 — Capability carries its domain](../adr/0007-capability-carries-its-domain.md)
- **Outcome:** `Capability.domain(parameter)` on the interface; a Manifold's Reach is its capability's
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

**No behaviour changes.** Every profile that composes today composes to the same geometry; the ADR's
tightness argument is that they were always the same set.

## What to build

Design and rationale are [ADR-0007](../adr/0007-capability-carries-its-domain.md) entire; this ticket
builds it.

- **`Capability` gains `domain(parameter: ParameterId) -> Domain`**, raising for a parameter it does not
  serve; `parameters` stays the sole membership authority. All four forms implement it —
  `FootprintCapability` (its declaration), `EnumerableCapability` (its grid, already exposed),
  `UnionCapability` (the dominating member), `DerivedCapability` (contained-in-all over inputs).
  `serves` **stays** and is unchanged.
- **`Reconciler` gains a domain-composition member.** `PriorityReconciler` implements dominance-or-raise
  — `GridReachRule.reach`'s body, moved.
- **Composite capabilities carry `ProducerKey`s** so composition can name the conflicting producers and
  axis in its `CompositionError`. This is what made the previous "errors can't be actionable" objection
  real; it is resolved by construction, not by message text.
- **Composition is eager at construction**, so an incomparable profile fails at build. `Arbiter.capability`
  stops rebuilding a fresh `UnionCapability` on every access.
- **Delete** `nodes/reach.py`'s `GridReachRule`, `resolve_reach`, `_contains`, `_split`,
  `_incomparable`, `_contained_in_all`, and `Provider.footprints` (with its Open-Meteo and fake
  implementations).
- **Keep** `validate_calculators` — wiring and cycles, not geometry. It still runs before `weave`. Its
  module home is an open question below.

## Implementation questions still open

Deliberately unsettled — they are placement, not contract, and the ADR does not bind them.

1. **Where `Reconciler` lives.** It must be reachable from `manifold/capability.py`, which today would
   invert the layering (`Reconciler` is in `nodes/arbiter.py`). Preferred direction: move `Reconciler`,
   `Producer` and `PriorityReconciler` into `manifold/` — `Producer` is `{Manifold, ProducerKey}`, both
   manifold-visible, and it keeps all four capability forms together, which
   [capability.py](../../src/meteoscape/manifold/capability.py)'s docstring states as intent. **Watch
   the import cycle**: `core → capability`, so `capability → reconciler → core` closes a loop; a
   `TYPE_CHECKING` import breaks it, as [catalog/calculators.py](../../src/meteoscape/nodes/catalog/calculators.py)
   already does. The rejected alternative was moving `UnionCapability` / `DerivedCapability` out to
   `nodes/`, which guts that stated intent.
2. **Where `build_reconciler` stays.** It needs `SourceRegistry` / `CalculatorRegistry` / `ArbiterPolicy`,
   so it cannot follow the protocol into `manifold/`. Protocol and factory end up on opposite sides —
   acceptable, but decide whether `PriorityReconciler` sits with the protocol or the factory.
3. **Where `validate_calculators` lives** once `reach.py` is otherwise empty — its own module, or
   `composition.py` beside the binders that build the `ProfileDef` it validates.
4. **Whether the domain composition member takes `parameter`.** `select` does; the moved
   `GridReachRule.reach` body does not use it. Symmetry vs. an unused argument.
5. **`Provider.footprints` removal blast radius** — `tests/fakes.py`'s `FakeProvider`,
   `CountableFakeProvider`, and the Open-Meteo leaf all implement it.

## Acceptance criteria

- [ ] `Capability.domain(parameter)` exists on the protocol and on all four forms; raises for an unserved
      parameter; `parameters` remains the only membership authority.
- [ ] `serves` is unchanged in behaviour and still the sole admission authority.
- [ ] A profile whose producers are incomparable for a parameter fails at **build** with a
      `CompositionError` naming the conflicting producers and the failing axis — the message quality
      003a's tests already assert.
- [ ] Composition returns an **existing** child `Domain`, never a synthesized one, so a clock-anchored
      `RollingAxis` stays live: a reach read after the clock advances reflects the new anchor.
- [ ] Equal-extent ties return one of the candidates without raising (the derived-wind case).
- [ ] `Arbiter.capability` is computed once, not per access.
- [ ] `nodes/reach.py`'s geometry passes and `Provider.footprints` are gone; `validate_calculators`
      still runs before `weave` and its tests pass unchanged.
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
