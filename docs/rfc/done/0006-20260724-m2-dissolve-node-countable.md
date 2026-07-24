# RFC 0006 · 2026-07-24 · Dissolve node-`Countable` — implementation plan

Implementation plan for [m2](../tickets/done/m2-dissolve-node-countable.md), owned by
[ADR-0006](../adr/0006-materialization-granularity-and-store-shape.md) (the decision the code
predates) with one delta beyond it (storeless materialized providers). **Living document** — being
built up during the 2026-07-24 align session; decisions land here as they crystallise.

**Scope in one line:** `Countable` becomes a **result** facet only — `Store`, `Reservoir`, and
`Provider` lose it; a materialized provider (declared by `EnumerableCapability`) wires storeless as a
bare `Producer`; the provider-exact lattice channel closes and `StoreFactory.create` narrows to
`StoreSpec`.

## Boundaries involved

| Boundary | Owner | What m2 does to it |
|---|---|---|
| `Countable` facet | [ADR-0001](../adr/0001-manifold-algebra-and-composition.md), [ADR-0006](../adr/0006-materialization-granularity-and-store-shape.md) | **Narrows to result-only** — docstring drops the node-lattice sentence; `Coverage(Manifold, Countable)` unchanged (`resample` reads `coverage.domain`). |
| `Store` protocol | [ADR-0006](../adr/0006-materialization-granularity-and-store-shape.md) | **Narrows** — `(Manifold, Countable, Writable)` → `(Manifold, Writable)`; `StubStore.domain` and `_STUB_DOMAIN` deleted. |
| `Reservoir` | [ADR-0001](../adr/0001-manifold-algebra-and-composition.md) | **Narrows** — `domain` deleted (zero readers in `src`); "Countable by delegation" docstring goes. |
| `StoreFactory.create` | [ADR-0006](../adr/0006-materialization-granularity-and-store-shape.md), [ADR-0005](../adr/0005-build-time-composition.md) | **Narrows** — `EnumerableDomain \| StoreSpec \| None` → `StoreSpec`. The `EnumerableDomain` arm's only caller was `_source_grid` (deleted); no caller passes `None` (`ProfileDef.root_store` is always a `StoreSpec`). |
| `SourceBinder` invariant | [ADR-0005](../adr/0005-build-time-composition.md) | **Rereads** — discriminator moves from `isinstance(provider, Countable)` to `isinstance(provider.capability, EnumerableCapability)`; loud `CompositionError` in **both** directions (see decisions). |
| `Weaver._weave_providers` | [ADR-0005](../adr/0005-build-time-composition.md) | `_source_grid` deleted; a materialized source wires `Producer(node=provider, key=...)` — no `Reservoir`, no store allocation. |
| `Provider` ABC | [ADR-0004](../adr/0004-producer-resolution-and-capability.md) | No implementation is node-`Countable`; materialized-ness is a capability fact. |
| Doc set | ADR-0006, [architecture.md](../architecture.md) | Amended with the code — the ticket's "Docs to sync" section enumerates the sites. |

**Ownership rule preserved:** `errors, parameters, clock, identity ← manifold ← nodes`; nothing in
`manifold/` learns about stores or binding.

## Design decisions (aligned 2026-07-24)

