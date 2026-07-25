# 003c — Request shaping

> Formerly numbered **003b**; renumbered when 003b (capability domain) was inserted ahead of it.

- **Status:** Planned — the window semantics ride
  [m4 — Snapped request mode](./m4-snapped-t-request-mode.md); m4 must land first.
- **Plan:** [RFC 0008](../rfc/0008-20260725-003c-request-shaping.md) (**on hold** — it planned the
  superseded edge-clamp approach and is kept as that decision's record; its surviving decisions
  stand, and it is re-staged after m4 lands).
- **Depends on:** [m4](./m4-snapped-t-request-mode.md) (Ready, design tentative), and
  [003b — Capability carries its domain](./done/003b-capability-domain.md) (which reshapes
  [003a](./done/003a-profile-reach.md); 003a depends on 002, 002b).
- **Outcome:** Free `start`/`end` request windows (ISO datetimes) served as the caller's bounds ∩
  the live window, plus reach-based narration; `Settings.default_horizon` deleted.

## Parent PRD

`docs/v1-requirements.md`

## Decision trail

The window semantics settled in the 2026-07-25 align through three shapes — containment-rejection
→ edge clamping → **Snapped-T resolution** — plus one reversal of a session-0013 rule (bare-date
day-cells → datetimes only). The reasoning lives at its owners:
[m4](./m4-snapped-t-request-mode.md) (why fitting belongs to resolution, the mode sketch) and
[RFC 0008](../rfc/0008-20260725-003c-request-shaping.md)'s hold banner (the clamp record). The
rules below are the settled result.

## What to build

Make the request flexible at the edge. The MCP adapter accepts optional `parameters` (a subset of
the **6 product** params — temperature, precipitation, wind speed, wind direction, humidity, cloud
cover; the internal `wind_u` / `wind_v` are not requestable; default all), `start`, and `end`, and
builds the canonical `Selection`: a lat/lon **point** `Domain` whose T axis is a **Snapped-T**
request — hourly step plus the caller's bounds ([m4](./m4-snapped-t-request-mode.md)). Resolution
serves `bounds ∩ the winner's live window`; admission on a snapped T axis is **intersective**
(enumerable requests keep whole-request containment); a **no-overlap** window resolves as
`capability-mismatch` through admission — the edge never rejects on reach's word, and
`bad-request` stays purely **syntactic**. The tool description **narrates the available
envelope** — the served parameters plus the profile's **reach**, both read off the woven root's
`Capability`.

`reach` — the per-parameter `Domain` a `Capability` publishes — is
[003b](./done/003b-capability-domain.md). This ticket consumes it for **narration**: the surface
folds `min` over the parameters *it* exposes (a surface-specific fold, so it stays at the edge).
`serves` stays the sole admission authority ([ADR-0007](../adr/0007-capability-carries-its-domain.md)).

