# Pilot deployment

**Status:** first client of the [embedding edge](./edge/embedding.md) — identified 2026-08-19 at
the 0123 align. Its composition is **deployment configuration, deliberately outside the public
shape**; this document is its one home in the corpus. The deployment's commercial identity is
private and appears nowhere in this repository.

The deployment serves an operator's site-specific weather-alert product; meteoscape is the
weather-resolution engine behind it, and the alerting decision layer above it is not meteoscape's
concern. The pilot is a *candidate use case* exercising the framework, not the framework's
purpose ([product roadmap](./product-roadmap.md)).

## What this deployment declares that the public shape does not

- **TWC as the primary producer, Open-Meteo as backstop.** *Temporary state of this deployment's
  path, never the repo's official shape* — the shipped server's profile is vendor-neutral (keyless
  Open-Meteo). The TWC-primary declaration lives in this deployment's own composition root behind
  the embedding edge; a declared keyed offering without its secret refuses startup
  ([0123](./tickets/01-0123-config-secrets-degrade.md), 2026-08-19 resolutions).
- **Station observations** from the operator's Collector database —
  [Mongo obs source](./tickets/01-0130-mongo-obs-source.md), read-only, per-parameter provenance;
  the Collector schema is a dependency meteoscape does not own
  ([#45](./concerns.md#45-the-collector-schema-is-a-contract-meteoscape-depends-on-but-does-not-own)).
- **Forecast-run archives** with run identity —
  [Mongo forecast-run archive source](./tickets/01-0134-forecast-run-archive-source.md).
- **Forecast correction** against station history —
  [correction calculator](./tickets/01-0140-correction-calculator.md); correction ships only after
  measured bias proves stable.
- **Vendor-spend visibility and control** for the metered primary —
  [ledger](./tickets/01-0124-vendor-call-ledger.md), then
  [governor](./tickets/01-0155-vendor-budget-governor.md).

## Where its composition lives

Until the embedding surface is supported ([0125](./tickets/01-0125-supported-python-embedding.md)),
the TWC-primary composition exists only as **embedder-shaped tests** and the opt-in parity
composite — proven, not shipped. 0125's align selects the durable home: a temporary parallel
setup in-tree, or a separate project embedding meteoscape. Until that decision, nothing in the
public shape may present this deployment's configuration as the product's default.

**Sequencing (2026-08-19):** the bee-line runs on the Open-Meteo path until the correction
workstream — the [ledger](./tickets/01-0124-vendor-call-ledger.md) meters vendor-agnostically and
the [tick convention](./tickets/01-0126-tick-convention-declaration.md) reads the in-tree TWC
declarations, so neither needs TWC live. TWC goes live with this deployment's root at the
embedding surface, ahead of the [Mongo sources](./tickets/01-0130-mongo-obs-source.md) whose
consumer that root is; it is first *wanted* at the
[correction calculator](./tickets/01-0140-correction-calculator.md), whose product point is
correcting the primary this deployment serves.
