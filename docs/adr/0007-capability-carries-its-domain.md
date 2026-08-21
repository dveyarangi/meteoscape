---
status: accepted
---

# Capability carries its domain; reach is a Manifold's

A **`Capability` publishes the `Domain` it serves, per parameter** — `reach(parameter) -> Domain`,
alongside `parameters` and `serves` (and `origins`, the declared-provenance member owned by
[ADR-0003](./0003-provenance-and-origin.md)'s origin-identity amendment). A Manifold's **Reach** *is* that domain — the member carries the
glossary's name for the concept, leaving `domain` to the parameter-free enumerable field
result-`Countable` forwards to. The profile's reach is
the woven root's; a Calculator's input reach is its scoped Arbiter's. There is no separate reach
artifact, no reach rule, and no build-time pass that recomputes what the capability tree already
composes.

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
| `GranularCapability` | a Provider leaf, a multi-domain carrier, or a retentive `Store` | that parameter's own `Domain` — declared footprint or held record |
| `EnumerableCapability` | a materialized Coverage | its grid (narrowed to `EnumerableDomain` in the type) |
| `UnionCapability` | an Arbiter | the dominating producer's domain |
| `DerivedCapability` | a Calculator | the domain contained in all inputs' |

`EnumerableCapability` already defines `serves` as
`parameter in parameters and domain.matches(requested)` — the shape the other three share.

Two contract details ride on the table. **`parameters` is the sole membership authority**:
`p in parameters` ⟺ `reach(p)` answers, and no form may declare a parameter whose reach it cannot
publish — which is why a scoped composite derives its parameter set from the domains it composed,
never from its whole-producer members. For an unserved parameter `reach` raises a plain `KeyError`:
asking is a caller error, not a composition failure. And **`EnumerableCapability.reach` narrows
covariantly to `EnumerableDomain`** — the co-domained form's reach *is* its grid, so
"materialized ⇒ enumerable reach" is stated in the type **for that form**. It is deliberately *not*
claimed of the per-parameter `GranularCapability`: its materialized use (a multi-domain carrier, a
retentive `Store`) publishes enumerable domains as a fact of construction, and no caller reads a
reach back at the narrower type. The materialized-**provider** discriminator
([ADR-0006](./0006-materialization-granularity-and-store-shape.md)) rests on the *class*
`EnumerableCapability`, never on a reach type — a parameterized form could not carry it at all,
since parameterization is erased at runtime.

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

The Calculator's fold is its node's for the same reason: `Calculator` composes contained-in-all over
its inputs' reaches at construction and hands the result to the `DerivedCapability` that carries it —
capability forms carry composed reaches; the rules live with the composing nodes.

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
  admissible, no guessing. **The fallback need not be a source:** a Calculator deriving the parameter
  from a global's basics is a global producer of it, and rescues disjoint regionals the same way
  (regional gusts over Europe and the Americas, plus a gust Calculator over GFS →
  [#32](../concerns.md#32-footprint-aware-ranking-inside-the-algebra)). This has a structural
  consequence: a Calculator is never in its own scoped resolver, so that resolver cannot see the
  fallback and must be **restricted to the Calculator's inputs** — otherwise it composes parameters
  its Calculator never consumes and rejects a profile the top-level Arbiter resolves.

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
- **Sample levels compose by Allowance, not containment.** Where both candidates declare a count-1
  **sample** cell,
  containment degenerates to point equality — `[2,2]` neither contains nor is contained by
  `[1.5,1.5]`, though both are ordinary screen heights — so the exact-fit question is the wrong one.
  Fallback is *accepted quality degradation*: serving one screen level for another is that
  degradation, and it is accepted the same way — by declaring its bound. Two sample levels compose
  iff **equal** (a tie, per the tie rule above — the band never narrows what composes) **or both
  inside the Parameter's declared allowance**
  ([parameters.md § Sample-level allowance](../parameters.md#sample-level-allowance)); dominance is
  then decided on the remaining axes, and the winner's own `Domain` is returned unchanged — its
  level stays its own, honest within the band. A level outside the band is a genuine
  incomparability and still fails the build. A sample-vs-span pair under a **banded** parameter
  is the same incomparability — the band declares that Z is a sample level, so a span candidate
  under that id is a modeling violation to surface, not absorb; unbanded parameters keep
  containment for mixed pairs. The allowance is the **Parameter's** fact, never a
  producer's: a leaf declaring its own acceptability would be policy smuggled into a declaration,
  and the shared fold stays provider-blind. Statistic **span** cells (cloud cover's column) keep
  containment — that is the maximal-served-cell rule, where extent is genuinely coverage.
- **Separability is a precondition of comparing, not of publishing.** A lone candidate compares
  against nothing, so its footprint — separable or not — is returned unchecked; refusing it would
  break reach-equals-`serves` for a leaf `serves` already admits. Two or more candidates must all
  expose axes, and a non-separable one among them fails the build
  ([#12](../concerns.md#12-curvilinear-domains)).
- **Config narrows candidates; it never declares geometry.** `OfferingSpec` carries no geometry,
  deliberately; declaring reach outright was rejected as a second source of truth that can drift.
- **The X/Y-first preference stays decided-but-unbuilt.** v1's body is containment plus the
  sample-level Allowance arm above. A regional provider is the incomparable configuration whose
  resolution would need an axis **preference**; an out-of-band sample level instead resolves by
  Parameter declaration and fails the build.

## Consequences

- **A misconfigured profile fails at build** with a `CompositionError` naming the conflicting producers
  and the axis. Composition is eager at construction, so this is structural rather than a separate
  validation pass. Each composition rule is the **sole author** of its own error — the reconciler names
  the parameter and producers, the `Calculator` node its calculator and inputs — so no rule raises
  something generic for another layer to translate. `CompositionError` itself lives in `errors.py` as
  a Tier-0 leaf.
- **Provider geometry has one public home:** the `Capability` publishes it; there is no second
  `Provider.footprints` accessor.
- **There is no standalone reach resolver or reach rule.** Calculator
  **wiring** validation (unproducible inputs, cycles) is unaffected — it is not geometry and runs as
  `weave`'s precondition (its first step).
- **The composite forms gain producer identity** so composition can name conflicts.
- **Obs + forecast still raises under `priority`**, correctly — `{Global × [0, 16 d],
  Global × [−2 d, 10 d]}` has no dominating producer. It needs a splicing reconciler, which will supply
  its own composition; the union is contiguous and therefore representable when it does.
- **The surface reads reach off the root's capability**, so nothing needs to be threaded from the
  composition root to the edge.
- **The domain is inside the algebra.**
  [#32](../concerns.md#32-footprint-aware-ranking-inside-the-algebra) guards against request-path
  routing on it; `serves` remains the sole admission authority.
- **Accepted limitation — a store's plural holdings truncate to one reach.** A live store accumulates
  Holdings at many spatial cells per parameter (two cities warm two cells in one store), but `reach(p)`
  returns **one** `Domain` and no capability form carries disjoint multi-cell reaches. `MemoryStore`
  advertises a `GranularCapability` whose per-parameter reach is the **latest-assimilated Holding's
  domain** — honest membership, narrated geometry. This is safe because reach is
  composition-and-narration, never request-path algebra: its only algebraic readers fold **producer**
  capabilities (the Arbiter's `compose_domains` over members, a Calculator's contained-in-all over its
  resolver), and the MCP edge narrates the root's reach — a store is never an Arbiter member, and the
  `Reservoir` forwards its *child's* capability upward. The per-ask exact answer lives on
  `store.project`'s returned `CoverageSet.capability`, where the ask pins one cell and plurality cannot
  arise. A narrating reach with gaps is even natural for an archive store, whose holdings are plural by
  design. **Revisit** when the first real multi-reach reader arrives — store hit/refill observability,
  or the persisting/archive substrate
  ([#44](../concerns.md#44-dedicated-live-archive-store-for-throughput)); that reader decides whether
  to mint a plural-reach advertisement form (amending this ADR) or to read the Holding table through a
  substrate-side face instead.

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
