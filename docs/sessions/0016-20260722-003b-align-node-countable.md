# 0016 · 2026-07-22 · 003b align — five questions closed; node-`Countable` spawns m2

An align session over [003b](../tickets/done/003b-capability-domain.md)'s five open placement questions.
All five resolved (recorded inline in the ticket); two side-finds outgrew the ticket — a new
maintenance ticket [m2](../tickets/done/m2-dissolve-node-countable.md) and the discovery that
`validate_calculators` was never wired into production. Rules live in the ticket, ADR-0007, and m2;
this record carries the reasoning trail.

## What was decided

**Q1/Q2 dissolved together — the `Arbiter` invokes composition; nothing moves to `manifold/`.** Both
questions existed only under the assumption that `UnionCapability` holds the `Reconciler` and composes
lazily, which forces a `manifold → nodes` import. Instead `Arbiter.__init__` calls
`reconciler.compose_domains(...)` and hands the result to the `UnionCapability` it constructs —
symmetric with `project` invoking `select`. The reconciler owns the *rule*; the capability holds the
*result*. ADR-0007's "composition is the reconciler's" is satisfied by who authors the body, not who
holds the reference.

**The member is `reach(parameter)`, not `domain(parameter)`.** The ticket's "its grid, already
exposed" claim for `EnumerableCapability` was wrong at the type level: the protocol member is a
callable, the field is parameter-free, and `CoverageRecord.domain` (result-`Countable`, load-bearing
in `resample`) forwards to that field. Renaming the *field* instead was explored and killed by the
glossary: every synonym (`grid`, `lattice`, `extent`, `geometry`, `bounds`) is `_Avoid_`-listed —
apparently deliberately, so that `Domain` is the only word for a Domain — while the newcomer already
had a glossary name, **Reach**. Doc-only rename propagated to ADR-0007, ADR-0004, architecture,
module-layout, 003c.

**Node-`Countable` dissolves → [m2](../tickets/done/m2-dissolve-node-countable.md).** Started as a
challenge to the `Store` docstring's "capability = held, domain = could hold" split and ended in a
survey: every real countable-provider candidate (archive bundle, climatological normals, static
fields) is *an already-materialized local dataset*, for which `Reservoir(store, provider)` builds a
full mirror of data that is already local. Mid-write, [ADR-0006](../adr/0006-materialization-granularity-and-store-shape.md)
turned out to have **already decided** "Nodes are not `Countable`" — rejected alternatives included —
so m2 is mostly code catching up with an accepted ADR. The genuine delta beyond the ADR: a
materialized provider wires **storeless** (ADR-0006 still handed its lattice to the `StoreFactory`).
Open placement question — where a storeless producer's read-back homogenization lives — registered as
[#37](../concerns.md#37-storeless-materialized-producers-and-read-back-homogenization); **Lattice**
(a Store's private retention grid) joined the glossary. Sequenced 003b → m2 → 006; 006 already
assumes the shape m2 delivers.

**The geometry predicates move, they are not deleted.** The ticket said delete `_contains` / `_split`
/ `_incomparable`; their bodies are exactly what `compose_domains` and `DerivedCapability`'s
contained-in-all need. They land in `manifold/domain.py` beside `AXIS_ORDER`, reachable downward from
both consumers.

**`compose_domains` takes `parameter`.** The ticket's "symmetry vs. an unused argument" framing
dissolved: composition is eager and per-parameter, the raise site inside the reconciler is the only
author of the error, and the operator needs to know *which parameter* sheared. The acceptance
criterion now requires the parameter in the `CompositionError` — new versus 003a, whose resolver was
called per parameter from outside.

**`validate_calculators` → `nodes/composition.py`, and `compose()` gains the call.** It validates the
`ProfileDef` defined there and raises the `CompositionError` defined there; `reach.py` is deleted
entirely rather than surviving as a misnamed one-function module. The find behind the "corollary":
**production never calls `validate_calculators`** — `module-layout.md`, concern #34, and 003b's own
criterion all asserted it runs before `weave`, but `server.compose()` has no such call; the
operator-facing wiring errors were dead code behind the Weaver's terser backstop. Wiring it is 003b's
one deliberate behaviour change.

## Open questions

- **[#37](../concerns.md#37-storeless-materialized-producers-and-read-back-homogenization)** — where
  a storeless materialized producer's read-back homogenization lives (provider base vs a thin
  non-retentive wrapper), and whether `isinstance(capability, EnumerableCapability)` survives as the
  "already materialized" discriminator once a provider is enumerable but unholdable (cloud ARCO).
  Trigger: the first real materialized provider; no v1 driver.
- Unchanged from 0015: **[#33](../concerns.md#33-reconciler-owns-domain-composition)** (whether one
  `compose_domains` signature serves `priority` / `tile` / `splice` — unknowable until a second
  reconciler) and **[#29](../concerns.md#29-narrated-reach-what-a-profile-promises)** (what a profile
  narrates against the declared-vs-served gap).

## Continuation

- **Implement [003b](../tickets/done/003b-capability-domain.md)** — all questions closed, doc set
  consistent, no code touched this session.
- **Then [m2](../tickets/done/m2-dissolve-node-countable.md) before [006](../tickets/006-retentive-store-freshness.md)** —
  006 assumes the storeless/private-lattice shape m2 delivers.
- The 0015 continuation items not addressed here remain: 003c after 003b (with the relative-horizon
  decision), and the unpushed commit backlog.

## Process notes

- Two of the five questions were resolved by **dissolving the premise** rather than choosing between
  the offered options (Q1/Q2's "where does the protocol move" assumed lazy composition; the naming
  question's "which name moves" assumed the field could be renamed). Worth checking a question's
  premise against the code before weighing its options.
- A claim can be believed by three documents and still be false in the code
  (`validate_calculators` "runs before weave"). The class of defect: docs cross-confirming each other
  while none of them was checked against the call site.
- The glossary's `_Avoid_` lists acted as a designed constraint surface — the naming decision fell
  out of them almost mechanically once every synonym was checked.
