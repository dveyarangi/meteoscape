# m2 — Dissolve node-`Countable`

- **Status:** Done (maintenance)
- **Depends on:** [003b — Capability carries its domain](./003b-capability-domain.md) — shares the
  files (`weaver.py`, `composition.py`, `tests/fakes.py`) and reads geometry off the `Capability`,
  which 003b publishes.
- **Blocks (soft):** [006 — Retentive store](../006-retentive-store-freshness.md) assumes the `Store`
  has **no public `domain`**; without this ticket 006 would have to do this dissolution itself.
- **Owning decision:** [ADR-0006](../../adr/0006-materialization-granularity-and-store-shape.md) —
  *"Nodes are not `Countable`; `domain` lives only on the Coverage"* — already accepted; the code
  below predates it. One **delta beyond the ADR**: ADR-0006 still hands a provider-exact lattice to
  the `StoreFactory`; this ticket removes the store entirely for a materialized provider (see Why).
- **Outcome:** `Countable` is a **result** facet only. `Provider`, `Store`, and `Reservoir` are not
  node-`Countable`; a Store's lattice flows **in** through `StoreFactory.create` and stays private; a
  materialized provider wires **storeless**. `Coverage`/`CoverageRecord` are untouched.

## Why

The decision is already made and the code contradicts it.
[ADR-0006](../../adr/0006-materialization-granularity-and-store-shape.md): *"Nodes are not `Countable`;
`domain` lives only on the Coverage"* — a provider-exact lattice is a build-time declaration, the
quantize target is internal to the `Store`, and the loosened-node-`Countable` alternative was
explicitly rejected as a vestigial face. [architecture.md](../../architecture.md) ("Manifold algebra")
concurs: *"A node exposes no public lattice … the only public `domain` is a materialized
`Coverage`'s."* The [glossary](../../glossary.md) lists *Node-Countable* under `_Avoid_`. Yet `Store` is
declared `Countable` (`nodes/store.py`), `Reservoir` forwards `store.domain` publicly
(`nodes/reservoir.py` — zero readers in `src`), and `Weaver._source_grid` reads `provider.domain` off
a `Countable` provider.

**The one step past ADR-0006:** the ADR kept `Reservoir(store, provider)` for a provider-exact
lattice, handing it to the `StoreFactory`. This ticket concludes the materialized provider needs **no
store at all**:

a survey of countable-provider candidates found exactly one category — **an already-materialized
local dataset** (archive bundle, climatological normals, static fields like DEM / land-sea mask) —
and for all of them *the provider is already the store*: wrapping it in `Reservoir(store, provider)`
builds a full mirror of data that is already local. Cloud ARCO archives and station networks are
enumerable in principle but unholdable or unbounded in practice, so countability buys them nothing.
The `SourceBinder` invariant "Countable ⇒ `store is None`" already states the conclusion; the Weaver
currently draws the opposite one.

