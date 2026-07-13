## Parent PRD

`docs/v1-requirements.md`

## What to build

Make the request flexible at the edge. The MCP adapter accepts optional `parameters` (a subset of the
**6 product** params — temperature, precipitation, wind speed, wind direction, humidity, cloud cover;
the internal `wind_u` / `wind_v` are not requestable; default all), `start`, and `end`, and builds the canonical
`Selection` accordingly — a lat/lon
**point** `Domain` plus an hourly `valid_time` extent. When `end` is omitted, a configurable **default
horizon** (≈ 7 days) applies; `start` / `end` form a free window (no interval enum — the `Domain` models
arbitrary extents). The `Arbiter` admits a provider per parameter only when its `Capability`
**temporally contains** the requested extent (whole-request `Domain`-containment). The tool description
**narrates the available envelope** (parameters × max horizon) from the `Capability` union — dynamic
off the woven root, extending 001's served-parameters narration with the max horizon.

**Already landed at 001 (Phase C):** the `parameters` input (unknown name → `bad-request`, default =
the woven root capability), dynamic served-parameters narration, `serves`-containment admission in the
`Arbiter`, and the supplied-`start`/`end` → `bad-request` stubs. This issue's remaining substance:
make the window real (free `start`/`end` → exact-window fetch mapping), apply the configurable default
horizon to an omitted `end`, extend the **edge exposure table** (minted at 002 — presence =
requestability) with **alias desugaring** (requestable names → canonical functionals + **exact-mode
Z** — a precise level or layer cell, the dual of the default bundle's vantage window; sessions
0009/0011), extend narration with the max horizon, and exercise
out-of-envelope admission with real free windows (Phase C's fixed 168 h window never leaves the
envelope). Concern #24 is **resolved** (session 0011 → [ADR-0002](../adr/0002-data-model.md) /
[ADR-0004](../adr/0004-producer-resolution-and-capability.md)); this issue inherits the
vantage/exact request modes 002 builds.

Output resolution stays hourly (no `step` input). See `docs/v1-requirements.md` (Request / tool
contract, Time axis).

## Acceptance criteria

- [ ] `parameters` selects a subset of the 6 product params; omitting it returns all six.
- [ ] `start` / `end` define a free hourly window; omitting `end` applies the configurable default
      horizon.
- [ ] A request whose extent exceeds a provider's temporal `Capability` is not admitted for that
      provider (whole-request containment).
- [ ] The tool description narrates the available envelope (parameters × max horizon) from the
      `Capability` union.
- [ ] Unit + mocked-transport integration tests cover subset selection, default horizon, and
      out-of-envelope extents.

## Blocked by

- Blocked by `docs/tickets/002-core-5-parameters.md`
- Blocked by `docs/tickets/002b-derived-wind-calculator.md`

## User stories addressed

- User story 2
- User story 3
- User story 10
