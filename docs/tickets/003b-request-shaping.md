# 003b — Request shaping

- **Status:** Partial
- **Depends on:** [003a — `Capability.reach`](./003a-capability-reach.md) (which depends on 002, 002b)
- **Outcome:** Free request windows, plus reach-based narration and default windows at the edge.

## Parent PRD

`docs/v1-requirements.md`

## What to build

Make the request flexible at the edge. The MCP adapter accepts optional `parameters` (a subset of the
**6 product** params — temperature, precipitation, wind speed, wind direction, humidity, cloud cover;
the internal `wind_u` / `wind_v` are not requestable; default all), `start`, and `end`, and builds the canonical
`Selection` accordingly — a lat/lon
**point** `Domain` plus an hourly `valid_time` extent. When `end` is omitted the window runs to the
profile's **reach end** — what the caller gets when they do not say how far; `start` / `end` form a
free window (no interval enum — the `Domain` models
arbitrary extents). The `Arbiter` admits a provider per parameter only when its `Capability`
**temporally contains** the requested extent (whole-request `Domain`-containment). The tool description
**narrates the available envelope** — the served parameters plus the profile's **reach**, read off the
woven root's `Capability`.

`reach` itself — the per-parameter `Domain` and its per-axis composite folds — is
[003a](./003a-capability-reach.md). This ticket **consumes** it: the surface folds `min` over the
parameters *it* exposes (a surface-specific fold, so it stays at the edge) and uses the result for
both narration and the omitted-`end` default. Reach is **advisory** — `serves` stays the sole
admission authority, and the edge never pre-rejects a request against it.

