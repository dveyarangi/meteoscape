## Parent PRD

`docs/v1-requirements.md`

## What to build

Extend the Open-Meteo `Provider` from one parameter to the **5 canonical, provider-served parameters**,
exercising homogenization across a deliberately heterogeneous set: air temperature (2 m), relative
humidity (2 m), `wind_u` / `wind_v` (10 m) — **intensive & linear**; precipitation — **extensive**
(accumulation over the hourly cell, read off the shared `valid_time` `bounds`). **Wind is canonical as
u/v components**: the vendor delivers native speed/direction, and the **`Normalizer` converts them to
`wind_u` / `wind_v` on ingest** (both linear, so linear interpolation of u/v *is* correct wind
interpolation). `wind_u` / `wind_v` are **internal-only** (not requestable); the requestable
`wind_speed` / `wind_direction` product views are derived by Calculators in **002b**. The `Provider`'s
`Capability` advertises the 5 canonical parameters; its `Normalizer` maps each vendor field to its
canonical functional `(quantity, statistic)` and unit, and the response returns their `ParameterData`
(each canonical unit + per-parameter provenance) on a single shared hourly `valid_time` axis.

Encoding follows `docs/v1-requirements.md` (Parameters): all share `statistic = point`; precipitation
differs only by `extent_scaling`; the shared axis carries hourly `bounds`; every `ParameterData` carries
`present = None` and `Uniform` provenance.

**Decision to record in this issue:** the concrete canonical unit chosen per parameter.

## Acceptance criteria

- [ ] `get_forecast(lat, lon)` returns the directly-requestable canonical parameters (air temperature,
      precipitation, relative humidity) as `ParameterData` on one shared hourly `valid_time` axis (wind
      speed / direction arrive in 002b).
- [ ] The `Normalizer` ingests the vendor's native wind speed/direction as `wind_u` / `wind_v` (both
      linear, m/s), verified at the `Normalizer` / Coverage level.
- [ ] Units are canonicalized per parameter (vendor units reconciled by the Normalizer); chosen
      canonical units are recorded in this issue.
- [ ] Precipitation reads its accumulation extent from the shared hourly `bounds`; intensive params
      sample at the tick.
- [ ] Each `ParameterData` carries `present = None` and `Uniform` provenance with `expiration`.
- [ ] Unit + mocked-transport integration tests cover the canonical set, the vendor-speed/dir → u/v
      conversion, and the extensive precipitation case.

## Blocked by

- Blocked by `issues/20260623_v1/001-walking-skeleton.md`

## User stories addressed

- User story 1
- User story 2
- User story 4