1. **The provider-exact lattice channel closes — deliberately.** A capability cannot substitute as a
   lattice source: a non-materialized provider's reach is *continuous* (`FootprintCapability` — no
   grid to read), and the only enumerable-reach providers are materialized and get no store. The
   declaration channel is the catalogue's **`OfferingSpec.store`** (a `StoreSpec` authored beside the
   manifest by whoever knows the vendor grid), overridable per profile by `OfferingDef.store` —
   **already built** (`composition.py`: `offering.store if ... else spec.store`). No new config
   surface. The lattice *representation* is [006](../tickets/006-retentive-store-freshness.md)'s
   decision; the enumerable-but-unholdable residual (cloud ARCO) stays with the ticket's open
   question 2 / [#37](../concerns.md#37-storeless-materialized-producers-and-read-back-homogenization).
2. **The `SourceBinder` invariant is loud in both directions.** A configured store on a materialized
   offering raises `CompositionError` (an operator believing something false about the deployment),
   mirroring the missing-store error for a non-materialized source — which rewords from
   "non-Countable" to **"non-materialized"**. Never a silent discard; matches every other operator
   contradiction in `composition.py` (dangling `secret_ref`, duplicate keys) and
   [#27](../concerns.md#27-stored-calculator-store-binding)'s proposed rule.
3. **Doc sync lands with the code** — ADR-0006's construction-face clause amended; three
   architecture.md sentences stop handing a provider lattice to the factory; §Source / glossary
   **Source** deliberately *unchanged* (true for every v1 source; widening deferred to
   [#37](../concerns.md#37-storeless-materialized-producers-and-read-back-homogenization)'s trigger).
   Site list: the ticket's "Docs to sync" section.
4. **`CountableFakeProvider` is deleted, not reshaped.** With `domain=` gone the subclass has no
   remaining member; a materialized fake is `FakeProvider(capability=EnumerableCapability(...))`.
   Strictly stronger than the ticket's original "reshape": capability/domain disagreement is
   unrepresentable because there is no second class to disagree. The fake factory's `countable=`
   flag renames to `materialized=`.

## Code shapes

### `nodes/composition.py` — `SourceBinder` (decision 2)

```python
def _is_materialized(provider: Provider) -> bool:
    """Every parameter on one enumerable domain ⇒ an already-materialized dataset (ADR-0006 / m2)."""
    return isinstance(provider.capability, EnumerableCapability)

# in SourceBinder.build — resolve the store once, then branch (simplify pass, 2026-07-25):
store: StoreSpec | None = offering.store if offering.store is not None else spec.store
if _is_materialized(provider):
    if store is not None:
        raise CompositionError(
            f"store configured for materialized source {key}; a materialized provider wires storeless"
        )
elif store is None:
    raise CompositionError(f"missing store shape for non-materialized source {key}")
```

`RegisteredSource` invariant docstring rewords to: *materialized (EnumerableCapability) ⇒ `store is
None`; non-materialized ⇒ `store` set* — both enforced here, so downstream reads `store is None` as
the materialized fact without re-deriving it.

### `nodes/weaver.py` — `_weave_providers` (`_source_grid` deleted)

```python
def wire_source(registered: RegisteredSource, stores: StoreFactory) -> Manifold:
    """Storeless bare Provider when materialized; else `Reservoir(store, Provider)`."""
    if registered.store is None:
        return registered.provider
    return Reservoir(stores.create(registered.store), registered.provider)

# Weaver._weave_providers:
return [
    Producer(node=wire_source(registered, self.stores), key=key)
    for key, registered in profile.sources.sources.items()
]
```

No capability re-check in the Weaver — `registered.store is None` *is* the materialized fact, owned
by the binder invariant (single authority; no drift between two readers). `wire_source` is
module-level (simplify pass, 2026-07-25) so test wiring (`test_arbiter._producers`) calls the same
rule instead of mirroring it — when [#37](../concerns.md#37-storeless-materialized-producers-and-read-back-homogenization)'s
homogenization wrapper lands here, the Arbiter tests follow automatically.

### `nodes/store.py` — narrowed protocol and factory

```python
class Store(Manifold, Writable, Protocol):
    ...  # docstring drops the "capability = held vs domain = could hold" contrast

class StoreFactory:
    def create(self, spec: StoreSpec) -> Store: ...  # param renamed: it is a spec, not a grid
```

## Open items (appended as the align session surfaces them)

- **Storeless fakes must be exercised on-grid only** — a storeless producer asked an off-its-grid
  enumerable Selection would need self-homogenization, whose placement is
  [#37](../concerns.md#37-storeless-materialized-producers-and-read-back-homogenization) (open, no
  v1 driver). Tests for the storeless path pin their Selections to the fake's declared domain.

## Implementation stages (per /tdd — vertical slices; deletions ride the existing suite)

**Stage 0 — fake dissolution (pure test-side refactor, suite stays green).** Delete
`CountableFakeProvider`; `fake_catalog`'s `countable=` → `materialized=`, building
`FakeProvider(capability=EnumerableCapability(domain=sample_lattice(...), parameters=...))`. The two
tests whose premise is the dissolved node-`Countable` path — `test_countable_provider_drops_store`
and `test_countable_source_passes_provider_domain` — are **retired here** (their store-dropping
behavior returns keyed off capability as the Stage 1 / Stage 2 RED tests), and their now-unused
`Countable` import goes. No production code touched; the rest of the suite staying green proves the
fakes carried no behavior of their own.

**Stage 1 — binder invariant, loud both directions (new behavior).**
- RED: `SourceBinder` raises `CompositionError` for a *configured* store on a materialized offering
  (message names the source and says storeless); missing-store message says "non-materialized".
  Fixture built inline — `fake_catalog(materialized=True, offerings={"default":
  OfferingSpec(..., store=SAMPLE_STORE)})` — so provider capability (`EnumerableCapability`, from
  `materialized=True`) and the store knob (`spec.store`) stay orthogonal; no `store=` factory knob.
- GREEN: the discriminator branch from Code shapes — `isinstance(provider.capability,
  EnumerableCapability)`; `manifold.core.Countable` import leaves `composition.py`.

**Stage 2 — storeless wiring (new behavior).**
- RED: a materialized fake weaves as a bare `Producer` (no `Reservoir` wrapper, no
  `StoreFactory.create` call for it — spy factory) and serves an on-grid request through the
  Arbiter end-to-end.
- GREEN: `_weave_providers` from Code shapes; `_source_grid` deleted.

**Stage 3 — facet removal (contract tests + existing suite as the net).**
- RED: the ticket's acceptance `isinstance` tests — no `Store` / `Reservoir` / `Provider` satisfies
  `Countable`; `Coverage` / `CoverageRecord` still do and `resample` is unchanged.
- GREEN: `Store` → `(Manifold, Writable)`; delete `Reservoir.domain`, `StubStore.domain`,
  `_STUB_DOMAIN`; narrow `StoreFactory.create(spec: StoreSpec)`; drop the node sentence from the
  `Countable` docstring; reword `store.py` / `reservoir.py` docstrings; reword `config.py`
  `StoreSpec` / `OfferingDef.store` docstrings ("non-Countable Source" → "non-materialized Source").
  `pyright` guards the signature narrowing across call sites.

**Test-side fallout (rides Stages 1–3; not a separate stage).** Three existing tests read members
this RFC deletes and are rewritten in the stage that deletes each: `test_countable_provider_drops_store`
and `test_countable_source_passes_provider_domain` (assert `isinstance(provider, Countable)` /
`provider.domain`) become the materialized-storeless assertions of Stages 1–2; `test_single_source_weaves…`
drops its `root.domain` assertion (the best-view `Reservoir` loses `domain`) in Stage 3.
`RecordingStoreFactory.create` and its `calls` list narrow `EnumerableDomain | StoreSpec | None` →
`StoreSpec` with the factory (Stage 3, `pyright`-guarded). The simplify pass (2026-07-25) then
consolidated the duplicated fixtures into `tests/fakes.py`: one `RecordingProvider` (capability
defaults to the held coverage's — the materialized shape; the arbiter tests override it) and one
`coverage_record(*pids, domain=…, value=…)` builder, replacing three per-file copies.

**Stage 4 — doc sync (DOCS commit, paired).** The ticket's "Docs to sync" section: ADR-0006
construction-face amendment; architecture.md §Store / §Provider / §Config; §Source and glossary
deliberately untouched (→ #37).

No migration/rollout/observability surface: build-time-only reshape, no persisted state, no wire
format; failure handling is the two `CompositionError`s of Stage 1.
