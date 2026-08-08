# Correction calculator

- **Status:** Planned — its own align precedes implementation; it settles the pairing semantics
  (how observations join forecasts along `valid_time` and lead time — the join half of
  [#9](../concerns.md#9-cross-run-combination)), the bias-product shape, and the parity tolerance.
- **Outcome:** A per-source, per-parameter bias report over paired forecast/observation history —
  the framework's first cross-source, cross-time calculator — validated against the operator's
  existing analysis flow as its parity reference. Correction (adjusted forecast values) is a
  strictly later step, gated on measured bias proving stable.

## Parent

Release 02 is contract-deferred ([delivery status](./README.md)); the owning durable context is
[product-roadmap → Priority candidate after v1](../product-roadmap.md#priority-candidate-after-v1-local-station-validation-and-bias-correction)
(including the staged division of labor: bias statistics start operator-side and eventually become
a Meteoscape product).

## What to build

The first Calculator whose inputs span sources and times: it pairs each provider's archived
forecast values (from the [forecast-run archive source](./02-0134-forecast-run-archive-source.md))
with observations (from the [Mongo obs source](./02-0130-mongo-obs-source.md)) at the same station
and `valid_time`, honoring lead time (`base_time` → `valid_time` distance), and produces bias
statistics per provider, per parameter, per station over a requested period.

- **First slice is scoped to temperature and relative humidity** — the parameters the operator's
  existing analysis covers, so its outputs are the parity reference (same pattern as provider
  parity checks: an independent reference reader, no shared code).
- **Bias report is the product of this ticket.** Corrected forecast parameters (with synthetic
  provenance recording the correction lineage) are the follow-on, opened only when the measured
  bias is shown stable — correcting an unmeasured or unstable bias is unfalsifiable.
- What the align must settle: whether pairing runs through the projection algebra (issue-keyed
  Selections) or a calculator-private read; the bias product's shape (a served parameter group vs
  a report surface); stability criteria that would later license correction.

**Out of scope:** correction itself (follow-on gated on stability); charts and presentation
(embedder-owned per the roadmap's division of labor); cross-run forecast folding (#9).

## Acceptance criteria

- [ ] For a requested station, period, and provider, the calculator produces bias statistics for
      temperature and relative humidity from paired forecast/observation history, honoring lead
      time in the pairing.
- [ ] Results match the operator's existing analysis for the same station and period within the
      align's declared tolerance, via an independent parity reference (no shared computation code).
- [ ] Bias output carries lineage: which origins, stations, period, and sample counts produced it —
      enough for a consumer to audit the claim.
- [ ] Missing history is honest: periods or parameters with insufficient pairs are reported as
      such, never silently averaged over gaps.
- [ ] No forecast value is modified by this ticket — the bias report is observational only, and
      the correction follow-on's gating criterion (bias stability) is recorded at the align.

## Blocked by

- [Mongo obs source](./02-0130-mongo-obs-source.md) (active)
- [Mongo forecast-run archive source](./02-0134-forecast-run-archive-source.md) (active)

## Parent scope addressed

- Roadmap "Priority candidate after v1": *report per-source, per-parameter bias per location*;
  *later, and only if the measured bias proves stable: correct the forecast for a station.*
