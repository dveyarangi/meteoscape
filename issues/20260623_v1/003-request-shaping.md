## Parent PRD

`docs/v1-requirements.md`

## What to build

Make the request flexible at the edge. The MCP adapter accepts optional `parameters` (a subset of the
**5 product** params — temperature, precipitation, wind speed, wind direction, humidity; the internal
`wind_u` / `wind_v` are not requestable; default all), `start`, and `end`, and builds the canonical
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
horizon to an omitted `end`, add the **edge alias table** (desugar requestable names to canonical
functionals / exact-Z Selections — session 0009), extend narration with the max horizon, and exercise
out-of-envelope admission with real free windows (Phase C's fixed 168 h window never leaves the
envelope).
[Concern #24](../../docs/concerns.md#24-parameter-height-carriage-fat-shared-z-cell-vs-per-z-group-requests)
is decided at 002 / this issue.

Output resolution stays hourly (no `step` input). See `docs/v1-requirements.md` (Request / tool
contract, Time axis).

## Acceptance criteria

- [ ] `parameters` selects a subset of the 5 product params; omitting it returns all five.
- [ ] `start` / `end` define a free hourly window; omitting `end` applies the configurable default
      horizon.
- [ ] A request whose extent exceeds a provider's temporal `Capability` is not admitted for that
      provider (whole-request containment).
- [ ] The tool description narrates the available envelope (parameters × max horizon) from the
      `Capability` union.
- [ ] Unit + mocked-transport integration tests cover subset selection, default horizon, and
      out-of-envelope extents.

## Blocked by

- Blocked by `issues/20260623_v1/002-core-5-parameters.md`
- Blocked by `issues/20260623_v1/002b-derived-wind-calculator.md`

## User stories addressed

- User story 2
- User story 3
- User story 10
