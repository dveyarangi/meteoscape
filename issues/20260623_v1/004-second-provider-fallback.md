## Parent PRD

`docs/v1-requirements.md`

## What to build

Add the second provider and prove **select + wholesale fallback**. Build the TWC `Provider` leaf
(adapter + `Normalizer` + `Capability` / cadence / grid declarations) alongside Open-Meteo. The
`Arbiter` carries a `priority` order (Open-Meteo primary → TWC fallback); per parameter it tries
candidates in order and, on a `runtime-failure` from the primary, **falls back wholesale** to the next
provider's whole window — never an A-then-B splice along `valid_time`. Demonstrable via a forced
provider failure.

See `docs/v1-requirements.md` (Providers, v1 invariants → wholesale-fallback rule) and
`docs/architecture.md` (Arbiter).

## Acceptance criteria

- [ ] With both providers enabled, results come from the primary (Open-Meteo).
- [ ] On a forced primary `runtime-failure`, the `Arbiter` falls back to TWC and serves the **whole**
      window for that parameter from the fallback.
- [ ] Fallback is wholesale and single-origin — no cached-primary ∪ fallback splice along `valid_time`.
- [ ] TWC `Provider` authors full per-parameter provenance (origin + `expiration`) like Open-Meteo.
- [ ] Unit + mocked-transport integration tests cover primary-serves and forced-failure-fallback.

## Blocked by

- Blocked by `issues/20260623_v1/002-core-5-parameters.md`
- Blocked by `issues/20260623_v1/003-request-shaping.md`

## User stories addressed

- User story 6
