# 0004 · 2026-07-09 · Identity leaf + Registry–Weaver code-lag reshape

Continues [session 0003](./0003-20260709-sourcekey-offering-align.md). Closes the code lag on the
`SourceKey` / `SourceDef` / Registry–Weaver seam.

## Decisions

- **`SourceKey` is a Tier-0 leaf** in `identity.py` (peer of `errors` / `clock`). Provenance imports it
  inward; config/registry never reach into `manifold/`. Re-exported from `meteoscape` for clients.
- **`Settings.sources()` / `secrets()`** replace the old `enabled_providers` + `arbiter_priority` string
  tuples. Env scalars stay (`open_meteo_enabled`, `twc_api_key`, store/retention/horizon). `priority` is
  an int rank (bands), not list position.
- **`Registry.build(defs, secrets, clock) → SourceRegistry`** — catalog unchanged (`impl-id → class`);
  output is a named read-only role (`RegisteredSource` = provider + extrinsic priority). Clock moves
  here (providers are instantiated here).
- **`Weaver.weave(sources, derivations, store)`** — retires `weave(providers, priority: Sequence[str])`.
  Ordering rides inside `sources`. `DerivationRegistry` / `StoreConfig` are thin declared seams.
  → [#21](../concerns.md#21-weaver-build-time-input-shape) settled.
- **`Provider.source_key`** — abstract property; Provider carries identity for provenance, never priority.

## Open / continuation

- **Behaviour** — `Registry.build` / `Weaver.weave` still `NotImplementedError`; first provider leaf
  (Open-Meteo) still unbuilt per [0002](./0002-20260708-openmeteo-provider-plan.md).
- **#20 build leftover** — footprint `step` / `match` / `score` / band walk.
- **server.py** documents the wiring order; live composition lands with the walking skeleton.
