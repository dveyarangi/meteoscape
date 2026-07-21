# 0015 · 2026-07-21 · m1 type hygiene, then reach moves onto `Capability`

Two pieces of work, connected by accident. A routine "pyright reports 40 errors" cleanup forced a
close reading of the `Domain` / `Capability` contracts, and that reading exposed a placement mistake in
[ADR-0007](../adr/0007-capability-carries-its-domain.md) one day after it landed. The ADR was replaced.

Rules live in **[ADR-0007](../adr/0007-capability-carries-its-domain.md)**; this record carries the
reasoning trail, the reversals, and what remains open.

## What landed

**`29a50c5` — 003a retired.** Profile reach validated against its acceptance criteria: 15 of 16 met.
The one failure was the ticket, not the code — a criterion forbade any `{Europe × …}` fixture, but the
both-axes error-message test builds one. Criterion reworded to forbid the X/Y-first *judgment* (which
genuinely isn't built) rather than the fixture.

**`88cba17` — m1, type contract hygiene.** `pyright` clean across `src` and `tests` without weakening a
contract: the `grid` rule's separability precondition (which removed a live `AssertionError` path),
four covariant return narrowings, two error-taxonomy corrections found by auditing every `isinstance`
site, and use-site narrowing everywhere else. Details in
[m1](../tickets/done/m1-type-contract-hygiene.md) / [RFC 0004](../rfc/done/0004-20260721-separability-narrowing.md).

**Uncommitted at session end:** ADR-0007 replaced, dependent docs amended, ticket 003b written,
003b/003c renumbered.

## The two reversals

### 1. `Domain.matches` must stay total

m1's plan had `matches` **raise** on geometry it cannot compare, on the theory that returning `False`
conflates *"does not match"* with *"cannot determine"*. Two things killed it:

- **Semantically** — `matches` asks *"will I serve this?"* A representation that cannot determine
  coverage **cannot serve**, so `False` is the correct answer, not a collapsed third state.
- **Operationally** — the Arbiter's candidate loop breaks on the first admitted producer. A raise
  aborts the loop and fails requests a later producer could serve.

The distinction is real but belongs to *diagnosis*, not the predicate → filed as
[#36](../concerns.md#36-unserved-and-uncomparable-are-indistinguishable). The build-time half survives:
a rule restricted to separable geometry declares that a **precondition** and raises, because it has one
caller and no fallback.

This reversal was caught **after** the wrong claim was committed into ADR-0002 and #36; the commit was
amended rather than corrected forward.

### 2. Reach belongs on `Capability`

ADR-0007 (2026-07-20) made reach a profile-level artifact resolved by a separate build-time pass,
explicitly rejecting a `Capability` accessor. That rejection did not survive contact:

- Its **"vestigial implementations"** argument was wrong — every form has a meaningful domain, and two
  were already written, sitting in `reach.py` as `GridReachRule.reach` and `_contained_in_all`.
- Its **"discipline could only be a rule"** argument dissolved — the rule existed because reach
  understated; it does not.
- Its **"errors could not be actionable"** argument was real, and is resolved by keying composite
  members on `ProducerKey`.

**The load-bearing realization: reach and `serves` describe the same set.** Composition returns the
dominating child's `Domain` or **raises**, so any profile that composes has a dominating producer per
parameter — and `serves` (the union) *is* that producer's footprint. The profiles where they would
diverge cannot start. "Inner bound" described a looseness the build guard makes impossible.

## Rejected along the way

- **Capping admission at reach** (serve only what you narrate) — clean, and it wastes a regional
  provider you deliberately paid for.
- **A different reach rule per reconciler** — no *selection* rule can produce a union; the wall is
  representational, not policy.
- **Reach as an antichain of footprints** — would unify exactly with `serves` even for incomparable
  producers. Unnecessary once the NWP fact lands: regional models reach **shorter**, not further
  (ICON-D2 48 h < ICON-EU 120 h < ICON 180 h; HRRR/NAM < GFS), so the global producer dominates on X/Y
  **and** T at once, and the ADR's own motivating example was inverted relative to reality. Recorded in
  the ADR because without it a future reader re-proposes the fold.
- **Moving the composite capability forms into `nodes/`** — rejected in favour of moving `Reconciler`
  into `manifold/`, because `capability.py` states as intent that its forms mirror the algebra.

## Open questions

**Placement, owned by [003b](../tickets/003b-capability-domain.md)** — five, all decided to be
non-contract-bearing: where `Reconciler` / `Producer` live (watch the `capability → reconciler → core`
import cycle), where `build_reconciler` and `validate_calculators` land, whether domain composition
takes a `parameter`, and `Provider.footprints` removal blast radius.

**[#33](../concerns.md#33-reconciler-owns-domain-composition)** — the composition member is on the
`Reconciler` protocol with a single implementation, deliberately: the alternative leaves a future
`tile` silently composing by dominance and narrating a wrong envelope with no signal. Whether one
signature serves `priority` / `tile` / `splice` is unknown until a second reconciler exists.

**[#29](../concerns.md#29-narrated-reach-what-a-profile-promises)** — narrowed to the product question:
declared geometry is an *upper* bound on what a running system serves, since a provider can be down
([#30](../concerns.md#30-response-membership-under-runtime-degraded-fallback)) and `serves` may tighten
below geometry. What a profile should narrate against that gap is undecided.

**Cross-parameter folding** is exact only while a surface pins the axes it is not folding.
`forecast_hourly` pins X/Y and Z, so folding T is exact; an area or alert product folding jointly needs
`Domain.intersect`, still a declared seam.

## Continuation

- **`Weaver.weave -> Reservoir` was reverted after `88cba17`** (uncommitted at session end). m1 landed
  it as one of four covariant narrowings; the revert restores `-> Manifold` on the argument that the
  seam promises the *algebra*, not the composite it happens to construct — root retention is a
  `root_store` config fact, and what makes the root the best view is the Arbiter's selection.
  `architecture.md` and `module-layout.md` were reconciled; the m1 ticket and RFC still describe the
  narrowing as landed, which is correct for a historical record.
- **Commit the uncommitted doc set**; `main` is 4 commits ahead of `origin/main` and unpushed. CI is
  green as of `ee503cf`.
- **Run [003b](../tickets/003b-capability-domain.md)** before
  [003c](../tickets/003c-request-shaping.md), which would otherwise write the first consumer against
  the contract 003b deletes.
- **003c carries one decision from this session**: the narrated horizon is **relative**, never absolute
  instants. The tool description is built once and frozen for the process lifetime, so an absolute date
  is stale within the hour; a `RollingAxis`'s *length* is invariant while its bounds move.
- **`nodes/reach.py` is unreachable production code** until `compose()` calls
  `validate_calculators` — unit-tested, no integration coverage.
- `.claude/CLAUDE.md` is untracked and was not authored in this session.

## Process notes

Three review passes over the doc changes, each finding real defects the previous missed:

1. Mechanical repointing fixed links while leaving prose that **contradicted the ADR it linked to** —
   including ADR-0004 asserting *"Capability carries no reach"*.
2. A link checker that validated only `concerns.md` anchors reported "all resolve" and was useless;
   rewritten to cover every cross-file anchor and self-link, it immediately found two dangling section
   references plus four pre-existing breaks.
3. Applying `/denoise` caught the remaining class: core architecture docs referencing tickets, and the
   replacement ADR written as a **rebuttal of the document it replaced** rather than a statement of
   what is true.

The general lesson: a validator that passes tells you nothing about the class of defect it does not
inspect.
