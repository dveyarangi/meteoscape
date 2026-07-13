# 0007 · 2026-07-11 · Phase A — weave-the-graph plan (align session)

Continues [session 0006](./0006-20260711-namespace-polish.md). Grilled the Phase A scope of
[issue 001](../tickets/done/001-walking-skeleton.md) — the build seam
(`OfferingDef` → `SourceBinder` → `SourceRegistry` → `ProfileDef` → `Weaver`), reshaped across
sessions 0003–0006 and never executed. This doc records the decisions and the TDD implementation
plan. Weaving is **pure construction, not projection**: Phase A exercises every node's *built face*
(constructors, `capability` — the dual of `project`); the runtime face (`project`) is Phase C.

## Decisions

- **Weaver allocates every `Store`, via an injected concrete `StoreFactory`** — today
  `create` returns `StubStore` (ignores lattice). The Weaver owns *where* stores exist; the
  factory owns *what* a store is. Retentive factory lands at 006. Stores arriving live in `ProfileDef`
  **rejected** — recorded in [ADR-0005](../adr/0005-build-time-composition.md).
- **`StubStore`** lives in `nodes/store.py` beside the `Store` protocol — weave-time placeholder (no
  retention; `domain` / `project` / `capability` raise; `assimilate` no-op). `Store` moved out of
  `reservoir.py` (which keeps only `Reservoir`). The declared-grid representation question is filed on
  [issue 006](../tickets/006-retentive-store-freshness.md).
- **Fake provider is a test fixture only** (`tests/fakes.py`): declared `FootprintCapability` +
  `CadenceDef` + `source_key`; `project` raises. The production `ProviderCatalog` holds only real
  vendors — empty until Phase C registers Open-Meteo.
- **Composition root** (`server.py`): module-level `PROVIDER_CATALOG` dict literal (vendor modules
  each export a `MANIFEST`; the root assembles — data, not logic), and
  `compose(profile: ProfileConfig, catalog, secrets, clock, stores: StoreFactory) → Gateway` — the
  fixed call sequence (binders → `ProfileDef` → `weave` → `Gateway`), no branches. `main()` projects
  `Settings` and calls `compose` with the real catalogue + `StoreFactory()`, so production
  runs the same code path the tests prove. `compose` takes `ProfileConfig` (not `Settings`) so tests
  never touch env.
- **The binder is strict; degrade is `Settings`' job.** Every `OfferingDef` that reaches
  `SourceBinder.build` is explicit operator intent: unknown `impl`, unknown offering `name`, dangling
  `secret_ref`, duplicate `SourceKey`, or unresolvable source lattice (non-`Countable` provider, no
  `default_lattice`) → **`CompositionError`** at startup. Graceful degrade (absent TWC key) happens
  where enablement lives — `Settings` never emits the def
  ([v1-requirements](../v1-requirements.md) and issue 008 updated).
- **`CompositionError`** is the build-time error category, defined in `nodes/composition.py` — *not*
  `errors.py`, which stays the request-path taxonomy adapters map to protocol errors. `CycleError`
  (002b) will subclass it.
- **Expand path deferred**: `OfferingDef(name=None)` → `NotImplementedError` (declared-but-unbuilt
  seam, not operator error). No v1 provider expands.
