# Config, secrets, and graceful degradation

**Legacy id:** 008

- **Status:** Partial
- **Depends on:** [011 — TWC provider](./done/01-0120-twc-provider.md) (repointed
  2026-08-02: what this ticket needs is a shipped manifest that *declares* a secret, which 011 lands —
  not 004's fallback behaviour)
- **Outcome:** Complete key-present/key-absent provider construction behavior.

> **Raised at the 2026-08-10 beeline align**, for two reasons that both make it heavier than
> "config nicety":
>
> - **The keyed provider is now the primary.** With TWC on the default path, key-absent stops being
>   a spare's absence and becomes the deployment's **degraded mode** — no key must mean "run on
>   Open-Meteo", never "run broken". [011](./done/01-0120-twc-provider.md) closes the `unknown impl` trap;
>   this ticket owns the whole behaviour.
> - **It is the mechanism the private sources need.** A Mongo connection string is a secret carried
>   the same way a vendor key is, so this ticket serves
>   [02-0130](./02-0130-mongo-obs-source.md) as well as TWC — and it is the injection path the
>   [vendor-call ledger](./02-0124-vendor-call-ledger.md) is built behind.

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

**This ticket also dissolves the vendor-named `Settings` fields** *(scoped 2026-08-18 by
[edge/provider.md](../edge/provider.md)'s vendor-config-purity invariant)*: `twc_api_key` and
`open_meteo_enabled` are acknowledged v1 plumbing — they name a vendor while carrying no vendor
default or semantics — and their generic forms land here: secret material populated generically
(e.g. an env scan keyed by the manifests' `SecretSlot` names into the injected secrets map),
enablement derived from slot presence and impl registration rather than per-vendor fields, and
generic env pass-through of opaque per-offering `settings` — the cadence-override channel
[0120's RFC](../rfc/done/01-0120-twc-provider.md) explicitly defers here. The Mongo connection string
([02-0130](./02-0130-mongo-obs-source.md)) is the second consumer, which is what forces the
generic shape. The exact env spelling is this ticket's own decision — as is whether the v1
**profile enumeration** itself (`offerings()` hard-coding impl names and priorities as code)
becomes declared data here, or stays code until [#26](../concerns.md#26-provider--calculator-plugin-scaffolding)'s
discovery story / the [embedding surface](./01-0125-supported-python-embedding.md)'s programmatic
path force it; today that question has no other owner.

See `docs/v1-requirements.md` (Config & secrets, acceptance §6), `docs/architecture.md` (Config,
binders, Weaver; Composition root), and [ADR-0005](../adr/0005-build-time-composition.md).

**Not this ticket:** response-level (5xx/429) retry stays **declined-until-evidence** (session 0009 —
once 004 lands, the right second attempt is a *different candidate*, not a re-try); quota /
rate-limit policy stays the **deferred null Gateway seam**
(`architecture.md` → Deferred decisions), out of v1 scope entirely.

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
- [ ] **No vendor-named field remains on `Settings`** *(added 2026-08-18)*: secrets and enablement
      ride generic mechanisms keyed by `SecretSlot` names and impl registration; the provider
      edge's vendor-config-purity carve-out for the v1 plumbing fields is discharged.

## User stories addressed

- User story 11
- User story 12
- User story 13
