---
status: accepted
---

# Capability carries its domain; reach is a Manifold's

A **`Capability` publishes the `Domain` it serves, per parameter** — `reach(parameter) -> Domain`,
alongside `parameters` and `serves`. A Manifold's **Reach** *is* that domain — the member carries the
glossary's name for the concept, leaving `domain` to the parameter-free enumerable field
result-`Countable` forwards to. The profile's reach is
the woven root's; a Calculator's input reach is its scoped Arbiter's. There is no separate reach
artifact, no reach rule, and no build-time pass that recomputes what the capability tree already
composes.

Replaces *"Reach is an inner bound, selected — not folded"*.

## Reach is tight

Reach is an inner bound in form — every point it names is servable — and **tight in every profile that
composes**, because the composition rule leaves no room for it to be loose:

- At an **Arbiter**, composition returns the candidate containing all others, or raises. So any profile
  that composes has a **dominating producer per parameter** — and the served set (the union of
  footprints, since `serves` admits if *any* producer covers the request) is exactly that producer's
  footprint.
- At a **Calculator**, composition returns the input domain contained in all others, or raises — which,
  when it exists, is the exact intersection, and a Calculator serves exactly where all inputs do.

Both folds are **exact whenever they do not raise**, and a profile where they would raise cannot start.
So `reach` and `serves` describe the *same set* in every running system.

Two divergences remain, and neither is fixable by representation:

- **`serves` may tighten below geometry.** Resampler-reachability and probed availability are declared
  seams inside `serves` ([ADR-0004](./0004-producer-resolution-and-capability.md)). `reach` is the
  *declared* geometry; narration off it overpromises exactly to the extent those seams land.
