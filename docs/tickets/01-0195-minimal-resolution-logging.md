# Minimal resolution logging

- **Status:** Planned — its own align precedes implementation; this ticket assigns the Phase-1
  structured-log slice while the richer trace sidecar remains deferred.
- **Outcome:** Operators can inspect structured evidence of how each request was resolved — producer
  choice, fall-through, and Store hit/refill — without changing the weather data product.

## Parent

[`docs/product-roadmap.md`](../product-roadmap.md) — Phase 1's minimal structured-log obligation and
technical proof obligation for inspectable resolution decisions; detailed open design remains in
[#14](../concerns.md#14-resolution-trace-and-observability).

## What to build

Ship the smallest useful structured logging surface for v1 resolution. The ticket's opening align
settles event granularity, correlation, sensitive-field policy, and the logging boundary. The emitted
evidence must explain per-parameter producer selection and fall-through, plus fresh Store reuse versus
refill, while keeping provenance in `Coverage` and diagnostics beside it.

This is not the structured trace sidecar, metrics catalogue, or observability platform described by
the wider concern. It must not alter `Coverage`, `ParameterData`, or MCP response schemas.

## Acceptance criteria

- [ ] A resolved request emits machine-parseable, correlated structured evidence identifying each
      requested parameter's selected producer and resolution outcome.
- [ ] A forced primary failure records the failed/fallen-through candidate and the fallback winner;
      partial and terminal failures remain distinguishable by the settled error categories.
- [ ] A fresh repeat and a missing/stale request are observably distinguishable as Store reuse versus
      refill at the relevant Reservoir positions.
- [ ] The aligned sensitive-field policy is documented and guarded; secrets, authorization material,
      vendor payloads, and returned weather values are never logged.
- [ ] Existing Coverage values and MCP response/error schemas remain unchanged, pinned by integration
      tests through successful, fallback, and failed requests.

## Blocked by

- [Retentive store](./done/01-0115-retentive-store-freshness.md) — creates the hit/refill behavior to
  observe.
- [Second-provider fallback](./done/01-0121-second-provider-fallback.md) — creates candidate fall-through.
- [Per-parameter selection](./01-0170-per-parameter-selection.md) — creates multi-winner resolution.
- [Errors and partial success](./01-0190-error-taxonomy-partial-success.md) — completes the outcome
  categories the log must distinguish.

## Parent scope addressed

- Product roadmap Phase 1 — minimal structured logs for resolution decisions
- Technical proof obligation — inspectable resolution trace or logging surface
