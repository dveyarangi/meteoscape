# 0006 · 2026-07-11 · Namespace polish (#22)

Continues [session 0005](./0005-20260710-profiledef-manifest-seam.md). Evacuates concern **#22** into
glossary / [ADR-0005](../adr/0005-build-time-composition.md) /
[architecture](../architecture.md#config-binders-weaver).

## Decisions

- **`SourceDef` → `OfferingDef`**; ticket field **`offering` → `name`** (pairs with `OfferingSpec.name`;
  `None` = expand).
- **`ProfileConfig.offerings` / `Settings.offerings()`** — ticket collection matches the type.
- **Full `Derivation*` → `Calculator*`** — `CalculatorCatalog` / `Manifest` / `Spec` / `Binder` /
  `Registry` / `RegisteredCalculator`; file `catalog/calculators.py`. Registry entries remain bindings;
  Weaver builds Calculator nodes.
- **`ProfileConfig.calculators`** — peer of `offerings`.
- **Keep `SourceBinder` / `SourceRegistry` / `RegisteredSource`** — ticket = offering; product = Source
  half of the weave.

## Open / continuation

- Walking skeleton ([001](../../issues/20260623_v1/001-walking-skeleton.md)): `SourceBinder.build` /
  `Weaver.weave` / first Provider leaf.
- [#20](../concerns.md#20-provider-multi-resolution-offerings-offering-aware-selection) build leftover.