**One reach, not a quality ladder.** Intermediate drafts narrated a quality/completeness pair; dropped
because **quality is a policy outcome, not a capability** — the response already reports it per
parameter via provenance, and declaring it leaked priority, flipped meaning with the reconciler mode,
and was unverifiable through `serves`. Quality tiers belong in **separate profiles behind separate
tools**, matching the sibling-tool precedent (session 0009). Consequently there is **no** `CadenceDef`
hoist onto `OfferingSpec`, no composition-time envelope derivation, no `ArbiterPolicy` threading, and
no consistency test: reach has exactly one source, and mode-correctness is inherited because the
capability composite already encodes the admission semantics
([#29](../concerns.md#29-narrated-reach-per-axis-join-conservative-on-extent-axes)).

**Already landed at 001 (Phase C):** the `parameters` input (unknown name → `bad-request`, default =
the woven root capability), dynamic served-parameters narration, `serves`-containment admission in the
`Arbiter`, and the supplied-`start`/`end` → `bad-request` stubs. This ticket's remaining substance:
make the window real (free `start`/`end` → exact-window fetch mapping), default an omitted `end` to
the reach end, extend narration with reach, **delete `Settings.default_horizon`**,
and exercise out-of-envelope
admission with real free windows (Phase C's fixed 168 h window never leaves the envelope). Concern #24
is **resolved** (session 0011 → [ADR-0002](../adr/0002-data-model.md) /
[ADR-0004](../adr/0004-producer-resolution-and-capability.md)); the request keeps 002's edge-authored
**vantage** Z window unchanged.

**Not in this ticket (session 0013):** **alias desugaring / exact-mode Z**. The mechanism is already a
recorded contract seam — the edge alias table and the `VantageAxis`-vs-`RegularAxis`-cell request modes
live in [architecture.md](../architecture.md#contract-surfaces) (Surface adapter) and
[ADR-0002](../adr/0002-data-model.md) — but v1 has **no driver** for it: `soil_temperature_6cm` is not a
v1 parameter, `cloud_cover_low` needs the deferred Overlap Calculator, and `temperature_2m` is a
semantic no-op against the count-1 `2 m` declaration (same winner, same values; only the response Z
label changes). It re-arises from its product point — derived parameters as composable DAGs
([roadmap](../product-roadmap.md) Phase 4) — with no decision to rediscover.

**Window → lattice semantics (session 0013).** The edge authors the hourly output lattice, so it must
turn two strings into a `RegularAxis(anchor, 1h, count)`:

- **Parse** ISO 8601; offset-aware converted to UTC, **naive interpreted as UTC** (narrated in the
  description). Unparsable → `bad-request`.
- **A date with no time means the day it names** — `start="2026-07-20"` → 00:00, `end="2026-07-20"` →
  through the **23:00 tick**. This is the inclusive-`end` rule applied at the granularity the caller
  supplied: `end` is inclusive *of the cell containing it*, a date is a day-cell. Reading a bare date
  as midnight instead would make "through the 20th" return **one hour** of the 20th — a silently short
  answer. Consequence, accepted: `"2026-07-20"` and `"2026-07-20T00:00"` differ, because one names a
  day and the other an instant.
- **`start` floors to the hour** — `anchor = floor(start, 1h)`, the tick whose cell *contains* `start`.
  Never `ceil`: that would silently drop the stretch the caller asked for.
- **`end` is inclusive**, same flooring — `count = floor((end − anchor) / 1h) + 1`. So an 18:30 `end`
  includes the 18:00 tick, and **`start == end` yields exactly one tick** — the "current conditions"
  request, which falls out rather than needing its own path.
- **Omitted `start` → `floor(now, 1h)`** (unchanged from Phase C).
- **Omitted `end` → the reach end**: `min` over the requested parameters of `reach(p)`'s `valid_time`
  upper bound, read **live at request time**. `Settings.default_horizon` is **deleted** — when the
  caller does not say how far, they get what the profile serves. Because `RollingAxis.extent` resolves
  against the clock, this is the *exact* footprint end, so the default request is admissible by
  construction (no anchor overshoot, no conservative shrink).
  - The reach end is **absolute, not a length from `start`**. Given `start` with `end` omitted, the
    window is `[start, reach_end]` — `start` clips the beginning; it does not push the end outward.
    (A length-from-`start` reading would overshoot the footprint whenever `start` is in the future.)
  - **Degenerate case** — `start` beyond the reach end yields `count ≤ 0`. Build a **single tick at
    `start`** and let admission answer. The edge must not pre-reject: the T fold is *conservative*, so
    a `start` past it may still be servable by some member, and the edge would be overruling the
    authority with an understatement.

No maximum-window guard: reach already bounds the request, an absurd `end` is an ordinary
`capability-mismatch`, and an axis is `anchor + step + count`, so a large `count` costs O(1) to build
before admission rejects it.

Output resolution stays hourly (no `step` input). See `docs/v1-requirements.md` (Request / tool
contract, Time axis).

## Acceptance criteria

- [ ] `parameters` selects a subset of the 6 product params; omitting it returns all six.
- [ ] `start` / `end` define a free hourly window: naive ISO reads as UTC, a bare date means the day
      it names (`end="2026-07-20"` runs through the 23:00 tick), `start` floors to its containing
      tick, `end` is inclusive, and `start == end` returns a single tick (current conditions).
      Omitting `start` anchors at `floor(now, 1h)`.
- [ ] Omitting `end` runs the window to the **reach end** — `min` over requested parameters of
      `reach(p)`'s `valid_time` upper bound, read live — and that default request is admissible by
      construction. `Settings.default_horizon` is gone. Given `start`, the reach end is absolute (it
      clips, it does not shift); `start` past it yields a single tick that admission judges.
- [ ] A profile with `{Europe × 16 d, Americas × 10 d}` narrates 10 d, and its default window is
      admissible at both a European and an American point (003a supplies the fold; this verifies the
      edge consumes it correctly).
- [ ] A request whose extent exceeds a provider's temporal `Capability` is not admitted for that
      provider (whole-request containment). Out-of-envelope windows (past `start`, over-horizon `end`)
      resolve through admission as `capability-mismatch` — the edge never pre-rejects against `reach`,
      which understates on T and over-states on X/Y (session 0013); `bad-request` is reserved for
      windows malformed in themselves (unparsable, `start > end`).
- [ ] The tool description narrates the served parameters plus the profile's reach, read off the woven
      root's `Capability`.
- [ ] Unit + mocked-transport integration tests cover subset selection, the reach-end default, and
      out-of-envelope extents.

## User stories addressed

- User story 2
- User story 3
- User story 10
