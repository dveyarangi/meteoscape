# 0005 · 2026-07-10 · ProfileDef / plugin-manifest seam align

Continues [session 0004](./0004-20260709-identity-registry-weaver.md). Grilled and locked the
config → catalogue → binders → ProfileConfig/ProfileDef → Weaver seam; former concern **#21** evacuated
into [ADR-0005](../adr/0005-build-time-composition.md) and
[architecture](../architecture.md#config-binders-weaver).

## Decisions

- **Three catalogues:** `ProviderCatalog`, `DerivationCatalog`, `ParameterTable` (process-wide code maps).
- **Cohesive plugin manifests:** declarations and construction operation stay together; binders
  dispatch without parallel builder registration.
- **`OfferingSpec` / `ProviderManifest`:** product catalogue; exact `ParameterId`s; optional `default_lattice`; `build(OfferingSpec, …)`.
- **`SourceDef`:** profile enablement ticket (`impl`, `offering?`, priority, `secret_ref`, settings) — no raw `SourceKey`.
- **Symmetrical binders:** `SourceBinder` → `SourceRegistry`; `DerivationBinder` → `DerivationRegistry`
  (catalog-resolved bindings, not Calculators). `ProfileDef` = both registries + root/arbiter.
- **`Weaver.weave(ProfileDef)`** — holds no catalogue; Calculators built at weave.
- **Source lattice** on `RegisteredSource`; profile root store separate.
- **#21 evacuated**; **#22** namespace polish filed (next immediate: `OfferingDef` primary; derivation↔calculator).

## Open / continuation

- Implement `SourceBinder.build` / `DerivationBinder.build` / `Weaver.weave` / first Provider leaf.
- [#22](../concerns.md#22-namespace-polish--sourcedef--derivationcalculator--producer-nouns).
- [#20](../concerns.md#20-provider-multi-resolution-offerings-offering-aware-selection) build leftover.
