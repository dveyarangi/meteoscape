## Parent PRD

`docs/v1-requirements.md`

## What to build

Introduce the single typed config (Pydantic Settings) as pure data and wire it through
`SourceBinder`. `Settings` projects a `ProfileConfig` carrying: the enabled **`OfferingDef`s** (explicit
offering names), provider secrets (the TWC API key, via `secret_ref` into the injected secrets map),
per-`SourceKey` `Arbiter` priority, and cache / grid config (store spatial step, hourly time step,
retention interval). Secrets are **injected at construction**, never read from globals.
`SourceBinder.build(defs, secrets, clock, parameters)` instantiates only the enabled/configured
providers into the `SourceRegistry` the `Weaver` consumes via `ProfileDef`. A **missing TWC key →
graceful degrade**: `Settings` never emits the TWC `OfferingDef`, so the server starts and serves with
Open-Meteo alone. Degrade is enablement policy owned by `Settings`; the **binder is strict** — a def
that reaches it either binds or startup fails (`CompositionError`).

Note: `config.py` (`Settings` / `OfferingDef` / `ProfileConfig` knobs) and `tests/test_config.py` already
exist from the seam work; this slice wires them through `SourceBinder` end-to-end and proves the
degrade path.

See `docs/v1-requirements.md` (Config & secrets, acceptance §6), `docs/architecture.md` (Config,
binders, Weaver; Composition root), and [ADR-0005](../../docs/adr/0005-build-time-composition.md).

## Acceptance criteria

- [ ] One typed config object holds the enabled `OfferingDef`s, secrets, per-`SourceKey` `Arbiter`
      priority, and cache / grid config.
- [ ] The TWC key is injected via config at construction; no secret is read from globals or hardcoded.
- [ ] With the TWC key absent, the server starts and serves on Open-Meteo alone (graceful degrade, no
      fail-fast).
- [ ] `SourceBinder` instantiates only configured providers into the `SourceRegistry`; `server.py`
      stays a thin composition root (catalogues + `Settings` → `ProfileConfig` → binders →
      `ProfileDef` → `weave`).
- [ ] Unit + integration tests cover key-present (both providers) and key-absent (degrade) startup.

## Blocked by

- Blocked by `issues/20260623_v1/004-second-provider-fallback.md`

## User stories addressed

- User story 11
- User story 12
- User story 13
