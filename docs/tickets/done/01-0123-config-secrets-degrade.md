# Config, secrets, ~~and graceful degradation~~ *(degrade re-cut out 2026-08-19; filename kept for citation stability)*

**Legacy id:** 008

- **Status:** Done (2026-08-19) — 422 deterministic tests, ruff + pyright clean, two
  `/review-impl` passes and a `/sync-arch` applied. Cut during implementation, each as machinery
  without a customer or contradicting an existing contract: the `optional` degrade flag, config
  `Protocol`s + coercion, a weave-time tie refusal, the **env `settings`-override channel**, and
  the **namespace sweep** behind it (secrets are read only at names the declared slots derive).
- **Depends on:** [011 — TWC provider](./01-0120-twc-provider.md) (repointed
  2026-08-02: what this ticket needs is a shipped manifest that *declares* a secret, which 011 lands —
  not 004's fallback behaviour)
- **Outcome:** Complete key-present/key-absent provider construction behavior.

> **Raised at the 2026-08-10 beeline align**, for two reasons that both make it heavier than
> "config nicety":
>
> - ~~**The keyed provider is now the primary.** With TWC on the default path, key-absent stops being
>   a spare's absence and becomes the deployment's **degraded mode** — no key must mean "run on
>   Open-Meteo", never "run broken".~~ *Re-cut 2026-08-19 (align): **TWC-as-primary is a temporary
>   private-deployment configuration, never the public repo's official shape.** The shipped
>   server's profile is vendor-neutral (Open-Meteo, keyless), so boot-degrade has no public use
>   case and the mechanism is not built: a declared keyed offering with a missing secret
>   **refuses** startup. That deployment's TWC-primary declaration is the **embedding edge's
>   first client** ([edge/embedding.md](../../edge/embedding.md) Roadmap); parallel setup vs
>   separate project is [0125](../01-0125-supported-python-embedding.md)'s align.*
>   [011](./01-0120-twc-provider.md)
>   closes the `unknown impl` trap; this ticket owns the construction machinery.
> - **It is the mechanism the private sources need.** A Mongo connection string is a secret carried
>   the same way a vendor key is, so this ticket serves
>   [01-0130](../01-0130-mongo-obs-source.md) as well as TWC — and it is the injection path the
>   [vendor-call ledger](../01-0130-vendor-call-ledger.md) is built behind.

## Parent PRD

`docs/v1-requirements.md`

## What to build

Introduce the single typed config (Pydantic Settings) as pure data and wire it through
`SourceBinder`. ~~`Settings` projects a `ProfileConfig` carrying: the enabled **`OfferingDef`s** (explicit
offering names), provider secrets (the TWC API key, via `secret_ref` into the injected secrets map),
per-`SourceKey` `Arbiter` priority, and cache / grid config (store spatial step, hourly time step,
retention interval).~~ *Resolved 2026-08-19 (align): `Settings` projects no profile. Profile
enumeration is **code-declared data at the composition root** — the root is the de-facto embedding
edge ([edge/embedding.md](../../edge/embedding.md)), and there is no global default profile, only
*profiles*: `server.py` declares the MCP product's own. `Settings` supplies only the
store/retention knobs (secrets are read by derived name into an `impl_id`-keyed map; per-offering
`settings` ride the def — both re-cut later the same day). `OfferingDef.secret_ref`
is **deleted**: the binder already holds the manifest when it resolves the secret
([composition.py](../../../src/meteoscape/nodes/composition.py) `SourceBinder.build`), so the slot name
comes from `manifest.secret`, the def's copy was a danglable duplicate, and the composition root
never names a secret. `priority` stays an explicit integer — it is a shared ranking scale with
`CalculatorDef` across one scoped Arbiter per parameter, which list order cannot express.*
Secrets are **injected at construction**, never read from globals.
`SourceBinder.build(defs, secrets, clock, parameters)` *(the map is keyed by `impl_id`; a
mid-align variant passing raw operator vars for the binder to slice was cut with the env override
channel)* instantiates only the declared providers into the `SourceRegistry` the `Weaver` consumes via `ProfileDef`. A **missing TWC key →
graceful degrade**: ~~`Settings` never emits the TWC `OfferingDef`, so the server starts and serves with
Open-Meteo alone. Degrade is enablement policy owned by `Settings`;~~ *resolved 2026-08-19 (align,
re-cut twice same day, final): **no degrade mechanism exists.** The public profile declares no
keyed provider, so keyless runs are the ordinary case, not a degraded one; a profile that does
declare a keyed offering and lacks its secret **fails startup**. An earlier `OfferingDef.optional`
flag was considered and **thrown away** — its only customer was a deployment-specific declaration
that does not belong in the public shape. `Settings` owns no enablement, and no filtering step
exists.* The
**binder is strict** — a def that reaches it either binds or startup fails (`CompositionError`).

Note: `config.py` (`Settings` / `OfferingDef` / `ProfileConfig` knobs) and `tests/test_config.py` already
exist from the seam work; this slice wires them through `SourceBinder` end-to-end and proves the
degrade path.

*Added 2026-08-19 (align follow-up, second):* the ticket also applies **"a def selects and ranks;
it never restates a manifest's declarations"** to the calculator side: `CalculatorManifest` gains
the co-produced `outputs`/`inputs` (the kernel's own facts, mirroring `OfferingSpec` as product
row) and `CalculatorDef` slims to selection + policy. The builtin modules export each id as a
named constant beside `CATALOG` — profiles select by handle, defs stay plain strings (a
protocol-and-coercion variant was rejected as ceremony) — and `priority` defaults to `0`, made
safe by the `priority` reconciler's standing contract: equal priorities keep bind order (stable
sort) — the ordered declaration is the tie-break. *(A weave-time tie refusal was built and
removed 2026-08-19: it contradicted that documented contract.)*

