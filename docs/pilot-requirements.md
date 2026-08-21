# Pilot deployment

**Status:** first client of the [embedding edge](./edge/embedding.md). Its composition is
**deployment configuration, deliberately outside the public shape**; this document is its one home
in the corpus. The deployment's commercial identity is private and appears nowhere in this
repository.

The deployment serves an operator's site-specific weather-alert product; meteoscape is the
weather-resolution engine behind it, and the alerting decision layer above it is not meteoscape's
concern. The pilot is a *candidate use case* exercising the framework, not the framework's
purpose ([product roadmap](./product-roadmap.md)).

This document owns **declaration**: which offerings this deployment enables at which priority, which
secrets it supplies, where its composition root lives, and when it goes live. What the framework can
*do* — and how that is verified in this repository — lives in
[v1 requirements](./v1-requirements.md). The
test for which side a sentence belongs on: **does it survive a second deployment?** If yes it is v1's;
if no it is this document's. v1's scope is driven by what this deployment needs, which is why the line
is worth stating rather than assuming.

## What this deployment declares that the public shape does not

- **TWC as the primary producer, Open-Meteo as backstop.** *Temporary state of this deployment's
  path, never the repo's official shape* — the shipped server's profile is vendor-neutral (keyless
  Open-Meteo). The TWC-primary declaration lives in this deployment's own composition root behind
  the embedding edge; a declared keyed offering without its secret refuses startup →
  [architecture § Config, binders, Weaver](./architecture.md#config-binders-weaver).
- **Station observations** from the operator's Collector database —
  [Mongo obs source](./tickets/01-0124-mongo-obs-source.md), read-only, per-parameter provenance;
  the Collector schema is a dependency meteoscape does not own
  ([#45](./concerns.md#45-the-collector-schema-is-a-contract-meteoscape-depends-on-but-does-not-own)).
- **Forecast-run archives** with run identity —
  [Mongo forecast-run archive source](./tickets/01-0134-forecast-run-archive-source.md).
- **Forecast correction** against station history —
  [correction calculator](./tickets/01-0140-correction-calculator.md); correction ships only after
  measured bias proves stable.
- **Vendor-spend visibility and control** for the metered primary —
  [ledger](./tickets/01-0130-vendor-call-ledger.md), then
  [governor](./tickets/01-0155-vendor-budget-governor.md).

## Where its composition lives

Until the [embedding surface](./tickets/01-0125-supported-python-embedding.md) is supported,
the TWC-primary composition exists only as **embedder-shaped tests** and the opt-in parity
composite — proven, not shipped. The embedding-surface work selects the durable home: a temporary parallel
setup in-tree, or a separate project embedding meteoscape. Until that decision, nothing in the
public shape may present this deployment's configuration as the product's default.

The [delivery status](./tickets/README.md) owns sequencing. TWC goes live with this deployment's
root at the embedding surface; the public server profile remains keyless Open-Meteo.
