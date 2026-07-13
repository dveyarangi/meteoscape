# Meteoscape · Parameter conventions

**Reference data, not a contract decision.** The *structure* a parameter must fill — quantity identity, the
`extent_scaling` and `scale` a `Quantity` carries, the `(quantity, statistic)` functional, extent on the
Domain — is fixed by [ADR-0002](./adr/0002-data-model.md). This file records the concrete *content* for the
**v1 set**, which ADR-0002 and [concern #10](./concerns.md#10-parameter-conventions) deliberately defer at
the contract level.

> Source of truth is `StaticParameterTable.core()` in [`nodes/catalog/paramtable.py`](../src/meteoscape/nodes/catalog/paramtable.py);
> this doc mirrors it with rationale. If the two ever disagree, the code wins — update this file.

## The v1 canonical set

Eight `ParameterDef`s: **6 canonical** (provider-served, post-Normalizer) + **2 derived** (Calculators over
`wind_u` / `wind_v`). Every one shares `statistic = point` on the T axis (v1 is hourly, no windowed
`max` / `min` / `mean`); `cloud_cover` is additionally a **cell statistic on Z** (session 0011).

| ParameterId | Quantity | extent_scaling | scale | canonical_unit | requestable | notes |
|---|---|---|---|---|---|---|
| `air_temperature` | air_temperature | intensive | linear | `degC` | yes | 2 m (a Z-cell, not the key) |
| `precipitation` | precipitation | **extensive** | linear | `mm` | yes | the only extensive param; accumulation over the hourly cell `bounds` |
| `wind_u` | eastward_wind | intensive | linear | `m/s` | **no** (internal) | canonical wind component |
| `wind_v` | northward_wind | intensive | linear | `m/s` | **no** (internal) | canonical wind component |
| `relative_humidity` | relative_humidity | intensive | linear | `percent` | yes | 2 m |
| `cloud_cover` | cloud_area_fraction | intensive | linear | `percent` | yes | total column — value is a **statistic over the Z cell** `[0, TOA]` |
| `wind_speed` | wind_speed | intensive | linear | `m/s` | yes | derived `= hypot(u, v)` |
| `wind_direction` | wind_direction | intensive | **circular** | `degree` | yes | derived `= atan2(...)`; first non-linear `scale`, unexercised under v1 nearest-neighbor read-back |

The agent-facing **product is 6**: air temperature, precipitation, wind **speed**, wind **direction**,
relative humidity, cloud cover (total). Wind is **canonical as u/v components** (both `linear`, so linear interpolation of u/v
*is* correct wind interpolation); providers deliver native speed/direction and the Normalizer converts to
u/v on ingest ([v1-requirements §Parameters](./v1-requirements.md)).

## Vertical carriage (v1 declarations — session 0011)

Leaves declare **native vertical facts, never widened**; the request's Z **shape** carries the mode
(Continuous = **vantage**, exact cell = **addressing**) → [ADR-0002](./adr/0002-data-model.md);
matching → [ADR-0004](./adr/0004-producer-resolution-and-capability.md). The edge default bundle
window is `[0, ~10 m]` `above_ground`.

| ParameterId | native Z declaration | kind | vantage `[0,10]` |
|---|---|---|---|
| `air_temperature` | sample @ `2 m` `above_ground` | sample | ✓ membership |
| `relative_humidity` | sample @ `2 m` | sample | ✓ |
| `wind_u` / `wind_v` | sample @ `10 m` (v1 single level) | sample | ✓ |
| `precipitation` | surface flux @ `0 m` | sample | ✓ |
| `wind_speed` / `wind_direction` | derived — inherit u/v carriage | sample | ✓ |
| `cloud_cover` | served statistic cell `[0, TOA]` (vendor layers `[0,2]` / `[2,6]` / `[6,TOA]` km are cells of this same functional, addressed exactly — **not** ids) | cell statistic | ✓ maximal served cell |

- **`cloud_cover` (total)**: a 1:1 scalar channel on the same vendor fetch — the first live exercise
  of cell-statistic matching and the maximal-served-cell rule. Layer aliases (`cloud_cover_low` …)
  and any low/mid/high→total **overlap Calculator** (a derivation under a declared assumption — never
  a resampler) are post-v1.
- These declarations are not yet in `StaticParameterTable.core()` / the leaf — they land with
  [issue 002](tickets/002-core-5-parameters.md).

## Rationale (only where the choice is non-obvious)

- **`degC` (not K)** — the surface is an MCP agent answering human-facing weather questions; Celsius is the
  ergonomic default. The interior is unit-blind regardless (canonical-mono-unit invariant, ADR-0002), so
  this is purely a presentation-of-canonical choice, cheap to revisit.
- **`mm` for precipitation** — the extensive integral over the cell; the hourly `valid_time` cell `bounds`
  carry the accumulation window.
- **`m/s` for u/v and wind_speed** — SI, avoids the km/h ↔ kn ↔ mph vendor spread at one edge.
- **`percent` for relative humidity** — 0–100, not a 0–1 fraction.
- **`degree` for wind_direction** — meteorological convention; `circular` scale means any future kernel is
  angular (via u/v), never linearly averaged in degrees ([concern #5](./concerns.md#5-read-time-homogenization-fidelity)).

## Deferred (still open at the contract level)

- The **canonical set beyond the v1 seven**, and the **conversion-edge qualities** (which vendor→canonical
  edges are lossless vs degrading), stay deferred → [concern #10](./concerns.md#10-parameter-conventions).
- Windowed statistics (`max` / `min` / `mean`) and their request surface → [concern #15](./concerns.md#15-coarser-grid-resampling-and-aggregation-semantics).
- **Spatial-ref encoding** (CRS / datum conventions) — deferred with the broader parameter conventions.
