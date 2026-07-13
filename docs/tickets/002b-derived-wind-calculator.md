## Parent PRD

`docs/v1-requirements.md`

## What to build

Add the **derived-wind Calculators** — the first synthetic composites — completing the requestable
product. `wind_speed` and `wind_direction` are served by **Calculators over `(wind_u, wind_v)`**
(`speed = hypot(u, v)`, `direction = atan2(...)`) — both **lossless** functions of the canonical vector,
so serving them is exact.

This slice stands up the Calculator machinery end-to-end: a `Calculator` node with its own **scoped
input `Arbiter`** (resolving `wind_u` / `wind_v` and nothing else, so every edge points downward and the
object graph stays an acyclic DAG), the **`Weaver`** wiring from the **`CalculatorRegistry`** (bound by
`CalculatorBinder` from `CalculatorSpec`s against the `CalculatorCatalog`,
[ADR-0005](../adr/0005-build-time-composition.md)) with **memoization** (one node per derived
parameter), a **`DerivedCapability`** that serves the output iff all inputs are servable through the
scoped resolver, and **synthetic provenance** (lineage = the u/v inputs). Routing a request for a derived parameter to its Calculator is still ordinary Arbiter
**selection** — the combination happens *inside* the Calculator, never in the Arbiter.

`wind_direction` is `circular` (the first non-linear `scale`), but v1's nearest-neighbor read-back never
interpolates it, so no angular kernel is exercised (a future kernel must be angular via u/v, never a
degree average — [concern #5](../concerns.md#5-read-time-homogenization-fidelity)). See
`docs/v1-requirements.md` (Parameters) and
[ADR-0004](../adr/0004-producer-resolution-and-capability.md) (Calculators).

## Acceptance criteria

- [ ] `forecast_hourly(lat, lon)` returns `wind_speed` and `wind_direction`, derived from the
      provider-served `wind_u` / `wind_v` (never requested from a provider directly).
- [ ] The derived values are exact functions of u/v (`speed = hypot`, `direction = atan2`) in their
      canonical units (m/s, degree).
- [ ] Each derived `ParameterData` carries **synthetic** provenance whose lineage is its `wind_u` /
      `wind_v` inputs.
- [ ] The `Calculator` resolves its inputs through a **scoped `Arbiter`** (inputs only); the `Weaver`
      memoizes one `Calculator` node per derived parameter; the graph is acyclic.
- [ ] `wind_u` / `wind_v` stay **internal-only** — not directly requestable via `forecast_hourly`.
- [ ] Unit + mocked-transport integration tests cover the u/v → speed/direction derivation and the
      synthetic-provenance lineage.

## Blocked by

- Blocked by `docs/tickets/002-core-5-parameters.md`

## User stories addressed

- User story 1
- User story 4
