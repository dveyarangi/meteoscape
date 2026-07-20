---
status: accepted
---

# Reach is an inner bound, selected — not folded

A profile's per-parameter **`reach` `Domain`** is an **inner bound**: *every point it names is
servable*. It is obtained by **selecting one producer's own `Domain`**, never by folding a new one per
axis.

**Reach is a profile-level product, not a `Capability` facet.** It is resolved **once at build time**
from the producers' declared footprints and handed to the surface; no Manifold carries it.

## Why per-axis folding is invalid

Joining reach **per axis** — point axes (X/Y/Z) by union and `valid_time` by intersection — yields a
value that is "spatially an outer bound, temporally a guarantee." It has three defects:

- **The spatial union is not a union.** Two disjoint footprints have no single-interval union, so the
  operation is really a **convex hull**: `{Europe × 16 d, Americas × 10 d}` produces a trans-Atlantic
  span *neither producer serves*. Rejecting the unservable interior later at admission preserves
  **safety**, not **usefulness**; reach's only consumer is narration, where a caller must not have to
  guess inside the reported boundary.
- **The motivating example is a misconfiguration, not a product.** A profile of disjoint regionals
  with no global fallback has a hole in it. Designing the semantics around it optimized for a broken
  deployment. The real topology is **regional + global fallback**, whose union collapses to the global
  footprint — exact, admissible, no guessing.
