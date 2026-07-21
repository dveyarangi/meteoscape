# RFC 0004 — Separability narrowing and predicate hygiene

- **Date:** 2026-07-21
- **Ticket:** [m1 — Type contract hygiene](../../tickets/done/m1-type-contract-hygiene.md) — maintenance; unblocks CI (`uv run pyright` is red on `tests/`)
- **Owning decisions:** [ADR-0002](../../adr/0002-data-model.md) · [ADR-0007](../../adr/0007-capability-carries-its-domain.md) · [ADR-0005](../../adr/0005-build-time-composition.md)
- **Concerns:** [#12](../../concerns.md#12-curvilinear-domains) · [#36](../../concerns.md#36-unserved-and-uncomparable-are-indistinguishable)

`pyright` reports **40 errors** in `tests/`, none in `src/`. CI runs bare `uv run pyright` over both,
so main is red. Triage shows the errors are not one problem: a few are real defects the type checker
found, the rest are the `Separable` facet and the Manifold facets **working as designed** — a test
holding a base-typed value and reaching for a refinement's member.

This RFC fixes those defects and clears the type debt, without narrowing any contract that
[#12](../../concerns.md#12-curvilinear-domains) needs left open.

## Scope

**In scope:** one build-time precondition, three under-declared return types, test-site narrowing,
test-fixture repair, and the second wave of errors currently masked by the first.

**Out of scope:** any `Domain` hierarchy change (a `SeparableDomain` intersection ABC was considered
and rejected — see [Rejected](#rejected)); implementing curvilinear geometry; any request-path
behaviour change beyond the `matches` raise; `intersect`, which stays a declared seam.

## The triage

| Cat | Errors | Cause | Disposition |
|---|---|---|---|
| **A** | 18 | `.axis()` on a `Domain` / `EnumerableDomain`-typed value — `Separable` is a facet, not the base | 6 production (Open-Meteo), 12 use-site |
| **B** | 4 | `project()` returns `Manifold`; test wants `Coverage` | use-site — `project` **must** stay closed (ADR-0001) |
| **C** | 9 | facet / union narrowing (`Countable`, `SourceKey`, `AtomicOrigin`, `Reservoir`) | 4 production (`weave`), 5 use-site |
| **D** | 9 | test fixtures typed loosely (`lambda *a: None` as `CombineFn`; indexing `dict[str, object]`) | fixture repair, no design content |

**40 is a floor.** Each error suppresses checking of whatever follows it. One follow-on is visible
statically — [test_mcp_app.py:286](../../../tests/api/test_mcp_app.py) reads `.axis(AxisName.T).count`, and
`.count` exists only on `RegularAxis`, so narrowing the domain reveals a new error there. Category B
unblocks `.ranges` / `.provenance` chains that have never been checked at all. Stage 4 iterates to a
fixed point rather than to a number.

## Boundaries and ownership

| Boundary | File | Change |
|---|---|---|
| `Domain.matches` on both v1 representations | `manifold/domain.py` | **none** — stays total; see [Why `matches` stays total](#why-matches-stays-total) |
| `GridDomain.axis` | `manifold/domain.py` | return type `Axis` → `EnumerableAxis` (under-declared today) |
| `grid` reach rule | `nodes/reach.py` | separability **precondition** at rule entry; private helpers take the narrowed type |
| `Weaver.weave` | `nodes/weaver.py` | return type `Manifold` → `Reservoir` |
| Open-Meteo leaf | `nodes/providers/open_meteo.py` | retain the concrete footprint map it already builds; `capability` returns its actual `FootprintCapability` |
| MCP serializer | `api/mcp_app.py` | delete the guard made unreachable by `GridDomain.axis` |
| `Provider`, `Selection`, `Coverage`, `Capability` | — | **none** — all must stay base-typed ([#12](../../concerns.md#12-curvilinear-domains)) |
| `Domain` hierarchy | `manifold/domain.py` | **none** — no new base class, no facet promoted to subtype |

## Why the contracts do not narrow

Chasing category A to the bottom produced a doc gap worth stating here, because it is the whole reason
this RFC is a test-side change rather than a contract change.

Non-separable geometry has **two independent roles** ([#12](../../concerns.md#12-curvilinear-domains)):
a **source role** (a producer *declares* swath geometry — committed by product pillar 10) and a
**target role** (a caller *asks for* values on swath geometry — committed by Phase 6
forecast-vs-observation verification in **observation space**). Neither implies the other.

`Provider.footprints` and `Coverage.domain` carry the source role; `Selection.domain` carries the
target role. All three are therefore pinned to the base `Domain`, and the 12 category-A use-site
narrowings are correct rather than a workaround: they assert a precondition **local to the grid path**,
which is exactly what [`serialize_coverage`](../../../src/meteoscape/api/mcp_app.py) already does in
production.

**`GridReachRule` narrows its operands, not its result.** ADR-0007 already states that a non-grid
composition *"needs its own rule; a rule that handled it would be wrong for grids"* — grid is **by
definition** the separable rule, so separability is a precondition it may assert on its *inputs*. The
Reach it returns is still one producer's own `Domain`, so `resolve_reach` keeps
`-> Mapping[ParameterId, Domain]` and its two test sites narrow like the rest. Narrowing the return
would need the `SeparableDomain` this RFC [rejects](#rejected); deciding it before 003b — its only
caller — exists would be fixing a contract to a consumer that does not yet make demands.

## Code shapes

### 1. The `grid` rule declares its precondition

#### Why `matches` stays total

An earlier draft of this RFC had `Domain.matches` **raise** on a non-separable operand. That was wrong
twice over and is **not** in scope.

Semantically: `matches` asks *"will I serve this request?"* A representation that cannot determine
whether it covers the request **cannot serve it**, so `False` is the correct answer — not a lossy
collapse of a third "cannot decide" state.

Operationally: [arbiter.py](../../../src/meteoscape/nodes/arbiter.py) iterates candidates and calls
`serves` on each, breaking on the first that admits. A raise there aborts the loop and **fails requests
a later producer could serve** — a regression in the degrade path. `UnionCapability.serves` (`any(...)`)
and `DerivedCapability.serves` (`all(...)`) have the same exposure. What `False` costs is *diagnosis*,
not correctness, and that belongs to the resolution trace
([#36](../../concerns.md#36-unserved-and-uncomparable-are-indistinguishable),
[#14](../../concerns.md#14-resolution-trace-and-observability)).

#### The one site that does change

`GridReachRule` is different: **build time, one caller, no fallback.** Its `_contains` returning `False`
for a candidate it cannot compare is individually correct, but the *rule* then concludes *"no candidate
dominates → incomparable footprints, X/Y preference unbuilt"* — an explanation pointing at an unbuilt
feature that has nothing to do with the operator's actual mistake, which is pairing a curvilinear
producer with a rule defined over separable geometry. Worse, `_split` is reached first and its bare
`assert` at [reach.py](../../../src/meteoscape/nodes/reach.py) throws `AssertionError` before the message
is ever produced.

The fix is a **precondition at the rule's entry**, not a changed return type — the check moves **out of
`_contains` and up**, where it can name the offending producer:

```python
class GridReachRule:
    def reach(self, candidates: Sequence[tuple[ProducerKey, Domain]]) -> Domain:
        for key, domain in candidates:
            if not isinstance(domain, Separable):
                raise CompositionError(
                    f"grid reach rule cannot compare non-separable footprint from {key}; "
                    f"grid requires separable geometry"
                )
```

`_contains` / `_split` / `_incomparable` / `_contained_in_all` then take the narrowed operand type, and
the two `isinstance` calls plus the bare `assert` at [reach.py:30](../../../src/meteoscape/nodes/reach.py)
are deleted. That `assert` is a live defect: on the current path a curvilinear candidate reaches
`_split` and raises `AssertionError`, not `CompositionError`.

### 2. Honest return types

Four signatures are narrower in fact than in declaration. Narrowing them is free: it kills 10 of the 40
errors, both existing `# type: ignore` suppressions, and one dead runtime guard. All four are
**covariant return narrowing on a concrete implementation** — the abstract declarations are untouched,
so no caller that holds the base type is affected.

| Signature | Today | Truth |
|---|---|---|
| `GridDomain.axis` | `-> Axis` | `axes` is already `Mapping[AxisName, EnumerableAxis]` |
| `Weaver.weave` | `-> Manifold` | literally `return Reservoir(...)`; ADR-0005 states the root **is** the best-view `Reservoir` |
| `OpenMeteoProvider.footprints` | `-> Mapping[ParameterId, Domain]` | `_build_capability` builds `FootprintDomain` values |
| `OpenMeteoProvider.capability` | `-> Capability` | `self._capability` **is** a `FootprintCapability`; the property widens it away |

`GridDomain.axis` makes [mcp_app.py](../../../src/meteoscape/api/mcp_app.py)'s
`if not isinstance(t_axis, EnumerableAxis): raise TypeError` structurally unreachable — delete it.

Open-Meteo needs care: the concrete type is currently **lost in transit**. `_build_capability` builds
`dict[ParameterId, tuple[ParameterDef, FootprintDomain]]`, hands it to `FootprintCapability` (whose
field is `Mapping[..., tuple[ParameterDef, Domain]]`), and `footprints` reads it back already widened.
The provider retains the map it built; the `Capability` widens it for the algebra. That is the right
direction anyway — the Capability is the **abstract advertisement**, the provider knows its own
geometry concretely. Object identity must be preserved: `test_provider_footprints_expose_capability_domains`
asserts `domain is cap_domains[pid]`.

Narrowing `capability` on the same leaf removes the only two `# type: ignore[attr-defined]` in the
suite — `test_open_meteo.py:194` / `:212` read `provider.capability.footprints`, which `Capability`
does not declare — with **no test edit at all**. `FakeProvider` is deliberately not changed:
[fakes.py](../../../tests/fakes.py) accepts any `Capability` by construction, so its internal
`assert isinstance(..., FootprintCapability)` is a genuine narrowing and stays.

### 3. Use-site narrowing

House idiom, already used in both `src` ([`serialize_coverage`](../../../src/meteoscape/api/mcp_app.py))
and `tests` (`assert isinstance(z, IntervalAxis)`): narrow inline to the concrete representation.

```python
selection = build_selection(...)
assert isinstance(selection.domain, GridDomain)   # this test exercises the grid path
assert selection.domain.axis(AxisName.X).extent.lower == pytest.approx(13.41)
```

Rejected alternatives: an `axis_of(domain, name)` helper in `tests/fakes.py` (hides the precondition
and makes tests stop resembling the code under test), and narrowing to `Separable` rather than the
concrete class (`Separable.axis` returns bare `Axis`, so most sites need a second narrowing anyway).

The same idiom covers category C, and there the production precedent is exact:
[`weaver.py:29`](../../../src/meteoscape/nodes/weaver.py) already writes
`assert isinstance(registered.provider, Countable)` before reading `provider.domain`, because
`Provider` declares no `domain` — countability is the `Countable` facet. The tests reach for the same
member and narrow the same way.

Two sites need restructuring rather than a bare assert: `test_arbiter.py:60` and `test_weaver.py:117`
read `provider.domain` inside a comprehension, where an `assert` cannot be placed — extract a loop or a
narrowing helper local to the test.

### 4. Fixture repair (category D)

- `CalculatorManifest(fn_id="wind_uv", fn=lambda *a: None)` — `CombineFn` returns
  `tuple[EnumerableDomain, Mapping[ParameterId, ParameterData]]`. Six sites; replace with one shared
  correctly-typed stub in the test module.
- `serialize_coverage` returns `dict[str, object]`; the test indexes two levels deep. Narrow the read
  at the test (`block = payload["air_temperature"]; assert isinstance(block, dict)`) rather than
  introducing a `TypedDict` — the payload's parameter keys are dynamic.

## Errors

| Condition | Raised | Where |
|---|---|---|
| non-separable candidate footprint at the `grid` rule | `CompositionError` naming the producer | `nodes/reach.py` |

One site, build-time only. It replaces an `AssertionError` behind a misleading `CompositionError`. Not
reachable in v1 — no v1 representation is non-separable — so it guards the seam rather than changing
observable behaviour today. `Domain.matches` raises nothing; see
[Why `matches` stays total](#why-matches-stays-total).

## Invariants

- No contract narrows below `Domain` on either side of `project`
  ([#12](../../concerns.md#12-curvilinear-domains) source **and** target roles).
- `project` stays closed: `Manifold -> Manifold` (ADR-0001). Category B narrows at the use site only.
- `Separable` stays a structural facet — no new base class, no facet promoted to a subtype.
- Object identity between `Provider.footprints` and `Capability.footprints` values is preserved.
- `uv run pyright` reports **0 errors** across `src` and `tests`; no `# type: ignore` is added, and the
  two that exist (`test_open_meteo.py:194` / `:212`) are removed rather than carried.

## Stages (TDD — red → green → refactor per stage)

1. **Docs** — ✅ done: [#12](../../concerns.md#12-curvilinear-domains) split into source/target roles,
   [#36](../../concerns.md#36-unserved-and-uncomparable-are-indistinguishable) filed as a diagnosability
   seam, ADR-0002 amended (admission total, build-time rules raise), architecture index updated.
2. **The `grid` precondition** — test first: reuse the `_NonSeparable(Domain)` stub at
   `tests/manifold/test_domain.py:315` to assert `CompositionError` naming the producer from
   `GridReachRule.reach`. Then the check at the rule's entry, then narrow the private helpers and
   delete the two `isinstance` calls and the bare `assert`.
   ✅ `test_domain.py:322`'s `footprint.matches(_NonSeparable()) is False` **stays as-is** — `matches`
   is unchanged.
3. **Honest return types** — the three narrowings; delete the unreachable guard in `mcp_app.py`.
4. **Type debt sweep** — use-site narrowing (categories A-remainder, B, C-remainder), fixture repair
   (D), then re-run and clear the second wave. Iterate to zero.

Commit split: `docs:` (stage 1) → `fix:` (stage 2, the only behaviour change, reviewable alone) →
`chore:` (stages 3–4).

## Rejected

- **`SeparableDomain(Domain)` — a named intersection ABC.** Would delete ~25 narrowing sites including
  production, and make `Provider.footprints` / `Coverage.domain` / `Selection.domain` read honestly.
  Rejected: those four signatures are **precisely and exhaustively** where curvilinear geometry enters
  the system, so narrowing them does not preserve the facet at a boundary — it deletes
  [#12](../../concerns.md#12-curvilinear-domains), spread across four signatures instead of one base
  class, which is the worst version because the deletion is invisible. Also promotes a facet to a
  subtype and forces a diamond with `EnumerableDomain`.
- **Hoisting `axis()` onto `Domain`.** Deletes the facet outright; contradicts ADR-0002 and forecloses
  [#12](../../concerns.md#12-curvilinear-domains).
- **Relaxing pyright config to exclude `tests`.** Would hide the real defects this triage found.
- **Suppressing with `# type: ignore`.** Every error here is either a real defect or a legitimate
  precondition worth stating; none is a checker limitation.

## Out-of-scope follow-ups

- **Curvilinear implementation itself** ([#12](../../concerns.md#12-curvilinear-domains)) — both roles;
  the target role additionally requires `resample` to sample onto an arbitrary point set, materially
  wider than [#5](../../concerns.md#5-read-time-homogenization-fidelity) scopes.
- **Skip diagnosability** ([#36](../../concerns.md#36-unserved-and-uncomparable-are-indistinguishable)) —
  the Arbiter skips an uncomparable candidate exactly as it skips an uncovering one, and the operator
  sees one message for both. A reason code on the resolution trace
  ([#14](../../concerns.md#14-resolution-trace-and-observability)) is the fix; nothing here addresses it.
- **`Interval[C]` generic invariance** — the `# type: ignore[arg-type]` on `.extent.contains(...)` is a
  separate problem (a constrained-typevar comparison across two `Interval` instances) and is untouched.