- **Runtime degrade.** A provider that is down shrinks the served set below its declaration
  ([#30](../concerns.md#30-response-membership-under-runtime-degraded-fallback)). Declared geometry
  cannot express availability.

This is why `serves` **stays** on the interface rather than being derived from `reach`: the two answer
different questions (*what do I declare* vs *what will I admit*), and the second is allowed to be
stricter.

## Every form has a domain

The member is vestigial on none of them:

| Form | Whose | `reach(parameter)` |
|---|---|---|
| `FootprintCapability` | a Provider leaf | the declared footprint |
| `EnumerableCapability` | a materialized Coverage | its grid |
| `UnionCapability` | an Arbiter | the dominating producer's domain |
| `DerivedCapability` | a Calculator | the domain contained in all inputs' |

`EnumerableCapability` already defines `serves` as
`parameter in parameters and domain.matches(requested)` — the shape the other three share.

**Composites hold their members keyed by `ProducerKey`.** Without that identity, a composition that
cannot resolve could report only *that* it failed, not *which* producers conflict on *which* axis — and
that error is read by an operator editing a profile, so it must name both.

## Composition is the reconciler's

How producers combine *is* what the combination serves, so the composition rule is a member of the
**`Reconciler`** — not a peer slot:

| Reconciler | Composed domain |
|---|---|
| `priority` (wholesale fallback) | the dominating footprint, else raise |
| `tile` / mosaic | the spatial union — which, given real nesting (regional ⊂ global), is the outer footprint |
| `splice` on `valid_time` | the temporal union, contiguous by construction |

v1 ships one reconciler and `build_reconciler` rejects the rest, so `priority`'s rule is correct for
every profile that can compose. Putting the member on the protocol despite the single implementation is
deliberate: the alternative leaves a future `tile` reconciler silently composing by dominance and
narrating a wrong envelope with **no signal**. Silent incorrectness is worse than an interface that may
need reshaping.

This **narrows [#33](../concerns.md#33-reconciler-owns-domain-composition)** rather than killing
it: two independently-configured slots that had to be paired coherently become one member that moves
with its reconciler.

## Per-parameter, always — and folding is the surface's

A capability's domain is **per parameter**. A single cross-parameter domain must either union
(overpromising for the parameter that reaches less far) or intersect (underpromising, and not
representable in general). Neither is a defensible default, so the algebra never folds across
parameters.

**Folding is a surface decision**, made per product, at the edge — and it is exact **only while the
surface pins the axes it is not folding**:

| Product | Fold | Exact? |
|---|---|---|
| `forecast_hourly` | `min` over `valid_time`; X/Y pinned to a point, Z edge-synthesized | yes |
| task surfaces (go / no-go) | intersection across jointly-consumed parameters | yes — and correctly underpromises |
| area / map / alert products | X/Y **and** T vary while parameters are consumed jointly | **no** — needs `Domain.intersect`, a declared seam |

A regional producer that supplies only *some* parameters makes X/Y diverge per parameter, so the last
row is not hypothetical; it is bounded by an already-named seam rather than by this ADR.

## Why per-axis folding is invalid

Composition **selects** an existing child `Domain`; it never joins them axis by axis. Joining per axis
— point axes (X/Y/Z) by union, `valid_time` by intersection — yields a value that is "spatially an
outer bound, temporally a guarantee", and it fails three ways:

- **The spatial union is not a union.** Two disjoint footprints have no single-interval union, so the
  operation is really a **convex hull**: `{Europe × 16 d, Americas × 10 d}` produces a trans-Atlantic
  span *neither producer serves*. Rejecting the unservable interior later at admission preserves
  **safety**, not **usefulness** — a caller must not have to guess inside a reported boundary.
- **It drops inter-axis correlation**, which is exactly what makes the answer usable. The T-intersection
  has the mirror defect: it lets a narrow regional with a short horizon **amputate the global promise**
  (`{Europe × 16 d, Global × 10 d, Arctic × 5 d}` → 5 d, though every point is served for 10 d) — an
  artifact of folding T without asking *who covers the space*.
- **The motivating example is a misconfiguration, not a product.** Disjoint regionals with no global
  fallback have a hole; designing semantics around it optimizes for a broken deployment. The real
  topology is regional + global fallback, whose union collapses to the global footprint — exact,
  admissible, no guessing.

**And the example is inverted relative to how NWP works.** Regional models reach *shorter*, not further
(ICON-D2 48 h < ICON-EU 120 h < ICON global 180 h; HRRR 48 h, NAM 84 h < GFS 384 h; AROME 42 h <
ARPEGE 102 h < IFS 240 h) — higher resolution costs per forecast hour and convective-scale
predictability decays fast. A regional adds **resolution inside a shorter window**
([#20](../concerns.md#20-provider-multi-resolution-offerings-offering-aware-selection),
[#29](../concerns.md#29-narrated-reach-what-a-profile-promises)), so the global producer dominates on
X/Y **and** T at once. This is the empirical reason the fold's motivating case cannot arise, and
without it a future reader will re-propose the fold.

## Composition rules

- **Ties are resolved, not unresolved.** Mutual containment means equal extents per axis, so tied
  candidates state the same promise and any may be returned — the choice is unobservable. Not exotic:
  v1's derived wind presents it on every parameter (`wind_u` / `wind_v` are distinct objects with equal
  extents), so "raise on non-unique" would fail every profile containing a Calculator.
- **Composition returns an existing `Domain`, never a synthesized one.** This is what buys three
  properties at once: tightness holds **by construction** (that producer serves every point — no proof
  obligation); liveness is **inherited**, so a clock-anchored `RollingAxis` still resolves against the
  clock at read and only the *selection* is frozen; and the representation survives, so a future
  curvilinear footprint passes through intact ([#12](../concerns.md#12-curvilinear-domains)).
- **Dominance is per-axis extent containment, not `Domain.matches`.** `matches` is the request-side
  admission test and `VantageAxis` specialises it to intersection, so reusing it would silently make
  dominance mean "overlaps".
- **Config narrows candidates; it never declares geometry.** `OfferingSpec` carries no geometry,
  deliberately; declaring reach outright was rejected as a second source of truth that can drift.
- **The X/Y-first preference stays decided-but-unbuilt.** v1's body is containment only; the judgment's
  trigger is the first regional provider, the only configuration that can make candidates incomparable.

## Consequences

- **A misconfigured profile fails at build** with a `CompositionError` naming the conflicting producers
  and the axis. Composition is eager at capability construction, so this is structural rather than a
  separate validation pass.
- **`Provider.footprints` is removed.** It existed only so a build-time reader could see geometry the
  `Capability` interpreted privately; the capability now publishes it.
- **The standalone reach resolver and its rule are removed**, and one of
  [#34](../concerns.md#34-producer-dag-walking-is-duplicated)'s three DAG walks with them. Calculator
  **wiring** validation (unproducible inputs, cycles) is unaffected — it is not geometry and still runs
  before `weave`.
- **The composite forms gain producer identity** so composition can name conflicts.
- **Obs + forecast still raises under `priority`**, correctly — `{Global × [0, 16 d],
  Global × [−2 d, 10 d]}` has no dominating producer. It needs a splicing reconciler, which will supply
  its own composition; the union is contiguous and therefore representable when it does.
- **The surface reads reach off the root's capability**, so nothing needs to be threaded from the
  composition root to the edge.
- **[#32](../concerns.md#32-footprint-aware-ranking-inside-the-algebra) is now live, not
  hypothetical** — the domain *is* inside the algebra. What that concern guards against is the request
  path routing on it; `serves` remains the sole admission authority.

## Rejected alternatives

- **Reach as a profile-level artifact resolved by a separate pass** — duplicates a DAG walk, needs
  `Provider.footprints` as a second accessor onto geometry the `Capability` already interprets, and
  requires a hand-obeyed rule keeping reach out of admission (necessary only while reach understates,
  which it does not).
- **Deriving `serves` from `reach`** — forecloses the resampler-reachability and probed-availability
  seams, which legitimately tighten admission below declared geometry.
- **Reach as a set of footprints (an antichain)**, unifying exactly with `serves` even for incomparable
  producers — unnecessary: the case requires a regional reaching *further* than a global, which NWP does
  not produce, and the disjoint-regional case is a misconfiguration that fails the build.
- **Composition on a separate policy object** rather than the reconciler — recreates the two-slot
  coherence problem ([#33](../concerns.md#33-reconciler-owns-domain-composition)) under a new
  name.
- **Convex hull / outer bound** — narrates a boundary containing unservable points.
- **Synthesizing the maximal inscribed box** — non-unique where it would matter, so it still needs a
  tie-break, and it discards the producer's own representation for no gain.
- **Tie-breaking by measure** (largest box by volume) — requires commensurating degrees² against days,
  and the answer flips as providers change.
- **Reach as a scalar horizon** — cheaper, but sells the `Domain` property that absorbs backward reach
  (archive) and the deferred capabilities-introspection surface without a contract change.
