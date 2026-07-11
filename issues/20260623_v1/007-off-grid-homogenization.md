## Parent PRD

`docs/v1-requirements.md`

## What to build

Answer an **off-grid** lat/lon **at the requested point** via read-time homogenization (S). Each
`Reservoir` quantizes the request onto its `Store`'s declared spatial grid for retention and
**homogenizes back onto the request at read**: when the request rides the grid it is a lossless crop
(identity); when it is off-grid the value is read from the **nearest** enclosing store cell
(cached-fresh or refilled) and reported at `sel.domain`. The v1 read-back kernel is **degenerate
(nearest-neighbor, kind-agnostic)**; `valid_time` stays hourly-aligned (identity). The store's spatial
step is **configurable** (coarser = more cache sharing + more interpolation).

Per-kind / higher-order kernels and a provider `exact` capability stay deferred. See
`docs/v1-requirements.md` (Request / tool contract, acceptance §4) and `docs/architecture.md`
(Normalization vs. homogenization, Reservoir).

## Acceptance criteria

- [ ] A request for an off-grid lat/lon returns values **at the requested point**, sourced from the
      nearest store cell (cached-fresh or refilled).
- [ ] An on-grid request degenerates to a lossless crop (identity kernel).
- [ ] `valid_time` remains hourly-aligned (identity on the time axis).
- [ ] The store spatial step is configurable (not hardcoded); native/store fidelity is recoverable
      server-side via the provenance `SourceKey` — **not** a dedicated provenance field
      ([ADR-0003](../../docs/adr/0003-provenance-and-origin.md)).
- [ ] Unit + mocked-transport integration tests cover on-grid crop and off-grid nearest-neighbor
      read-back.

## Blocked by

- Blocked by `issues/20260623_v1/006-retentive-store-freshness.md`

## User stories addressed

- User story 7
- User story 15