- **Per-axis folding is what destroys the answer.** It drops inter-axis correlation, which is exactly
  the information that makes reach usable. The extent-axis intersection has the mirror defect: it lets
  a narrow regional with a short horizon **amputate the global product's promise** (`{Europe × 16 d,
  Global × 10 d, Arctic × 5 d}` → 5 d, though every point is served for 10 d). That is an artifact of
  folding T without asking *who covers the space*.

## The rule

Reach **is one producer's `Domain`**, returned whole — never a synthesized one. One principle: *the
largest region the node can serve, expressed as a `Domain` that already exists.*

**The node type supplies the quantifier**, and reach has exactly **two composition sites**, because a
Calculator's inputs are themselves resolved by a **scoped Arbiter**
([ADR-0004](./0004-producer-resolution-and-capability.md)) — so the same two repeat at every depth:

| Site | Serves where | `grid` picks |
|---|---|---|
| **Arbiter** | **any** producer serves | the **dominating** (widest) footprint |
| **Calculator** | **all** its inputs serve | the **dominated** (most restrictive) input reach |

Same containment test, opposite directions. The quantifier is a fact about the node, not a policy —
and the two sites need **different procedures**, because only one of them gets its inner bound for
free:

**At the Arbiter** (the winner serves its own footprint by itself, so no cross-check is needed):

1. Find the footprint that dominates all others **on X/Y**.
2. Among X/Y ties, the one dominating on the **remaining axes**.
3. **Raise** if either step is unresolved.

The winner's `Domain` is the reach, entirely — its T comes along regardless of the others'. So
`{Europe × 16 d, Global × 10 d}` → **`Global × 10 d`**, and
`{Europe × 16 d, Global × 10 d, Arctic × 5 d}` → **`Global × 10 d`** (Arctic never extended the
spatial promise, so it cannot shorten the temporal one). Here dominance **must** be judged X/Y first,
not all axes at once: `Global × 10 d` does not contain `Europe × 16 d` as a whole box, so an all-axis
test would raise on the motivating case. That axis preference — *spatial completeness beats forecast
length* — is a **product judgment**, and it is the only judgment in the rule.

**At the Calculator** the same X/Y-first procedure would be **wrong**: the winner's footprint is only
servable where the *other* inputs also serve, so containment must hold on **every axis against every
other input** — whole-box, no axis ordering, no judgment. (X/Y-first would take
`{Europe × 10 d, Global × 5 d}` to `Europe × 10 d`, promising five days the Global input cannot back —
an inner-bound violation.) So:

1. Find the input contained in **every other input on all axes**.
2. **Raise** if none is (candidates exist but none is whole-box contained — *sheared* inputs).

When such an input exists, its footprint **is the exact intersection** of the candidates — not merely
an inner bound — so under never-synthesize it is the *only* correct answer. (A calculator input with
**no** producer at all is a different failure — a wiring gap, not geometry: a calculator is an operator
promise, so an unwired input fails the build with a distinct, explicit error. That is composition
well-formedness, checked before reach → [#35](../concerns.md#35-calculator-satisfiability-vs-optional-provider-degrade);
reach assumes every input is producible.)

**A tie is resolved, not unresolved — at either site.** Mutual containment means **equal extents per
axis**, so tied candidates state the *same promise*: **any of them may be returned, and the choice is
unobservable** — in v1 the tied footprints even share the same live axis objects. No ordering is needed
and none is imposed. This is not the rejected arbitrary tie-break, which hid a choice between
*incomparable* candidates; here there is no observable choice to hide. The case is not exotic — v1's
derived wind presents it on every parameter (`wind_u` / `wind_v` are distinct footprint objects with
equal extents), so "raise on non-unique" would fail every profile containing a Calculator.

Resolution is therefore one small mutual recursion: `reach(arbiter, p)` over its producers' footprints,
a Source's footprint being its provider's declaration, a Calculator's being the dominated one among
`reach(scoped_arbiter, i)` for its inputs.

**Returning an existing `Domain` rather than a synthesized one** — on *both* paths — is what makes this
cheap and correct: inner-boundedness holds **by construction** (that producer serves every point of it
— no proof obligation), and the representation is **inherited**, so a clock-anchored `RollingAxis`
stays live with no special handling and a future curvilinear footprint survives the selection intact.

**The selection is clock-dependent; the guarantee is not.** Both sites compare `valid_time` extents
(the Arbiter's tie-break, the Calculator's whole-box check), which a `RollingAxis` resolves against
the clock — so where producers tie on X/Y and differ on T, *which* one wins depends on when the
profile was built, and two instances of one config may narrate different reaches. That is **non-determinism, not incorrectness**: every candidate is a real producer's footprint,
so whichever wins is a true inner bound. It does mean the build-time guarantee covers
**unresolvability**, not **stability of the winner**. No v1 profile can hit it (a single provider
cannot tie with itself).

## Where it is resolved, and why not on `Capability`

**The surface is reach's only client** — the omitted-`end` default window and the tool-description
narration, plus the deferred introspection tool and backward reach. Nothing inside the algebra reads
it: `serves` does all admission, the Arbiter ranks by `reconciler`, the `Reservoir` uses store reports.

So reach is resolved **once at build time**, over the `ProfileDef`, and handed to the surface —
`resolve_reach(ProfileDef) -> Mapping[ParameterId, Domain]`, called from the composition root, **not**
from `Weaver.weave` (which stays thin). The only contract change is one accessor: **`Provider` publishes
the per-parameter footprint it already declares.** Nothing is added to `Capability`, no composite
implements reach, the `Reservoir` forwards nothing, and `Coverage` has no reach at all.

Footprints **cannot** come from config instead: `OfferingSpec` carries no geometry, deliberately —
the manifest keeps declarations and construction together while *"geometry … stays off it"*
([architecture: Catalogues](../architecture.md#config-binders-weaver)). Geometry is the provider's
to declare, so the resolver reads the built `Provider`.

**Liveness survives** because the map holds the winners' `Domain` *objects*, not snapshots: a
clock-anchored `RollingAxis` still resolves at read, so the default window tracks the clock. Only the
*selection* is fixed at build.

Placing reach on `Capability` is rejected for three reasons →
[Rejected alternatives](#rejected-alternatives).

## Reach is advisory in exactly one sense

`serves` remains the **sole admission authority**, and reach never feeds admission — structurally,
rather than by discipline. "Advisory" does not mean *imprecise*: reach is exact on
every axis it reports. What it may still do is **understate** — `Europe × 16 d` callers are narrated
10 d and served 16 d if they ask. That is a correct product statement ("this surface serves 10 days"),
and a caller may always request more explicitly and be admitted.

## The reach rule is a slot

The **axis ordering** — X/Y before `valid_time`, i.e. *spatial completeness beats forecast length* —
is a **product judgment**, not a derivation, and other compositions need other judgments. So the rule
is a **named unit in a slot**, alongside the Arbiter's `reconciler`
([ADR-0004](./0004-producer-resolution-and-capability.md)).

**The reconciler bounds the rule.** These two slots are not independent: the `reconciler` decides what
the composite can actually serve, and a reach rule can only report on that. A splicing or mosaicking
reconciler serves requests **no single producer covers**, so its reach is legitimately wider than any
*selection* rule can express — which is also why obs+forecast raises under `grid` (see Consequences).
Within one reconciler there is still residual product freedom: under `priority`, both "the widest
producer" (`grid`'s choice — it therefore **ignores priority**) and "the primary's footprint" are
correct inner bounds. Pairing the two slots incoherently would narrate a promise the engine cannot keep
→ [#33](../concerns.md#33-reach-rule-and-reconciler-mode-are-coupled).

v1 ships **exactly one** implementation (`grid`), called directly, with **no config plumbing and no
registry**. Freezing a `ReachRule` interface on a single implementation is the specific mistake
[#28](../concerns.md#28-reconciler-interface-selection-ordering-vs-per-cell-fold) records about the
`reconciler` slot — and the second rule is already known to need a wider interface, since a polar-swath
composition constrains the **request's shape** (only "fat" T requests are answerable), not merely which
axes dominate.

## Consequences

- **A profile with a genuine hole fails at build**, as a **`CompositionError`** — the same class as
  the Weaver's existing calculator-cycle check, raised from the resolver rather than from inside a
  node. Unresolved dominance means **the deployment is misconfigured**, so the error is read by an
  operator editing config, not by a caller: it must name **which producers conflict, on which axis**,
  and what would resolve it (add a covering source, or narrow the candidate set). Resolving over
  `ProfileDef` is what makes that possible — the resolver holds every candidate's `SourceKey` /
  `CalculatorKey`, which a `Capability` does not.
- **Holes are legitimate elsewhere, but unreachable in v1.** They arise for
  observation-shaped and archive-shaped sources — station networks, gapped archives, satellite swaths
  — but **no v1 source can produce one**: reach is per-parameter (so a `2 m` / `10 m` Z divergence is
  two single-cell reaches, not a gap), every v1 source is a forecast grid, and a footprint declares
  **reach, not resolution**, so anything the homogenization kernel fills was never a hole
  ([#5](../concerns.md#5-read-time-homogenization-fidelity)). The raise is therefore unreachable in v1
  and guards the seam.
- **Obs + forecast will raise under `grid`, correctly.** `{Global × [0, 16 d], Global × [−2 d, 10 d]}`
  has no dominating producer, though the true servable set is the box `Global × [−2 d, 16 d]`. That
  composition is a named [extension point](../architecture.md#extension-points) and needs its own
  rule; a rule that handled it would be wrong for grids.
- **Config narrows candidates; it never declares reach.** Excluding a producer from the promise (so a
  `Global × 10 d` fallback cannot cap a `Global-minus-poles × 16 d` primary) is the one recorded
  lever — [#29](../concerns.md#29-narrated-reach-inner-bound-by-producer-selection) holds its shape,
  deliberately unspecified. Declaring reach outright was rejected: it becomes a second source of truth
  that can drift from the producers and lie to callers, and it would need validating against the
  selection anyway.
- **Reach stays a `Domain`, not a scalar.** v1 reads only its `valid_time` upper bound, but the
  `Domain` is what absorbs **backward reach** (archive) and the deferred **capabilities-introspection
  tool** without a contract change.

## Rejected alternatives

- **Convex hull / outer bound** — narrates a boundary containing unservable points.
- **Per-axis fold of any kind** — drops the inter-axis correlation that makes the answer usable.
- **Synthesizing the maximal inscribed box** — non-unique in the motivating case (`Global × 10 d` and
  `Europe × 16 d` are both maximal), so it still needs the tie-break, and it discards the producer's
  representation for no gain.
- **Tie-breaking by measure** (largest box by volume/utility) — requires commensurating degrees²
  against days, and the answer flips as providers change.
- **Reach as a scalar horizon** — cheaper, but sells the `Domain` property bought for archive and
  introspection.
- **`reach` as a `Capability` facet** — three reasons:
  - **It served one caller from outside the algebra** by putting a member on every Manifold, yielding
    vestigial implementations: a materialized `Coverage`'s "reach" answers a question nobody asks, and
    a `Reservoir` forwarded a value it never used.
  - **The discipline could only be a rule.** "No admission path may consult `reach`" had to be obeyed
    by hand. Resolved at build, reach is **not reachable from the request path at all** — the rule
    becomes a fact.
  - **Errors could not be actionable.** A `Capability` carries no producer identity (`SourceKey` lives
    on `Producer`), so a raise from inside a composite structurally cannot name what conflicts.

  Revisit only if a **runtime** consumer appears inside the algebra →
  [#32](../concerns.md#32-runtime-footprint-awareness-inside-the-algebra).
