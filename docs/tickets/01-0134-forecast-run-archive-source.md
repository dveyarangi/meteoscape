# Mongo forecast-run archive source

- **Status:** Planned — its own align precedes implementation; it settles run-selection semantics
  within the initial scope and how per-provider origins compose (see below).
- **Blocks:** [correction calculator](./01-0140-correction-calculator.md).
- **Outcome:** Archived forecast runs from the operator's Collector database served as distinct
  per-provider origins, run identity carried in provenance, without deciding cross-run combination
  (stays at [#9](../concerns.md#9-cross-run-combination)).

## Parent

The release-01 bee-line makes forecast/observation comparison part of v1
([delivery status](./README.md)). Its durable product context is the
[local-station validation and bias-correction roadmap](../product-roadmap.md#priority-candidate-after-v1-local-station-validation-and-bias-correction)
and concerns [#9](../concerns.md#9-cross-run-combination) /
[#45](../concerns.md#45-the-collector-schema-is-a-contract-meteoscape-depends-on-but-does-not-own).

## What to build

The run-keyed half of the Collector projection: the collector's forecast collections — one document
per step, keyed `(base_time, time)`, common camelCase fields sparse per provider (`ibm`,
`tomorrow`, `visualcrossing`) — mapped onto canonical parameters and served through the algebra.
This is concern #9's "collection keyed by `issue_time`" seam made live on its cheapest concrete
case, deliberately without opening #9's combination semantics.

- **Initial serving scope: latest complete run per `base_time` slot.** Selecting an arbitrary
  historical run is representation the align may stage; folding runs together is explicitly not
  this ticket (#9).
- **Per-provider origins.** The three collector providers surface as three distinguishable origins
  — provenance must let a caller tell whose archived forecast a value came from, or the correction
  calculator's comparison is meaningless. One collector manifest yielding several Providers is the
  expected shape — likely the first real exercise of the manifest `expand` seam the
  [provider edge record](../edge/provider.md) lists as unexercised; whether it is `expand` or
  sibling manifests is the align's call.
- **Provenance:** the archived run's `base_time` is the parameter's `issue_time`; freshness
  semantics for an archived (non-live) forecast are the align's to state.
- **Runless producers.** [ADR-0003 § Run and bucket
  regimes](../adr/0003-provenance-and-origin.md#run-and-bucket-regimes) settles that a Provider publishing no run schedule
  carries a **Fetch bucket** in `issue_time`, not a run — TWC is the first. This archive keys by
  `base_time`, so filing a bucket under that key would archive fiction. **This ticket's align must
  decide**: decline runless producers, or record the distinction explicitly so a reader can tell a
  run from a bucket.
- Reuses the transport, registry read, and fixture-contract machinery of the
  [Mongo obs source](./01-0124-mongo-obs-source.md).

**Out of scope:** cross-run folding, run-ensemble semantics, any as-of-time request vocabulary
(#9); collector write paths; the live TWC provider (a different ticket and transport entirely).

## Acceptance criteria

- [ ] A request over an archived window at a registered station serves the latest complete run's
      forecast values per provider, with provenance carrying that run's issue identity.
- [ ] The three collector providers are distinguishable origins end to end: for the same request,
      a caller can obtain each provider's archived forecast separately and tell them apart by
      provenance.
- [ ] Per-provider sparseness is honest: a field a provider's documents never carry is absent from
      that origin's capability, not null-filled.
- [ ] An incomplete or absent run for a `base_time` slot is declined or skipped per the align's
      selection rule — never served as a silent mixture of runs.
- [ ] The forecast schema contract is pinned by integration fixtures, same mechanism as the obs
      source.
- [ ] Concern #9 is unchanged by this ticket: no cross-run combination semantics are introduced;
      the align's run-selection resolutions are recorded in their durable homes.

## Blocked by

- [Mongo obs source](./01-0124-mongo-obs-source.md) (active) — shares transport, registry, and the
  #45 contract machinery.

## Parent scope addressed

- Roadmap "Priority candidate after v1": *compare archived forecasts against those observations
  over time* — this ticket supplies the archived-forecast half of the pair.
