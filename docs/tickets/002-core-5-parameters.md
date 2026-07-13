## Parent PRD

`docs/v1-requirements.md`

## What to build

Extend the Open-Meteo `Provider` from one parameter to the **6 canonical, provider-served parameters**,
exercising homogenization across a deliberately heterogeneous set: air temperature (2 m), relative
humidity (2 m), `wind_u` / `wind_v` (10 m) — **intensive & linear**; precipitation — **extensive**
(accumulation over the hourly cell, read off the shared `valid_time` `bounds`); cloud cover (total) —
the first **cell statistic on Z** (value over the `[0, TOA]` cell; 1:1 `percent` channel, same vendor
fetch). **Wind is canonical as
u/v components**: the vendor delivers native speed/direction, and the **`Normalizer` converts them to
`wind_u` / `wind_v` on ingest** (both linear, so linear interpolation of u/v *is* correct wind
interpolation). `wind_u` / `wind_v` are **internal-only** (not requestable); the requestable
`wind_speed` / `wind_direction` product views are derived by Calculators in **002b**. The `Provider`'s
`Capability` advertises the 6 canonical parameters; its `Normalizer` maps each vendor field to its
canonical functional `(quantity, statistic)` and unit, and the response returns their `ParameterData`
(each canonical unit + per-parameter provenance) on a single shared hourly `valid_time` axis.

Encoding follows `docs/v1-requirements.md` (Parameters): all share `statistic = point`; precipitation
differs only by `extent_scaling`; the shared axis carries hourly `bounds`; every `ParameterData` carries
`present = None` and `Uniform` provenance.

**Decision to record in this issue:** the concrete canonical unit chosen per parameter (`degC` for
air temperature already landed with Phase C — confirm the remaining four).

**Build here — Z carriage (concern #24 resolved, session 0011 →
[ADR-0002](../adr/0002-data-model.md) /
[ADR-0004](../adr/0004-producer-resolution-and-capability.md)):** native per-parameter Z
declarations replace `_NEAR_SURFACE_Z`; the default bundle request carries a Continuous **vantage** Z
window (edge-authored); `serves` gains **axis-kind matching**; the request Domain becomes
**mixed-shape per axis** (X/Y exact, T regular, Z continuous — retires the fake count-1 request Z
axis). Declarations per parameter → [parameters.md §Vertical carriage](../parameters.md).

**Edge exposure table to land here:** the surface menu is the edge's own table — an entry per
requestable name (the six product params; `wind_u` / `wind_v` have none) — and the tool's default
set, narration, and validation all read **exposure ∩ woven capability** (wind speed/direction entries
stay hidden until 002b's Calculators serve them; disabled providers shrink the menu the same way).
**Requestability is presence in the table, never a `ParameterDef` flag** — the canonical table stays
facts. 003 extends this same table with alias desugaring.

**Build in this issue — the `extent_scaling`-branched `serves` edge** (settled in session 0008):
`Domain.contains` is pure tick containment (geometry; ADR-0004's "geometric half"), so an intensive
parameter serves up to the provider's final forecast instant. For an **extensive** parameter
(precipitation), `serves` must additionally check that the **last cell's accumulation span** fits the
footprint — at the horizon edge the request's final slot means "rain during the hour past the last
forecast instant," which the provider never produced. Failing that check is per-parameter
`capability-mismatch` (parameter omitted, producible subset served) — never a padded nodata cell.

## Acceptance criteria

- [ ] `forecast_hourly(lat, lon)` returns the directly-requestable canonical parameters (air temperature,
      precipitation, relative humidity, cloud cover) as `ParameterData` on one shared hourly `valid_time`
      axis (wind speed / direction arrive in 002b).
- [ ] The `Normalizer` ingests the vendor's native wind speed/direction as `wind_u` / `wind_v` (both
      linear, m/s), verified at the `Normalizer` / Coverage level.
- [ ] Units are canonicalized per parameter (vendor units reconciled by the Normalizer); chosen
      canonical units are recorded in this issue.
- [ ] Precipitation reads its accumulation extent from the shared hourly `bounds`; intensive params
      sample at the tick.
- [ ] Each `ParameterData` carries `present = None` and `Uniform` provenance with `expiration`.
- [ ] `wind_u` / `wind_v` are declared by the `Capability` but absent from the edge exposure table,
      so the tool's default set, narration, and validation (exposure ∩ capability) never surface them.
- [ ] The request carries a Continuous **vantage** Z window (edge default); leaf `Capability` declares
      **native** per-parameter Z facts (`_NEAR_SURFACE_Z` removed); admission is axis-kind matching
      ([ADR-0004](../adr/0004-producer-resolution-and-capability.md)).
- [ ] Unit + mocked-transport integration tests cover the canonical set, the vendor-speed/dir → u/v
      conversion, and the extensive precipitation case.

## Blocked by

- Blocked by `docs/tickets/done/001-walking-skeleton.md`

## User stories addressed

- User story 1
- User story 2
- User story 4