**Consequence — the provider-exact lattice channel closes.** With no `Countable` provider, nothing
ever hands an `EnumerableDomain` to the factory, so `StoreFactory.create` narrows to
`StoreSpec` (the `None` arm has no caller either — `ProfileDef.root_store` is always a
`StoreSpec`). A capability cannot substitute as the channel: a non-materialized provider's
reach is **continuous** (`FootprintCapability` — no grid to read), and the only enumerable-reach
providers are materialized and wire storeless. The catalogue's `OfferingSpec.store` (authored beside
the manifest by whoever knows the vendor grid) is the sole lattice channel; the lattice
*representation* is [006](../006-retentive-store-freshness.md)'s decision. The
remote-but-enumerable residual (cloud ARCO, worth caching) stays with open question 2 /
[#37](../../concerns.md#37-storeless-materialized-producers-and-read-back-homogenization).

After [ADR-0007](../../adr/0007-capability-carries-its-domain.md), "already materialized" is a
**capability fact**, not a node facet: a provider whose capability is an `EnumerableCapability` (every
parameter on one enumerable domain) *is* a materialized dataset. This also closes a live drift
surface: `CountableFakeProvider` takes `capability=` and `domain=` as independent constructor
arguments that can disagree; reading materialized-ness off the capability makes disagreement
unrepresentable.

## What to build

| Site | Change |
|---|---|
| `nodes/reservoir.py` — `Reservoir.domain` | **Delete.** Zero readers in `src`; exists only to satisfy node-`Countable`. |
| `nodes/store.py` — `Store(Manifold, Countable, Writable)` | → `(Manifold, Writable)`. The lattice flows in via `StoreFactory.create(grid)` and is private after (its **Lattice**, [glossary](../../glossary.md)). `StubStore.domain` and `_STUB_DOMAIN` go. |
| `nodes/providers/base.py` — `Provider` | No `Countable` implementations; a materialized provider declares an `EnumerableCapability`. |
| `nodes/weaver.py` — `_source_grid` | **Delete.** A materialized provider wires as `Producer(node=provider, key=...)` — no `Reservoir`, no store allocation. |
| `nodes/store.py` — `StoreFactory.create` | Signature narrows: `EnumerableDomain \| StoreSpec \| None` → `StoreSpec`. `_source_grid` was the `EnumerableDomain` arm's only caller (see Why — the channel closes), and no caller passes `None` (`ProfileDef.root_store` is always a `StoreSpec`; Source stores are loud-required). |
| `nodes/composition.py` — `SourceBinder` | Same invariant, read off the capability: `isinstance(provider.capability, EnumerableCapability)` ⇒ `store is None`. **Loud in both directions** (aligned 2026-07-24): a *configured* store on a materialized offering raises `CompositionError` — mirror of the missing-store error (which rewords to "non-materialized") — never a silent discard. |
| `manifold/core.py` — `Countable` docstring | Keep only the **result** reading (matches glossary and architecture.md); drop the "a *node* uses its `domain` as the canonical lattice" sentence. |
| `manifold/core.py` — `Coverage(Manifold, Countable)` | **Unchanged.** Result-Countable is load-bearing (`sampling.resample` reads `coverage.domain`). |
| `tests/fakes.py` — `CountableFakeProvider` | **Delete the subclass** (aligned 2026-07-24 — with `domain=` gone it has no remaining member). A materialized fake is `FakeProvider(capability=EnumerableCapability(...))`; disagreement is unrepresentable because there is no second class to disagree. The factory's `countable=` flag renames to `materialized=`. |

## Docs to sync (land with the code)

- [ADR-0006](../../adr/0006-materialization-granularity-and-store-shape.md) — the "Nodes are not
  `Countable`" bullet: *"a provider-exact lattice is a build-time declaration handed to the
  `StoreFactory` at weave (construction face)"* — amend to record this ticket's delta: a materialized
  provider wires **storeless**, so no provider hands a lattice to the factory; `StoreSpec` is the
  factory's only provisioning input.
- [architecture.md](../../architecture.md) §Store — *"provisioned from either a provider-exact lattice
  declaration (build-time construction face) or a `StoreSpec` configured guess"* → `StoreSpec` only.
- [architecture.md](../../architecture.md) §Provider — *"A vendor-declared native lattice is a
  build-time declaration handed to the `StoreFactory` at weave"* → replace: a provider whose data is
  already materialized declares an `EnumerableCapability` and wires storeless.
- [architecture.md](../../architecture.md) §Config, binders, Weaver — *"a provider-declared lattice
  reaches the factory through the build-time construction face"* → drop; every Source carries a
  `StoreSpec`.
- `config.py` — `StoreSpec` and `OfferingDef.store` docstrings say *"non-Countable Source"* → reword
  to *"non-materialized Source"* (aligned 2026-07-25 — the last stale node-`Countable` term in `src`,
  mirrors the binder-message reword).
- **Further stale sites found by the sync-arch pass (2026-07-25), beyond the original list:**
  [ADR-0005](../../adr/0005-build-time-composition.md) — the Source-store-binding **flowchart** still
  branched on "Provider declares a native lattice?" and `create(declared lattice | StoreSpec | None)`;
  its `OfferingSpec.default_lattice` rejection rationale; "source lattice" in the binder bullet; the
  rejected-option "provider-exact or a per-source guess". [ADR-0001](../../adr/0001-manifold-algebra-and-composition.md)
  — the no-public-lattice bullet's "provider-exact where a vendor declares one … build-time
  declaration at weave". [ADR-0002](../../adr/0002-data-model.md) — the declared-grid aside
  "provider-exact where a vendor declares a lattice". [v1-requirements](../../v1-requirements.md) —
  two "provider-exact or a configured guess" phrases. [concerns #27](../../concerns.md#27-stored-calculator-store-binding)
  — quoted the old binder message. All synced 2026-07-25.
- **Unchanged on purpose:** §Source, guiding principles, and the glossary **Source** entry keep
  "a Source is `Reservoir(store, Provider)`" — true for every v1 source (the storeless path exists
  only in fakes); their widening waits for the first real materialized provider →
  [#37](../../concerns.md#37-storeless-materialized-producers-and-read-back-homogenization).

## Open questions

1. **Read-back homogenization for storeless materialized producers.** Dropping the per-source
   `Reservoir` also drops its read-back homogenization, and
   [architecture.md](../../architecture.md) ("Reservoir") is explicit that homogenization is *not*
   leaf-only. A materialized provider asked an off-grid request must homogenize itself — shared
   `sampling` machinery, but its placement (in the provider base? a thin non-retentive wrapper?) is
   undecided → [#37](../../concerns.md#37-storeless-materialized-producers-and-read-back-homogenization).
   No v1 driver: no v1 provider is materialized.
2. **The discriminator.** Is `isinstance(provider.capability, EnumerableCapability)` the right test
   for "already materialized", or does that deserve an explicit declaration once a provider is both
   huge and enumerable (the ARCO case, where enumerable ≠ holdable)? v1 answer: the isinstance test;
   revisit with the first real materialized provider.

## Acceptance criteria

- [x] No node type satisfies `Countable`: `isinstance` checks against `Store`, `Reservoir`, and every
      `Provider` fail; `Coverage` / `CoverageRecord` still satisfy it and `resample` is unchanged
      (`tests/manifold/test_core.py`).
- [x] `Reservoir` has no `domain` member; the `Store` protocol has no `domain` member; the lattice
      reaches a store only through `StoreFactory.create`.
- [x] A materialized provider (fake) wires storeless (`test_materialized_source_weaves_storeless`)
      and serves through the Arbiter (`test_materialized_source_serves_through_arbiter`, on-grid per
      [#37](../../concerns.md#37-storeless-materialized-producers-and-read-back-homogenization)); the
      `SourceBinder` invariant holds read off the capability — loud both ways
      (`test_store_configured_on_materialized_source_raises`, `test_missing_store_raises`).
- [x] `CountableFakeProvider` no longer exists; the materialized fake is a plain `FakeProvider`
      carrying an `EnumerableCapability`.
- [x] Doc sync landed (see "Docs to sync"): ADR-0006's construction-face clause amended; no doc
      sentence still hands a provider lattice to the `StoreFactory` (2026-07-25 sync-arch pass).
- [x] `pyright` clean (0 errors), `pytest` green (151), `ruff` clean. No new `# type: ignore`.

## Out of scope

- The retentive `Store` itself and the lattice representation — [006](../006-retentive-store-freshness.md).
- Off-grid homogenization kernels — [007](../007-off-grid-homogenization.md) / [#5](../../concerns.md#5-read-time-homogenization-fidelity).
- Any real materialized provider (archive bundle, normals, static fields) — post-v1.
