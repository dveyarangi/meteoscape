# 003b — Request shaping

- **Status:** Partial
- **Depends on:** [003a — Profile reach](./003a-profile-reach.md) (which depends on 002, 002b)
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
**narrates the available envelope** — the served parameters, read off the woven root's `Capability`,
plus the profile's **reach**, resolved at build.

`reach` itself — the per-parameter `Domain` and the producer-selection rule — is
[003a](./003a-profile-reach.md). This ticket **consumes** it: the surface folds `min` over the
parameters *it* exposes (a surface-specific fold, so it stays at the edge) and uses the result for
both narration and the omitted-`end` default. Reach never feeds admission — `serves` stays the sole
authority, and the edge never pre-rejects a request against it.

**One reach, not a quality ladder** (→ [#29: quality is a policy outcome, not a capability](../concerns.md#29-narrated-reach-inner-bound-by-producer-selection)).
Build consequence: there is **no** `CadenceDef` hoist onto `OfferingSpec`, no composition-time envelope
derivation, no `ArbiterPolicy` threading, and no consistency test — reach has exactly one source, the
producers' declared footprints, read once at build.

**Already landed at 001 (Phase C):** the `parameters` input (unknown name → `bad-request`, default =
the woven root capability), dynamic served-parameters narration, `serves`-containment admission in the
`Arbiter`, and the supplied-`start`/`end` → `bad-request` stubs. This ticket's remaining substance:
make the window real (free `start`/`end` → exact-window fetch mapping), default an omitted `end` to
the reach end, extend narration with reach, **delete `Settings.default_horizon`**,
wire `resolve_reach` into `compose()` (below),
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
    `start`** and let admission answer. The edge must not pre-reject: reach may *understate* (it is
    the spatially-dominant producer's window, and a regional producer may reach further), so a `start`
    past it may still be servable, and the edge would be overruling the authority with an
    understatement.

**Wiring reach into the surface (session 0014).** [003a](./003a-profile-reach.md) delivers
`resolve_reach(ProfileDef) -> Mapping[ParameterId, Domain]`; this ticket **calls it**. `compose()`
gains one step — `binders → ProfileDef → weave → resolve_reach → Gateway` — and hands the map to the
surface adapter alongside the woven root. The Weaver is untouched: it stays a pure graph constructor,
and reach never becomes a node member.

A misconfigured profile therefore fails at **startup** with a `CompositionError` naming the conflicting
producers, and — because the selection is made at build while the winner's `RollingAxis` stays live —
the narrated window and the default `end` still track the clock with no staleness and no per-request
resolution.

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
- [ ] A profile with `{Europe × 16 d, Global × 10 d}` narrates 10 d, and its default window is
      admissible at both a European and an American point (003a supplies the reach rule; this verifies
      the edge consumes it correctly).
- [ ] A request whose extent exceeds a provider's temporal `Capability` is not admitted for that
      provider (whole-request containment). Out-of-envelope windows (past `start`, over-horizon `end`)
      resolve through admission as `capability-mismatch` — the edge never pre-rejects against `reach`,
      which understates on T (a regional producer may reach further than the profile's dominating one)
      and is exact on X/Y; `bad-request` is reserved for
      windows malformed in themselves (unparsable, `start > end`).
- [ ] The tool description narrates the served parameters (off the woven root's `Capability`) plus the
      profile's reach (off the build-time map).
- [ ] `compose()` calls `resolve_reach` and hands the map to the surface; a profile with unresolvable
      X/Y dominance fails at **startup** with a `CompositionError`, never on the request path. The
      selection is fixed at build while the winner's `RollingAxis` stays live, so the default window
      still tracks the clock.
- [ ] Unit + mocked-transport integration tests cover subset selection, the reach-end default, and
      out-of-envelope extents.

## User stories addressed

- User story 2
- User story 3
- User story 10