- **`Settings.calculators()` returns `()` until 002b** — the wind `CalculatorSpec`s move in with the
  slice that can bind them (enablement must not name what the process can't serve).
  `CalculatorBinder.build` is **implemented now** (strict lookup; the empty case runs real code).
- **`open_meteo_enabled` defaults to `False` during the A–B window**, flipping to `True` in Phase C
  when the Open-Meteo manifest registers. Strictness stands: enabled-but-unregistered impl is a
  startup error.
- **The empty weave is legal**: zero sources → zero-candidate Arbiter under the root `Reservoir`,
  empty capability envelope. "Nothing enabled" is valid degraded config; it is also the Phase A
  smoke-test path.
- **`Gateway.resolve` implemented now** (one-line pass-through to `best_view.project`).
- **`Arbiter` validates `ArbiterPolicy.default_reconciler == "priority"`** — anything else →
  `CompositionError` (the interpreter refuses programs it can't execute; keeps wired-but-unbuilt
  reconcilers loud). Weaver builds `SourceKey → Reservoir` and passes the map + raw `SourceRegistry`
  into the Arbiter — **no priority ranking in the Weaver**. A non-empty `CalculatorRegistry` at weave →
  `NotImplementedError` until 002b.
- **Test stance**: assertions ride the built face — registry values, `capability.parameters`
  (Reservoir forwards → Arbiter unions), factory call records — never isinstance-walks of internals.
  Priority ordering is asserted on `Arbiter` directly (reconciler owns it).

## Implementation plan (TDD — one test → one implementation, vertical)

Fixtures first (no test): `tests/fakes.py` — `FakeProvider` (serves `AIR_TEMPERATURE`;
`FootprintCapability` with `ContinuousAxis` X/Y/Z + `RollingAxis` T from a `CadenceDef` +
`StoppedClock`; `project` raises), a fake `ProviderManifest`/catalogue builder, a recording
`StoreFactory`.

**`SourceBinder` (`tests/test_composition.py`)**

1. One declared `OfferingDef` binds → `SourceRegistry` keyed by
   `SourceKey(manifest.provider_id, offering.name)`; provider built via `manifest.build(spec,
   settings, secret, clock, parameters)`; `priority` carried. *(Tracer bullet.)*
2. Lattice resolution — `Countable` provider → `provider.domain`; non-`Countable` +
   `default_lattice` → the spec's; neither → `CompositionError`.
3. Unknown `impl` → `CompositionError`.
4. Unknown offering `name` → `CompositionError`.
5. `secret_ref` present in secrets map → value reaches `manifest.build`; dangling → `CompositionError`.
6. Two defs resolving to one `SourceKey` → `CompositionError`.
7. `name=None` → `NotImplementedError` (expand deferred).

**`CalculatorBinder`**

8. Empty specs → empty registry (real code path). Unknown `fn_id` → `CompositionError`.

**`Weaver` (`tests/test_weaver.py`)**

9. Single-source `ProfileDef` weaves → root's `capability.parameters` == the fake's parameters;
   `stores.create` once per Source (its lattice) + once for the root (`None`). *(Tracer bullet.)*
10. Two sources, distinct priorities → each parameter's `Arbiter.candidates` list ordered by
    priority (lower wins; wired order breaks ties).
11. Empty `SourceRegistry` → legal weave, empty envelope (`capability.parameters == {}`).
12. `default_reconciler != "priority"` → `CompositionError`.
13. Non-empty `CalculatorRegistry` → `NotImplementedError` (002b seam).

**Composition root + Gateway**

14. `compose(profile, fake_catalog, secrets, clock, stores)` → `Gateway` whose `best_view`
    advertises the enabled offerings' union.
15. `Gateway.resolve(selection)` forwards to `best_view.project` (stub manifold records the call).
16. Smoke (update `tests/test_server_smoke.py`): default `Settings` (`open_meteo_enabled=False`) +
    empty real catalogue → `compose` succeeds on the empty weave; server starts, tool registered.

**Config (`tests/test_config.py` updates, test-first)**

17. Defaults: `open_meteo_enabled=False` → `offerings() == ()`; `calculators() == ()`; TWC-key-present
    still emits the TWC def.

Then the refactor pass (dedupe binder error construction, deepen fixtures) — never while red.

## Modules touched

`nodes/composition.py` (+`CompositionError`, both `build`s) · `nodes/weaver.py` (`StoreFactory` ctor,
`weave`) · `nodes/store.py` (`Store` protocol, `StubStore`, concrete `StoreFactory`) ·
`nodes/reservoir.py` (`Reservoir` only) ·
`api/gateway.py` (`resolve`) · `server.py` (`PROVIDER_CATALOG`, `compose`, `main`) · `config.py`
(defaults) · `docs/module-layout.md` · `tests/` (fakes + 4 test modules).

## Out of scope (Phase B/C of issue 001)

Every `project` (`Arbiter`, `Reservoir`, `Timeline`), the value-type behaviour
(`RegularAxis`/`RegularDomain`/`FootprintDomain.contains`), the `Transport` seam, the Open-Meteo
leaf, the MCP tool body, catalogue registration + `open_meteo_enabled=True` flip.

## Continuation

- Phase B (value-type behaviour) and Phase C (the spine) per
  [issue 001](../tickets/done/001-walking-skeleton.md).
- Store-grid representation decision → [issue 006](../tickets/006-retentive-store-freshness.md).
- Wind `CalculatorSpec`s return to `Settings` at
  [002b](../tickets/002b-derived-wind-calculator.md).