**One reach, not a quality ladder** (→ [#29: quality is a policy outcome, not a capability](../concerns.md#29-narrated-reach-what-a-profile-promises)).
Build consequence: there is **no** `CadenceDef` hoist onto `OfferingSpec`, no composition-time envelope
derivation, no `ArbiterPolicy` threading, and no consistency test — reach has exactly one source, the
`Capability` each node publishes, composed as the graph is built.

**Already landed at 001 (Phase C):** the `parameters` input (unknown name → `bad-request`, default =
the woven root capability), dynamic served-parameters narration, containment admission in the
`Arbiter`, and the supplied-`start`/`end` → `bad-request` stubs. This ticket's remaining substance:
turn `start`/`end` into snapped bounds the resolver fits, extend narration with reach, **delete
`Settings.default_horizon`**, and exercise out-of-range windows for real (Phase C's fixed 168 h
window never left the envelope). Startup validation needs no work: `validate_calculators` is
`weave`'s own first step (`weaver.py`; asserted by `test_server.py`), so a misconfigured profile
already fails at startup before any `Store` is allocated. Concern #24 is **resolved** (session
0011 → [ADR-0002](../adr/0002-data-model.md) /
[ADR-0004](../adr/0004-producer-resolution-and-capability.md)); the request keeps 002's
edge-authored **vantage** Z window unchanged.

**Not in this ticket (session 0013):** **alias desugaring / exact-mode Z**. The mechanism is already a
recorded contract seam — the edge alias table and the `VantageAxis`-vs-`RegularAxis`-cell request modes
live in [architecture.md](../architecture.md#contract-surfaces) (Surface adapter) and
[ADR-0002](../adr/0002-data-model.md) — but v1 has **no driver** for it: `soil_temperature_6cm` is not a
v1 parameter, `cloud_cover_low` needs the deferred Overlap Calculator, and `temperature_2m` is a
semantic no-op against the count-1 `2 m` declaration (same winner, same values; only the response Z
label changes). It re-arises from its product point — derived parameters as composable DAGs
([roadmap](../product-roadmap.md) Phase 4) — with no decision to rediscover.

**Window → bounds semantics.** The edge turns two strings into **snapped bounds** (hourly step);
the *resolver* authors the output lattice:

- **Parse** ISO 8601 **datetimes only**: offset-aware converts to UTC, **naive reads as UTC**
  (narrated). Unparsable → `bad-request`. A **bare date** (or week date — same probe) →
  `bad-request` with guidance ("use a datetime like 2026-07-20T00:00"): loud rejection preserves
  the session-0013 rationale — never a silently short answer — without day-cell semantics.
- **`start` floors to the hour** — the lower bound is `floor(start, 1h)`, so the tick whose cell
  *contains* `start` survives resolution. Never `ceil`: that would silently drop the stretch the
  caller asked for.
- **`end` is inclusive** of the tick containing it — the raw instant rides as the upper bound and
  "last tick ≤ end" at resolution delivers it. An 18:30 `end` includes the 18:00 tick, and
  **`start == end` yields exactly one tick** — the "current conditions" request, which falls out
  rather than needing its own path.
- **Omitted `start` → `floor(now, 1h)`** — an edge-authored bound, never an open lower side.
- **Omitted `end` → open upper bound** — the winner serves to its own live window end;
  `Settings.default_horizon` is **deleted**: when the caller does not say how far, they get what
  the profile serves. The served end is **absolute** — `start` clips the beginning, never shifts
  the end.
- **Backwards window** (raw instants; implicit `start = floor(now)` when omitted) → `bad-request`.
  A well-formed window with **no overlap** with the served range (e.g. history) →
  `capability-mismatch` via admission.

**Reading reach at the surface.** [003b](./done/003b-capability-domain.md) puts the per-parameter
`Domain` on the `Capability` ([ADR-0007](../adr/0007-capability-carries-its-domain.md)), so
**nothing needs threading**: the surface reads the profile's reach off the woven root
(`gateway.best_view.capability.reach(p)`) and `compose()` keeps its signature. Geometry needs no
pass of its own: each node's `Capability` composes its `Domain` as the graph is built, so an
unresolvable one fails at `weave`, and a misconfigured profile fails at **startup** with a
`CompositionError` naming the culprit. The narrated horizon stays true with no staleness (a
`RollingAxis` length is clock-invariant); the served window itself is resolved per request by the
winner.

No maximum-window guard: an absurd `end` just bounds a snapped request that resolution trims; a
snapped axis carries `step + bounds`, so any window costs O(1) to state.

Output resolution stays hourly (no `step` input). See `docs/v1-requirements.md` (Request / tool
contract, Time axis).

## Acceptance criteria

- [ ] `parameters` selects a subset of the 6 product params; omitting it returns all six. An
      **explicitly empty list is `bad-request`** (an empty request is meaningless; `None` keeps
      meaning "all served"); an empty *resolved* set (the no-provider profile) is
      `capability-mismatch` at the edge.
- [ ] `start` / `end` define a free hourly window from **ISO datetimes only**: naive reads as UTC,
      a bare date is `bad-request` with guidance, `start` floors to its containing tick, `end` is
      inclusive of the tick containing it, `start == end` returns a single tick, omitting `start`
      anchors at `floor(now, 1h)`, and a backwards window is `bad-request`.
- [ ] Omitting `end` leaves the snapped upper bound **open**: the winner serves to its own live
      window end; `Settings.default_horizon` is gone; the served end is absolute (`start` clips,
      never shifts it).
- [ ] Bounds outside the served range yield the **servable part** — resolution serves
      `bounds ∩ the winner's live window` ([m4](./m4-snapped-t-request-mode.md)); a no-overlap
      window is `capability-mismatch` via intersective admission; enumerable-mode admission is
      unchanged elsewhere; the response's `valid_time` shows what was served. (Mixed-reach
      membership under a future second provider →
      [#30](../concerns.md#30-response-membership-under-runtime-degraded-fallback).)
- [ ] The tool description narrates the served parameters plus the profile's reach, both off the woven
      root's `Capability`. The reach is narrated as a **relative horizon** (*"out to N ahead of the
      latest run"*), never as absolute instants: the description is built once and frozen for the
      process lifetime, so an absolute date would be stale within the hour. A `RollingAxis`'s length is
      invariant even as its bounds move, which is what makes the relative form true indefinitely.
- [ ] Unit + mocked-transport integration tests cover subset selection, the open-`end` default,
      snapped fitting of out-of-range bounds, and the no-overlap mismatch; the live snapped
      end-to-end validation is this ticket's landing parity run.

## User stories addressed

- User story 2
- User story 3
- User story 10
