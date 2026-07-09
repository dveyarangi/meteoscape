# 0003 · 2026-07-09 · SourceKey / offering model & Registry–Weaver seam align

Continues [session 0002](./0002-20260708-openmeteo-provider-plan.md). A `/sync-arch` pass surfaced that
`architecture.md` still described the pre-`SourceKey` provider-level model; grilling the fix opened the
offering / resolution and Registry–Weaver seams. Contract-level outcomes landed in their canonical homes
(below); this is the narrative record.

## Decisions — contract (recorded in place)

- **Offering folds into an extensible `SourceKey`.** A distinct offering (resolution / cadence *product*)
  is a distinct `SourceKey` via its `dataset` tag; the tag **discriminates identity opaquely** (the algebra
  never parses it). `dataset` is **always named** (no partial provider-only identity; default impl-supplied,
  v1 Open-Meteo → `best_match`) — `SourceKey.dataset` is required (`str`, not `str | None`). The offering's
  native **geometry is not in the key** — it lives on the footprint Domain's axis `step`s. "Offering" is a
  `SourceKey` dimension, not a peer noun. → [glossary](../glossary.md),
  [ADR-0004](../adr/0004-producer-resolution-and-capability.md), [#20](../concerns.md#20-provider-multi-resolution-offerings-offering-aware-selection).
- **Three homes for "native resolution"** — identify (`SourceKey.dataset` tag) / rank (footprint Domain
  per-axis `step`, read by `match`) / sample (native `Domain`). No separate Capability / provenance
  `Resolution` type. The `native_resolution` provenance **string is retired**: v1 emits no native-fidelity
  field (recoverable server-side from the `SourceKey`). →
  [ADR-0002](../adr/0002-data-model.md), [ADR-0003](../adr/0003-provenance-and-origin.md),
  `provenance.py`, `v1-requirements`.
- **Two selection tiers differ by timing and precedence (policy 1 locked).** Quality / model = **static
  `priority`** (weave-time, baked ordered lists) and **always wins across bands**; resolution =
  **`Capability.score` → `Domain.match`** (project-time), a tie-break among **equal-`priority`** peers
  only (band walk: admit → try peers in `score` order → on fault next peer in band → leave band when
  none remain). Cross-priority geometric override is a later `#7` scorer policy, not the default.
  Constant `score` when no step / no constrained axes; composites expose the constant (Arbiter scores
  leaves). An offering (distinct published origin) is distinct from **coarsening within** one product
  (same `SourceKey`, read-back homogenization). →
  [ADR-0004](../adr/0004-producer-resolution-and-capability.md).
- **`Domain.match` locked.** Only request-constrained axes participate; per-axis fits combine by
  **product**; per axis prefer `o <= r`, closest to `r`, coarser below all fine-enough. →
  [ADR-0002](../adr/0002-data-model.md).
- **Config → Provider → Capability delivery.** `SourceDef` carries **no geometry** (`SourceKey` +
  `{impl, secret_ref, priority}`); the Provider — vendor knowledge — maps its fixed `dataset` → native
  geometry and populates its footprint Domain's axis steps. Multi-offering is a pure additive change
  (richer `dataset` values + axis `step`s + more `SourceDef`s). →
  [ADR-0004](../adr/0004-producer-resolution-and-capability.md),
  [architecture](../architecture.md#config-registry-weaver).
- **`priority` is per-`SourceKey` (per-`SourceDef`), extrinsic to the Provider** (which carries only its
  `SourceKey`, for provenance) — keeps profiles additive. → [architecture](../architecture.md#config-registry-weaver).
- **Registry keyed by `SourceKey`; Weaver consumes its read-only surface.** Class catalog stays
  `impl-id → Provider class`; the Registry's read-only, `SourceKey`-keyed surface (producers + `priority`)
  + the derivation registry + store/grid config are the Weaver's inputs. The degenerate
  `weave(providers, priority: Sequence[str])` is retired. → [architecture](../architecture.md#config-registry-weaver),
  [#21](../concerns.md#21-weaver-build-time-input-shape).
- **Also:** `/sync-arch` fixed `architecture.md` (Config/Registry/Weaver + Typed-config surface) to the
  `SourceKey` / `SourceDef` model it had never been updated to.

## Open / continuation

- **Weaver build-time input shape** — settled in [0004](./0004-20260709-identity-registry-weaver.md) /
  [#21](../concerns.md#21-weaver-build-time-input-shape).
- **#20 contract closed; build leftover** — footprint `step` / `match` / `score` / band walk →
  [#20](../concerns.md#20-provider-multi-resolution-offerings-offering-aware-selection). Provider
  `exact` / native-coarse-as-distinct-origin → [#5](../concerns.md#5-read-time-homogenization-fidelity).
- **Code lag** — contract signatures landed in [0004](./0004-20260709-identity-registry-weaver.md);
  `build` / `weave` behaviour and the Open-Meteo leaf remain unbuilt (per [0002](./0002-20260708-openmeteo-provider-plan.md)).
