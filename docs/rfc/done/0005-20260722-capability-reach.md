# RFC 0005 · 2026-07-22 · Capability carries its domain — implementation plan

Implementation plan for [003b](../tickets/done/003b-capability-domain.md), owned by
[ADR-0007](../adr/0007-capability-carries-its-domain.md). Planned in the 0016 align session, which
resolved the ticket's five placement questions and found three further design defects; all are
recorded inline in the ticket and restated here where they shape the build.

**Scope in one line:** `Capability` gains `reach(parameter)`; the standalone reach resolver, its rule,
and `Provider.footprints` are deleted; composition becomes a `Reconciler` member the `Arbiter` invokes
eagerly at construction.

## Boundaries involved

| Boundary | Owner | What 003b does to it |
|---|---|---|
| `Capability` protocol | [ADR-0004](../adr/0004-producer-resolution-and-capability.md), [ADR-0007](../adr/0007-capability-carries-its-domain.md) | **Widens** — third member `reach(parameter)`. `serves` and `parameters` unchanged. |
| `Reconciler` protocol | [ADR-0004](../adr/0004-producer-resolution-and-capability.md), [#33](../concerns.md#33-reconciler-owns-domain-composition) | **Widens** — second member `compose_domains(parameter, candidates)`. |
| `Provider` ABC | [ADR-0004](../adr/0004-producer-resolution-and-capability.md) | **Narrows** — `footprints` deleted; geometry published by the capability. |
| `Arbiter` construction | [ADR-0004](../adr/0004-producer-resolution-and-capability.md) | Composes eagerly; a **scoped** Arbiter now declares its scope. |
| `Calculator` construction | [ADR-0004](../adr/0004-producer-resolution-and-capability.md) | Accepts its `CalculatorKey` (for error attribution). |
| `Domain` / `Separable` | [ADR-0002](../adr/0002-data-model.md) | **Gains** the per-axis containment predicates, moved from `nodes/reach.py`. No representation change. |
| `compose()` pipeline | [ADR-0005](../adr/0005-build-time-composition.md) | Gains the `validate_calculators` call the docs already assert. |
| `Arbiter(producers, reconciler, scope=None)` | [ADR-0004](../adr/0004-producer-resolution-and-capability.md) | **Widens** — optional `scope`. Already amended in [architecture.md](../architecture.md#arbiter), [module-layout.md](../module-layout.md) and ADR-0004's scoped-construction example during planning. |
| `Countable` facet | [ADR-0006](../adr/0006-materialization-granularity-and-store-shape.md) | **Untouched** — belongs to [m2](../tickets/m2-dissolve-node-countable.md). |

**Ownership rule preserved:** `errors, parameters, clock, identity ← manifold ← nodes`. Nothing in
`manifold/` imports from `nodes/` — the reason the align session put composition invocation on the
`Arbiter` rather than inside `UnionCapability`.

## Design decisions this plan builds on

Settled in the align session; rationale in the ticket, not repeated here.

1. **The member is `reach(parameter)`, not `domain(parameter)`** — `EnumerableCapability.domain` is a
   parameter-free field that `CoverageRecord.domain` forwards to, and every glossary synonym for it is
   `_Avoid_`-listed.
2. **The `Arbiter` invokes composition**, symmetric with `project` invoking `select`. `Reconciler`,
   `Producer`, `PriorityReconciler`, `build_reconciler` all stay in `nodes/arbiter.py`.
3. **`compose_domains` takes `parameter`** — the raise site is the sole author of the whole error, and
   the operator needs to know which parameter sheared.
4. **Geometry predicates move to `manifold/domain.py`**; `validate_calculators` moves to
   `nodes/composition.py`; `nodes/reach.py` is deleted.
5. **A scoped Arbiter declares its scope** (defect found while planning — see below).
6. **`DerivedCapability` carries its `CalculatorKey`** (defect found while planning).
7. **A lone non-separable footprint is returned, not rejected** (defect found while planning).

## Code shapes

### `manifold/domain.py` — the moved predicates

Per-axis extent containment is geometry, and both consumers sit above this module, so it is the only
home both can reach downward.

```python
def contains_extents(outer: Separable, inner: Separable) -> bool:
    """Whole-box containment by per-axis extent — NOT `Domain.matches`.

    `matches` is the request-side admission test and `VantageAxis` specialises it to intersection,
    so reusing it would silently make dominance mean "overlaps" (ADR-0007).
    """

def as_separable(domain: Domain) -> Separable | None:
    """The domain as `Separable`, or `None` — pure geometry, no error text, no producer key."""

def split_extents(left_key, left, right_key, right) -> str:
    """Why two Domains nest neither way, BOTH directions — the split is the incomparability."""

def first_incomparable(candidates) -> tuple[...] | None:
    """First pair nesting neither way — the witness both call sites report."""
```

**`as_separable` returns; it does not raise.** `CompositionError` lives in `nodes/composition.py` and
`manifold/` may not import it, so a raising predicate would force callers to translate
`ValueError → CompositionError` — the exact "one error, two authors" split the plan rejected for
`compose_domains` (decision 3) and for defect 2. Returning `None` instead lets each caller **author its
whole message with its own context**: the reconciler adds the parameter, `DerivedCapability` adds the
calculator key — both strictly more than 003a's rule, which could name only the producer. The predicate
stays pure geometry with no `key` argument, and nothing in `manifold/` raises a composition error.

### `manifold/capability.py` — the widened protocol

```python
class Capability(Protocol):
    def serves(self, parameter: ParameterId, requested: Domain) -> bool: ...
    def reach(self, parameter: ParameterId) -> Domain: ...
    @property
    def parameters(self) -> Mapping[ParameterId, ParameterDef]: ...
```

| Form | `reach(p)` | Return type |
|---|---|---|
| `FootprintCapability` | membership check, then `self.footprints[p][1]` — a plain lookup | `Domain` |
| `EnumerableCapability` | membership check, then `self.domain` (constant over served parameters) | **`EnumerableDomain`** |
| `UnionCapability` | membership check, then `self.domains[p]` — composed by the Arbiter at construction | `Domain` |
| `DerivedCapability` | membership check, then contained-in-all over `upstream.reach(i) for i in inputs`, computed eagerly at construction | `Domain` |

`EnumerableCapability.reach` **narrows covariantly** — the m1 pattern. That form's reach *is*
enumerable and `CoverageRecord.domain` already returns the narrow type, so the narrowing is honest
rather than speculative; it also states "materialized ⇒ enumerable reach" in the type, which is the
premise [m2](../tickets/m2-dissolve-node-countable.md)'s materialized-provider discriminator rests on.

`UnionCapability` gains `members: Mapping[ProducerKey, Capability]` (was a flat `Sequence`) plus
`domains: Mapping[ParameterId, Domain]`. `DerivedCapability` gains `key: CalculatorKey`.

**Invariant to hold everywhere:** `p in parameters` ⟺ `reach(p)` answers. No form may declare a
parameter whose reach it cannot publish.

**`UnionCapability` holds that invariant structurally, not by discipline.** `parameters` must be
derived from **`domains.keys()`**, not from the members:

```python
@dataclass(frozen=True)
class UnionCapability:
    members: Mapping[ProducerKey, Capability]
    domains: Mapping[ParameterId, Domain]      # the composed reach — also the membership authority

    @property
    def parameters(self) -> Mapping[ParameterId, ParameterDef]:
        merged = {pid: d for m in self.members.values() for pid, d in m.parameters.items()}
        return {pid: merged[pid] for pid in self.domains}      # scoped by construction

    def serves(self, parameter: ParameterId, requested: Domain) -> bool:
        return parameter in self.domains and any(
            m.serves(parameter, requested) for m in self.members.values()
        )
```

Deriving `parameters` from the members instead would break a **scoped** Arbiter: its members are whole
producers declaring parameters outside the scope, so `parameters` would list what `domains` cannot
answer — violating the invariant above and the ticket's criterion that a scoped Arbiter declares
exactly its Calculator's inputs. `serves` needs the explicit membership guard for the same reason: it
self-filters today only because members and scope coincide, which scoping ends.

**Construction precondition:** `domains.keys() ⊆ ⋃ members.parameters`. The Arbiter satisfies it by
construction (it composes `domains` *from* the members it holds), but `UnionCapability` is also
hand-built in tests, so the precondition is documented rather than assumed.

**Layering note for the reviewer.** `capability.py` will import `ProducerKey` / `CalculatorKey` from
`identity`, which can read as an upward dependency. It is not: the rule is
`errors, parameters, clock, identity ← manifold ← nodes` ([module-layout.md](../module-layout.md)), and
`manifold/provenance.py` **already** imports `SourceKey` — identity's own docstring names provenance as
an inward importer. `identity` is a Tier-0 leaf below `manifold`; keys are identities, not node types.

### `nodes/arbiter.py` — the widened reconciler

```python
class Reconciler(Protocol):
    def select(self, parameter, candidates: Sequence[Producer]) -> Sequence[Producer]: ...
    def compose_domains(
        self, parameter: ParameterId, candidates: Sequence[tuple[ProducerKey, Domain]]
    ) -> Domain: ...
```

`PriorityReconciler.compose_domains` is `GridReachRule.reach`'s body plus the parameter in its
messages. It **ignores priority** — dominance is geometric, which 003a's priority-independence test
asserts and which survives as a composition test.

```python
class Arbiter:
    def __init__(self, producers, reconciler, *, scope: frozenset[ParameterId] | None = None):
        self.producers = tuple(producers)
        self.reconciler = reconciler
        self.by_parameter = _index(self.producers, scope)
        self._capability = UnionCapability(
            members={p.key: p.node.capability for p in self.producers},
            domains={
                parameter: reconciler.compose_domains(parameter, _reaches(parameter, candidates))
                for parameter, candidates in self.by_parameter.items()
            },
        )

    @property
    def capability(self) -> Capability:
        return self._capability


def _reaches(
    parameter: ParameterId, candidates: Sequence[Producer]
) -> Sequence[tuple[ProducerKey, Domain]]:
    """Each candidate's published reach for one parameter — `compose_domains`'s input.

    Every candidate is indexed under `parameter`, so `reach` is answerable for all of them
    (`p in parameters` ⟺ `reach(p)` answers).
    """
    return [(p.key, p.node.capability.reach(parameter)) for p in candidates]
```

`scope=None` (the top Arbiter) means every declared parameter. The Weaver passes
`scope=reg.inputs` for a Calculator's scoped Arbiter.

Four details this pins down, so no ambiguity is left to implementation:

- **`Arbiter.capability` stays `-> Capability`, not `-> UnionCapability`.** The seam promises the
  algebra, not the composite it happens to construct — the same argument that reverted
  `Weaver.weave -> Reservoir` in m1 (session 0015). It is now a stored attribute rather than a fresh
  object per access, which is what the "computed once" criterion asks for.
- **`compose_domains` is never called with an empty candidate list.** `by_parameter` only holds
  parameters with at least one producer, so the empty case is unreachable by construction — unlike
  `GridReachRule.reach`, which had to guard it because `resolve_reach` assembled candidate lists
  itself. The implementation still raises on empty (cheap, and it is a genuine contract violation),
  but no test needs to drive it through an Arbiter.
- **Scoping changes `Arbiter.project` for out-of-scope parameters**: a scoped Arbiter asked for a
  parameter outside its scope now finds no candidates and omits it (an all-omitted request raises
  `CapabilityMismatch`, as today). Intentional and unreachable in practice — `Calculator.project`
  only ever asks its resolver for `self.inputs`.
- **`_index` takes the scope** and filters while building, rather than the caller pruning afterwards,
  so `by_parameter` and the capability are never transiently inconsistent.

### `nodes/composition.py` — `validate_calculators` arrives

Body unchanged except `source_serves`, which currently reads `registered.provider.footprints` and
becomes `registered.provider.capability.parameters` — the same set, since `FootprintCapability`
derives `parameters` from `footprints`.

### `server.py` — the wiring the docs already assert

```python
profile_def = ProfileDef(...)
validate_calculators(profile_def)      # NEW — never called in production
woven = Weaver(stores).weave(profile_def)
```

## Flows

**Build (the new eager path)**

```
compose()
 └─ binders → ProfileDef
 └─ validate_calculators(profile)          # wiring + cycles; NEW call site
 └─ Weaver.weave
     ├─ source Producers                    (Reservoir(store, provider))
     ├─ build_reconciler                    → PriorityReconciler
     ├─ per Calculator:
     │   ├─ Arbiter(producers_for(inputs), reconciler, scope=reg.inputs)
     │   │    └─ compose_domains per INPUT parameter  ← may raise CompositionError
     │   └─ Calculator(key, outputs, inputs, fn, scoped)
     │        └─ DerivedCapability: contained-in-all over inputs ← may raise
     └─ Arbiter([*sources, *calcs], reconciler)   # no scope = all parameters
          └─ compose_domains per served parameter ← may raise
```

Every raise is a build-time `CompositionError` naming **parameter + producers + axis** (and, for a
Calculator's shear, its `CalculatorKey`). Nothing reaches the request path.

**Request (unchanged).** `serves` remains the sole admission authority; `reach` is never consulted by
`Arbiter.project`. This is [#32](../concerns.md#32-footprint-aware-ranking-inside-the-algebra)'s
guard and must stay true.

**Read (003c's consumer, not built here).** `gateway.best_view.capability.reach(p)`.

## Defects found while planning

Three, all resolved with the user and back-recorded in the ticket, ADR-0007 and concerns.

### 1. Eager composition rejects a valid profile (scoped Arbiter over-declares)

`Weaver.producers_for` returns **whole producers**, and `Arbiter._index` files each under **every**
parameter it declares. So a Calculator's scoped resolver declares parameters the Calculator never
consumes, and eager composition would compose them.

That rejects a realistic deployment:

| Producer | Serves | Footprint |
|---|---|---|
| ICON-D2 | basics + `wind_gust` **directly** | Europe × 48 h |
| HRRR | basics + `wind_gust` **directly** | Americas × 36 h |
| GFS | basics only | World × 180 h |
| gust Calculator | `wind_gust` from basics | World × 180 h |

The top Arbiter resolves `wind_gust` (the Calculator dominates). The Calculator's scoped resolver
sees only ICON-D2 and HRRR — incomparable — and raises, because **a Calculator is never in its own
scope**. ADR-0007's "disjoint regionals need a global fallback" is satisfied here by a *Calculator*,
which the scoped resolver structurally cannot see.

**Resolution:** the scoped Arbiter is restricted to the Calculator's inputs. This is faithful to its
only use (`Calculator.project` asks it for `self.inputs`; `DerivedCapability` asks upstream only about
inputs), and it restores the `parameters` ⟺ `reach` invariant. The over-declaration is a latent defect
today; eagerness merely exposes it. → ADR-0007 amended; the deployment filed as
[#32](../concerns.md#32-footprint-aware-ranking-inside-the-algebra)'s motivating scenario, since the
*wanted* behaviour (prefer the regional inside its footprint) is footprint-aware ranking, not
composition.

### 2. `DerivedCapability` cannot name its calculator

003a's `_contained_in_all` took `calculator: CalculatorKey` explicitly; `DerivedCapability` holds no
identity, so the sheared-inputs message would lose the calculator name that
`test_resolve_reach_sheared_calculator_inputs_raise` asserts.

**Resolution:** `DerivedCapability` carries its `CalculatorKey` — the exact mirror of the ticket's
existing decision that composites carry `ProducerKey`s. `Calculator.__init__` widens to accept it;
the Weaver has `reg.key` at hand. Rejected: catching and re-raising in `Calculator` (splits one error
across two authors — the shape already rejected for `compose_domains`).

*Verified, not assumed:* `contained_in_all(upstream.reach(i) for i in inputs)` composes the same value
003a computed — 003a also folded over per-input **composed** reaches (`reach_over(scoped, inp)`), not
raw footprints. No divergence.

### 3. A lone non-separable footprint changes verdict

003a checked separability **before** the single-candidate shortcut, so a one-source curvilinear
profile failed the build. Under 003b a leaf's `reach` is a plain lookup, so it builds.

**Resolution: accept the change.** Separability is a precondition of *comparing* per axis, and one
candidate compares against nothing; 003a checked anyway only because the profile-level pass had no
better home for the guard. It also restores consistency — `serves` already admits such a leaf, so a
leaf that can serve but cannot publish its reach would break ADR-0007's reach-equals-`serves` claim
immediately, and curvilinear geometry in the **source role** is a live seam
([#12](../concerns.md#12-curvilinear-domains)). Strictly more permissive: nothing 003a accepted is now
rejected. Two non-separable candidates still fail.

## Stages

TDD, vertical slices — one behaviour, one implementation, repeat. Every stage ends `pyright` +
`pytest` + `ruff` clean. No stage leaves `main` unbuildable.

**Stage 0 — move the predicates (refactor, no behaviour).**
Move `_contains` → `contains_extents`, `_split` → `split_extents`, `_incomparable` →
`first_incomparable`, and `_require_separable` → `as_separable` (returning `Separable | None`, not
raising) into `manifold/domain.py`. `nodes/reach.py` imports them; where it called
`_require_separable` it now checks the `None` and raises its own `CompositionError`, so its behaviour is
unchanged and its existing tests pass **untouched** — that is the proof the move is behaviour-free. Add
`tests/manifold/test_domain.py` cases for the predicates at their new home, including `as_separable`
returning `None` for a `CurvilinearDomain` stand-in.

**Stage 1 — `reach` on the two leaves.**
RED: `FootprintCapability.reach` returns the declared footprint; raises for an unserved parameter.
Then `EnumerableCapability.reach`, narrowed to `EnumerableDomain` — assert the static type at the call
site, not just the value. Then the inverted lone-non-separable case (defect 3). Nothing else changes;
`Capability` protocol gains the member and the two leaves satisfy it.

**Stage 2 — `compose_domains` on the reconciler.**
RED: dominance, equal-extent ties, incomparability naming **parameter + producers + both axes**,
priority-independence, the separability precondition. These are 003a's `GridReachRule` tests, ported
to `PriorityReconciler` with the parameter assertion added. `GridReachRule` still exists at this
point; the two coexist until stage 6a.

*Why the coexistence is safe:* `resolve_reach` **is never called in production** — `compose()` does
not call it and nothing else does (session 0015). So the old path is dead code with unit tests, not a
live second implementation, and there is no dual-path window where the two could disagree in a
running system.

**Stage 3 — `UnionCapability.reach`, and the Arbiter composes eagerly.**
RED: an Arbiter over two producers publishes the dominating reach; an incomparable pair raises at
**construction**; the composed reach is the child's own object (`is`), so a `RollingAxis` stays live
after the clock advances; `capability` is the same object across accesses. Also: **a `Reservoir`
forwards its child's reach unchanged** — `Reservoir(store, provider).capability.reach(p)` `is` the
provider's own domain. That forwarding carries the *root's* reach (the root is
`Reservoir(store, Arbiter)`), so it is load-bearing, not incidental.

*Collateral (mechanical, not a slice — reshaping `UnionCapability` from a flat sequence):*

| Site | Change |
|---|---|
| [test_capability.py](../../tests/manifold/test_capability.py) `UnionCapability(members=[leaf, enumerable])` | key the members: `members={KeyA: leaf, KeyB: enumerable}` |
| [test_server_smoke.py](../../tests/test_server_smoke.py) `UnionCapability([])` | `UnionCapability(members={}, domains={})` — an empty best view still constructs |

`test_arbiter.py` needs no change: its two providers serve **disjoint** parameters, so every
`by_parameter` entry has one candidate and eager composition is trivial.

**Stage 4 — scoped Arbiter declares its scope (defect 1).**
RED: the gust topology above builds; the scoped Arbiter's `capability.parameters` equals the
Calculator's inputs — **and `reach` answers for every one of them and raises for the rest**, which is
the invariant the unscoped `parameters` derivation would break. Then `Arbiter(..., scope=...)`,
`UnionCapability.parameters` derived from `domains`, and the Weaver passing `reg.inputs`.

**Stage 5 — `DerivedCapability.reach` and the `CalculatorKey` (defect 2).**
RED: contained-in-all over inputs; the derived-wind equal-extent tie returns one input's domain
(`is`); sheared inputs raise naming the calculator **and** the inputs. Then the key on
`DerivedCapability` and `Calculator`, and the Weaver passing it.

*Collateral (the new required `key` field):*

| Site | Change |
|---|---|
| [calculator.py](../../src/meteoscape/nodes/calculator.py) `DerivedCapability(self.outputs, self.inputs, self.resolver.capability)` | **production** — pass `self.key`; `Calculator.__init__` gains it, Weaver supplies `reg.key` |
| [test_capability.py](../../tests/manifold/test_capability.py) `DerivedCapability(parameters=…, inputs=…, upstream=…)` | add `key=CalculatorKey(...)` |

**Stage 6a — delete the dead rule and resolver.**
Remove `GridReachRule` and `resolve_reach`. Nothing calls either by now (they were never called in
production), so this is pure deletion. Their tests are already re-homed: geometry predicates in
`tests/manifold/test_domain.py` (stage 0), composition rules on `PriorityReconciler` (stage 2),
calculator contained-in-all and shear on `DerivedCapability` (stage 5).

**Stage 6b — retire `Provider.footprints` and re-home `validate_calculators`.**
Remove `footprints` from the `Provider` ABC, the Open-Meteo leaf, and `FakeProvider`
(`_build_footprints` stays — it builds the capability's declaration; `FootprintCapability.footprints`
keeps its name). Move `validate_calculators` into `nodes/composition.py`, `source_serves` now reading
`capability.parameters`, and **move its tests to `tests/nodes/test_composition.py`** — inputs served,
unserved input, cycle, and the source-shadowed cycle, all unchanged bar the import. Only then delete
`nodes/reach.py` and `tests/nodes/test_reach.py`, which by this point hold nothing else. Rewrite
`test_provider_footprints_expose_capability_domains` against `capability.reach(pid)`, keeping its
same-object and live-T assertions.

*This is the irreversible cut.* 6a and 6b are separately revertible; everything before them is
additive.

**Stage 7 — wire `validate_calculators` into `compose()`.**
RED: an unproducible calculator input fails `compose()`, not just the unit-tested function. This is
the only stage that changes production behaviour reachable from the surface.

**Stage 8 — the reach is reachable end to end.**
The test the ticket exists for, and the gap session 0015 recorded (*"`nodes/reach.py` is unreachable
production code — unit-tested, no integration coverage"*). RED, through the public surface only:
`compose()` a real profile, then read `gateway.best_view.capability.reach(p)` and assert it is the
expected domain — the same object the provider declared, still live after the clock advances. A second
case asserts a **derived** parameter's reach off the root (wind, via the Calculator), since that
exercises `DerivedCapability` → scoped Arbiter → top Arbiter → `Reservoir` forwarding in one path.
Without this, 003b ships the same "well-tested but never exercised" shape it replaces.

**Stage 9 — docs.** Only the **code** docstrings remain to write: `capability.py` (which currently says
a `Domain` is "deliberately kept **off** the interface" — now false), `arbiter.py`, `domain.py`. Then
tick the ticket boxes and update `docs/tickets/README.md`.

Every prose document is **already at the target state** — architecture.md's `compose()` sequence and
"geometry needs no pass of its own", its Arbiter constructor, module-layout.md's `reach.py` and
`Arbiter(...)` lines, and ADR-0004's scoped-construction example were all amended during planning. So
this stage **verifies** rather than rewrites.

*Note the standing risk this creates:* between now and stage 9 the prose describes code that does not
exist yet — the same drift class that let `compose()` go without its `validate_calculators` call while
three documents asserted it. The difference is that this window is owned by an open ticket rather than
forgotten, and stage 9 is where it closes.

## Rollout, failure handling, observability

- **Migration:** none. No persisted state, no wire format, no config key changes. `OfferingSpec`
  carries no geometry and still won't.
- **Compatibility:** `Provider.footprints` is an internal ABC member with no external implementors;
  v1 ships one provider.
- **Failure handling:** every new failure is a build-time `CompositionError` — the server does not
  start. That is the intent (a misconfigured profile must not serve a wrong envelope). No new
  request-path failure mode: `Arbiter.project` is untouched, and `reach` is never on it.
- **Observability:** none added. The `CompositionError` message *is* the observable, which is why
  its content is an acceptance criterion. Resolution tracing stays
  [#14](../concerns.md#14-resolution-trace-and-observability).
- **Rollback:** stages 0–5 are additive and independently revertible; **6a** and **6b** are the
  irreversible cuts, split so the revert boundary is small; stage 7 is one line.

## Limitations and follow-ups

**Deliberately not built here**

- The **X/Y-first preference** — decided-but-unbuilt; incomparable candidates raise. Trigger: the
  first regional provider.
- **`Domain.intersect`** — declared seam, needed by area products folding X/Y and T jointly.
- **Surface narration** and the omitted-`end` default → [003c](../tickets/003c-request-shaping.md).
- **Node-`Countable`** → [m2](../tickets/m2-dissolve-node-countable.md), immediately after. 003b must
  not deepen what m2 deletes: leave `_source_grid` and the `Countable` isinstance sites alone, and add
  no new reader of a node's `domain`. The order is load-bearing — `CountableFakeProvider` inherits
  `FakeProvider.footprints`, whose assert m2's `EnumerableCapability` reshaping would break; 003b
  deletes that accessor first, so the contradiction never exists. The two need no co-design because
  `Reservoir.capability` forwards its child's, so m2's rewiring leaves the composed object identical.

**Concerns this touches without closing**

- [#32](../concerns.md#32-footprint-aware-ranking-inside-the-algebra) — now live: geometry is inside
  the algebra. 003b must keep `serves` the sole admission authority; the gust deployment is filed
  there as the motivating case for per-request ranking.
- [#33](../concerns.md#33-reconciler-owns-domain-composition) — narrowed, not closed: whether one
  `compose_domains` signature serves `priority` / `tile` / `splice` is unknown until a second
  reconciler exists.
- [#34](../concerns.md#34-producer-dag-walking-is-duplicated) — one of three DAG walks disappears.
  The remaining two still diverge; do not extract preemptively.
- [#36](../concerns.md#36-unserved-and-uncomparable-are-indistinguishable) — unchanged;
  `Domain.matches` stays total.
- [#12](../concerns.md#12-curvilinear-domains) — the source role stays alive, and defect 3 makes it
  slightly more alive than 003a left it.

**Known residue**

- `PriorityReconciler` will hold two members whose only relationship is that both are "policy over
  competing producers" — `select` reads priority, `compose_domains` ignores it. That asymmetry is
  ADR-0007's deliberate choice (coherence over minimalism) and is expected to be revisited by #33.
- `nodes/composition.py` grows to roughly 210 lines. Judged a deeper module rather than a muddier
  one: "everything that turns config into a weavable `ProfileDef`" is one job.
