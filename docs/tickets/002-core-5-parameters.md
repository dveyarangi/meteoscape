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

**Vendor mapping — the `Tap` table (session 0011; session 0002's `Channel`, renamed).** The leaf
carries a `Tap` per canonical parameter: `Tap { produces: ParameterId, vendor_vars: (VendorVar…),
z: ZDecl, decode }`, `VendorVar { name, unit }` (`unit` = the expected native unit, verified against
`hourly_units`, never converted by request). **Single-output** — `produces` is one parameter, so wind
is **two taps** (`wind_u`, `wind_v`) both reading the same two vendor vars (`wind_speed_10m`,
`wind_direction_10m`); the trig runs per tap (nanoseconds vs an HTTP fetch) and keeps the table, the
`Capability` derivation, and `present` handling uniform. `decode(vendor arrays) → (values, present)`
does the **quantity transform only** (speed/dir → u/v); unit **conversion** to canonical is the tap's
own ingest step (see below). The `Tap` table is the single leaf-side source for the fetch var list,
the normalizer program, **and** the capability declaration (X/Y + T from the offering, Z from the tap).

**Units — verify-always, convert-on-ingest, no request knob (sessions 0009/0011).** Native→canonical
conversion is the Normalizer's job (`architecture.md` §Normalization vs. homogenization): each tap
converts its `VendorVar` to canonical on ingest, driven by `VendorVar.unit`. The URL **never**
negotiates units (no `wind_speed_unit` knob) — Open-Meteo wind arrives `km/h` and the wind taps
convert `× 1/3.6` to `m/s` before `decode`'s trig, so `decode` sees canonical inputs. Every other v1
tap is a unit no-op (vendor default already canonical). A `VendorVar.unit` mismatch against the
vendor's reported units is `runtime-failure`, never a guess. The shared conversion **catalogue** is
deferred to [ticket 010](./010-unit-conversion-edge.md) (forced by 004's second vendor); 002 ships the
one `km/h→m/s` factor inline.

**Decision recorded — canonical units (session 0011):** `air_temperature` `degC` (Phase C),
`precipitation` `mm`, `relative_humidity` `percent`, `cloud_cover` `percent`, `wind_u` / `wind_v`
`m/s` (`wind_speed` / `wind_direction` → `m/s` / `degree` at 002b). Mirrors
[parameters.md](../parameters.md).

**Decision recorded — precipitation vendor variable (session 0011):** Open-Meteo `precipitation`
(the vendor **total** — rain + showers + snow water-equivalent, `mm`), matching the canonical
quantity's "all falling water, liquid-equivalent" meaning and the agent's "will I get wet?" intent.
`rain` / `snowfall` / `showers` component decomposition is a post-v1 parameter family, not the total.

**Build here — Z carriage (concern #24 resolved, session 0011 →
[ADR-0002](../adr/0002-data-model.md) /
[ADR-0004](../adr/0004-producer-resolution-and-capability.md); encoding settled at the 002 align →
[ADR-0006](../adr/0006-materialization-granularity-and-store-shape.md)):** native per-parameter Z
declarations replace `_NEAR_SURFACE_Z` — footprint Z is a **sample** level (`RegularAxis` count-1
**point cell**: `[2,2]` temperature/humidity, `[10,10]` wind, `[0,0]` precipitation) or a **statistic
cell** (`IntervalAxis` **span**: `[0,TOA]` cloud), extents only. The default bundle request carries
a **`VantageAxis`** on Z — a single-cell `IntervalAxis` (overriding `matches` with overlap) whose
`interval` is the edge-authored window `[0,~10]` (retires the fake point `Z=2.0`); `RegularDomain`
widens to **`GridDomain`**
(`Mapping[AxisName, EnumerableAxis]`, mixed), so the request stays enumerable — X/Y exact count-1, T
hourly cellular, Z the vantage cell. Admission becomes the **request-side gate**
`requested.matches(declared)` hidden inside the footprint's `contains`: a `VantageAxis` request uses
`Interval.intersects(declared.extent)` (which *is* membership `2 ∈ [0,10]` against a point cell,
inclusion `[0,10] ⊆ [0,TOA]` against a span), the default axis uses `contains` (X/Y/T unchanged) — one
predicate, no new public verb. By closed projection the `VantageAxis` rides onto the served Coverage
(`resample` sets `domain = selection.domain`); *which* admitted cell answers (maximal served cell /
resampler) is a separate selection step, trivial in v1. Declarations per parameter →
[parameters.md §Vertical carriage](../parameters.md).

**Data-plane contract landing here
([ADR-0006](../adr/0006-materialization-granularity-and-store-shape.md)):**
`Normalizer.normalize(raw, provenance) → Sequence[Coverage]` — **native records** grouped by shared
native Domain (Open-Meteo: `{air_temperature, relative_humidity}` @ 2 m · `{wind_u, wind_v}` @ 10 m ·
`{precipitation}` @ 0 m · `{cloud_cover}` @ `[0,TOA]`). With the store still a stub the leaf
assembles the served Coverage on `sel.domain` directly (the relabel onto the fat Z cell is
value-passthrough); the records become the assimilation input at 006. **Node-`Countable` retirement
is deferred to ticket 006** — the build/store-allocation path ADR-0006 targets (`Reservoir.domain` /
`Store.domain`-as-public / the Weaver's `provider.domain` read; provider-exact lattices moving to the
build-time construction face), which 006 rewrites once the retentive `Store` makes `domain` real. It
has no hard dependency on the vantage work, so **002 keeps `Countable` intact**; `StubStore.domain`
stays a dummy (retyped `GridDomain` in the rename sweep).

**Edge exposure table to land here:** the surface menu is the edge's own table — an entry per
requestable name (the six product params; `wind_u` / `wind_v` have none) — and the tool's default
set, narration, and validation all read **exposure ∩ woven capability** (wind speed/direction entries
stay hidden until 002b's Calculators serve them; disabled providers shrink the menu the same way).
**Requestability is presence in the table, never a `ParameterDef` flag** — the canonical table stays
facts. 003 extends this same table with alias desugaring.

**Build in this ticket — the `extent_scaling`-branched `serves` edge** (settled in session 0008):
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
- [ ] Units are canonicalized per parameter by **convert-on-ingest** in the `Tap` (wind `km/h→m/s`;
      others no-op), verified against `hourly_units`; **no `*_unit` URL knob**; mismatch →
      `runtime-failure`. Canonical units recorded above.
- [ ] `precipitation` reads Open-Meteo's **total** `precipitation` variable (liquid-equivalent `mm`).
- [ ] Precipitation reads its accumulation extent from the shared hourly `bounds`; intensive params
      sample at the tick.
- [ ] Each `ParameterData` carries `present = None` and `Uniform` provenance with `expiration`.
- [ ] `wind_u` / `wind_v` are declared by the `Capability` but absent from the edge exposure table,
      so the tool's default set, narration, and validation (exposure ∩ capability) never surface them.
- [ ] The request carries a **`VantageAxis`** Z aperture over a **`GridDomain`** (edge default); leaf
      `Capability` declares **native** per-parameter Z facts — samples as `RegularAxis` count-1
      point cells, the cloud statistic cell as an `IntervalAxis` span (`_NEAR_SURFACE_Z` removed);
      admission is the request-side gate `requested.matches(declared)` (`VantageAxis` → `intersects`)
      hidden inside footprint `contains`
      ([ADR-0002](../adr/0002-data-model.md) /
      [ADR-0004](../adr/0004-producer-resolution-and-capability.md)).
- [ ] `normalize` returns native records grouped by shared native Domain; the leaf assembles the
      served Coverage on `sel.domain`. `Countable` **stays** in 002 (`StubStore.domain` dummy, retyped
      `GridDomain`); its retirement is deferred to ticket 006
      ([ADR-0006](../adr/0006-materialization-granularity-and-store-shape.md)).
- [ ] Unit + mocked-transport integration tests cover the canonical set, the vendor-speed/dir → u/v
      conversion, and the extensive precipitation case.

## Blocked by

- Blocked by `docs/tickets/done/001-walking-skeleton.md`

## User stories addressed

- User story 1
- User story 2
- User story 4