*Added 2026-08-19 (align follow-up):* the ticket also **relocates the shipped catalogues out of the
root** — availability is a system prop, not an edge prop, and five test modules were importing the
catalogues through `meteoscape.server` to reach it. The membership maps move to
`nodes/providers/builtin.py` / `nodes/calculators/builtin.py` (each exporting `CATALOG`);
`server.py` imports availability and declares only enablement. This partially discharges
[#26](../../concerns.md#26-provider--calculator-plugin-scaffolding) (membership lists off the root);
discovery, optional sets, and symmetric selection stay open there.

**This ticket also dissolves the vendor-named `Settings` fields** *(scoped 2026-08-18 by
[edge/provider.md](../../edge/provider.md)'s vendor-config-purity invariant)*: `twc_api_key` and
`open_meteo_enabled` are acknowledged v1 plumbing — they name a vendor while carrying no vendor
default or semantics — and their generic forms land here: secret material populated generically
~~(e.g. an env scan keyed by the manifests' `SecretSlot` names into the injected secrets map)~~
*(spelling resolved below — derived per-impl env names, map keyed by `impl_id`)*,
enablement derived from slot presence and impl registration rather than per-vendor fields, and
~~generic env pass-through of opaque per-offering `settings` — the cadence-override channel
[0120's RFC](../../rfc/done/01-0120-twc-provider.md) explicitly defers here.~~ *Re-cut 2026-08-19
(final): **no env channel for `settings`.** Env carries secrets and scalars, as env is for;
structured per-offering configuration is declared on the `OfferingDef` at a composition root —
the field 0120's deferral actually targets — and a config file may fill it later
([0125](../01-0125-supported-python-embedding.md)). Deferring a decision to this ticket did not
oblige it to build a channel with no customer: the pilot root, the only TWC tuner, writes
`settings={...}` in code. Squeezing structure through env had produced a prefix grammar, JSON
value parsing, and collision guards — a config-file parser inside the env namespace.* The Mongo connection string
([01-0130](../01-0130-mongo-obs-source.md)) is the second consumer, which is what forces the
generic shape. ~~The exact env spelling is this ticket's own decision~~ *Resolved 2026-08-19
(align): **one namespace per impl** — `METEOSCAPE_<IMPL>_<PROP>` (uppercase, hyphens →
underscores). ~~`Settings` collects the unconsumed `METEOSCAPE_*` vars once at construction; they travel into
`compose` whole and are sliced per-impl at the binder.~~ *Re-cut 2026-08-19 (final): no sweep —
`secrets_from_env(secret_slots(catalog))` reads **only the names the declared slots derive**, and
`compose`/`SourceBinder.build` take the resulting `impl_id`-keyed map (an embedder fills it from a
vault with no env spelling).* The **secret** sits at the derived slot suffix — `SecretSlot` names go impl-local (TWC
declares `api_key`; spelling `METEOSCAPE_TWC_API_KEY`, unchanged from today), one slot per impl
being `ProviderManifest.secret`'s standing contract. ~~Every **other var under the prefix** becomes
a `settings` override, JSON-scalar parsed; boot-checks refuse a prefix colliding with a `Settings`
field or nesting inside another impl's.~~ *Cut 2026-08-19 with the override channel — with no
scanning there is nothing to mis-slice and no prefix to guard; a var matching no impl's secret
name is simply inert.* `build` rejects unknown settings keys (typo guard for the **declared**
map — both v1 impls gain it). `open_meteo_enabled` is **dropped with no
replacement**: disabling a keyless impl has no operator story, and a generic disabled-list can
arrive with a real need. A `.env.example` ships as the operator narration.* — ~~as is whether the v1
**profile enumeration** itself (`offerings()` hard-coding impl names and priorities as code)
becomes declared data here, or stays code until [#26](../../concerns.md#26-provider--calculator-plugin-scaffolding)'s
discovery story / the [embedding surface](../01-0125-supported-python-embedding.md)'s programmatic
path force it; today that question has no other owner.~~ *Resolved 2026-08-19 (align): the
enumeration becomes **declared data at the composition root**, next to the hand-assembled
catalogues — the one place vendor names are already legal
([edge/provider.md](../../edge/provider.md) vendor-config-purity), and the same `ProfileConfig`
seam every future producer (a config-file parser, [#26](../../concerns.md#26-provider--calculator-plugin-scaffolding)'s
discovery, an embedder's own profile) feeds without touching `compose`. A config-*file* grammar is
deliberately not minted: one customer today; the file form waits for the second materially
different profile author ([0125](../01-0125-supported-python-embedding.md)).*

See `docs/v1-requirements.md` (Config & secrets, acceptance §6), `docs/architecture.md` (Config,
binders, Weaver; Composition root), and [ADR-0005](../../adr/0005-build-time-composition.md).

**Not this ticket:** response-level (5xx/429) retry stays **declined-until-evidence** (session 0009 —
once 004 lands, the right second attempt is a *different candidate*, not a re-try); quota /
rate-limit policy stays the **deferred null Gateway seam**
(`architecture.md` → Deferred decisions), out of v1 scope entirely.

## Acceptance criteria

- [x] ~~One typed config object holds the enabled `OfferingDef`s, secrets, per-`SourceKey` `Arbiter`
      priority, and cache / grid config.~~ *(re-cut 2026-08-19, align)* One typed config object
      (`Settings`) holds only generic residue — secret values, per-impl `settings` overrides, store
      / retention knobs; the profile enumeration (defs with priorities) is declared data at the
      composition root, and `ProfileConfig` reaching `compose` carries offerings, calculators, root
      store, and arbiter policy as today.
- [x] The TWC key is injected via config at construction; no secret is read from globals or hardcoded.
- [x] ~~With the TWC key absent, the server starts and serves on Open-Meteo alone (graceful degrade, no
      fail-fast).~~ *(re-cut 2026-08-19, align)* The public server's profile declares no keyed
      provider and starts keyless on Open-Meteo; a profile declaring a keyed offering without its
      secret fails startup with a `CompositionError` naming the impl, slot, and derived env var.
      TWC-primary composition is proven by an embedder-shaped test profile, not by the shipped
      one.
- [x] `SourceBinder` instantiates only configured providers into the `SourceRegistry`; `server.py`
      stays a thin composition root (catalogues + declared profile data + `Settings` →
      `ProfileConfig` → binders → `ProfileDef` → `weave`).
- [x] Unit + integration tests cover the keyless public boot, key-present composition of a
      TWC-primary profile (embedder-shaped test), and key-absent refusal of that same profile
      *(re-cut 2026-08-19)*.
- [x] **No vendor-named field remains on `Settings`** *(added 2026-08-18)*: secrets and enablement
      ride generic mechanisms keyed by impl registration and the manifests' `SecretSlot`s; the
      provider edge's vendor-config-purity carve-out for the v1 plumbing fields is discharged.

## User stories addressed

- User story 11
- User story 12
- User story 13
