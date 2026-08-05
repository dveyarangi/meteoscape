# Request shaping

**Legacy id:** 003c

> Formerly numbered **003b**; renumbered when 003b (capability domain) was inserted ahead of it.

- **Status:** Ready — the window semantics ride
  [m4 — Snapped request mode](./done/01-0100-snapped-t-request-mode.md), which landed 2026-08-04.
- **Plan:** [RFC 0008](../rfc/0008-20260725-003c-request-shaping.md) (**re-staged 2026-08-05**
  against the landed Snapped-T mode; the superseded edge-clamp staging is preserved in its
  §Superseded approach as that decision's record).
- **Depends on:** [m4](./done/01-0100-snapped-t-request-mode.md) (done), and
  [003b — Capability carries its domain](./done/01-0060-capability-domain.md) (which reshapes
  [003a](./done/01-0040-profile-reach.md); 003a depends on 002, 002b).
- **Outcome:** Free `start`/`end` request windows (ISO datetimes) served as the caller's bounds ∩
  the live window, plus reach-based narration; `Settings.default_horizon` deleted.

## Parent PRD

`docs/v1-requirements.md`

## Decision trail

The window semantics settled in the 2026-07-25 align through three shapes — containment-rejection
→ edge clamping → **Snapped-T resolution** — plus one reversal of a session-0013 rule (bare-date
day-cells → datetimes only). The reasoning lives at its owners:
[m4](./done/01-0100-snapped-t-request-mode.md) (why fitting belongs to resolution, the mode sketch) and
[RFC 0008](../rfc/0008-20260725-003c-request-shaping.md)'s hold banner (the clamp record). The
rules below are the settled result.

## What to build

Make the request flexible at the edge. The MCP adapter accepts optional `parameters` (a subset of
the **6 product** params — temperature, precipitation, wind speed, wind direction, humidity, cloud
cover; the internal `wind_u` / `wind_v` are not requestable; default all), `start`, and `end`, and
builds the canonical `Selection`: a lat/lon **point** `Domain` whose T axis is a **Snapped-T**
request — the caller's bounds as raw instants ([m4](./done/01-0100-snapped-t-request-mode.md)). Resolution
serves `bounds ∩ the winner's live window`; admission on a snapped T axis is **intersective**
(enumerable requests keep whole-request containment); a **no-overlap** window resolves as
`capability-mismatch` through admission — the edge never rejects on reach's word, and
`bad-request` stays purely **syntactic**. The tool description **narrates the available
envelope** — the served parameters plus the profile's **reach**, both read off the woven root's
`Capability`.

`reach` — the per-parameter `Domain` a `Capability` publishes — is
[003b](./done/01-0060-capability-domain.md). This ticket consumes it for **narration**: the surface
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

**Window → bounds semantics.** The edge turns two strings into **snapped bounds** — raw instants,
no step; the *resolver*'s grid supplies anchor and step and authors the output lattice:

- **Parse** ISO 8601 **datetimes only**: offset-aware converts to UTC, **naive reads as UTC**
  (narrated). Unparsable → `bad-request`. A **bare date** (or week date — same probe) →
  `bad-request` with guidance ("use a datetime like 2026-07-20T00:00"): loud rejection preserves
  the session-0013 rationale — never a silently short answer — without day-cell semantics.
- **`start` rides as the raw instant** — the *resolver* includes the tick whose cell *contains*
  `start`, flooring on **its own** lattice (the edge holds no step to floor with —
  [m4](./done/01-0100-snapped-t-request-mode.md)). Never a ceil semantics: the stretch the caller asked for
  is served, not dropped.
- **`end` is inclusive** of the tick containing it — the raw instant rides as the upper bound and
  "last tick ≤ end" at resolution delivers it. An 18:30 `end` includes the 18:00 tick, and
  **`start == end` yields exactly one tick** — the "current conditions" request, which falls out
  rather than needing its own path.
- **Omitted `start` → `now`** — an edge-authored raw bound, never an open lower side; the
  resolver's cell-containment yields the current tick.
- **Omitted `end` → the folded reach end, read live** — a default *hint*, not a promise:
  resolution still serves `bounds ∩ the winner's live window`, so a stale read trims harmlessly
  (open-ended bounds are a deferred m4 form —
  [#30](../concerns.md#30-response-membership-under-runtime-degraded-fallback)'s diverging-reach
  trigger). `Settings.default_horizon` is **deleted**: when the caller does not say how far, they
  get what the profile serves. The served end is **absolute** — `start` clips the beginning, never
  shifts the end.
- **Backwards window** (raw instants; implicit `start = now` when omitted) → `bad-request`.
  A well-formed window with **no overlap** with the served range (e.g. history) →
  `capability-mismatch` via admission.

**Reading reach at the surface.** [003b](./done/01-0060-capability-domain.md) puts the per-parameter
`Domain` on the `Capability` ([ADR-0007](../adr/0007-capability-carries-its-domain.md)), so
**nothing needs threading**: the surface reads the profile's reach off the woven root
(`gateway.best_view.capability.reach(p)`) and `compose()` keeps its signature. Geometry needs no
pass of its own: each node's `Capability` composes its `Domain` as the graph is built, so an
unresolvable one fails at `weave`, and a misconfigured profile fails at **startup** with a
`CompositionError` naming the culprit. The narrated horizon stays true with no staleness (a
`RollingAxis` length is clock-invariant); the served window itself is resolved per request by the
winner.

No maximum-window guard: an absurd `end` just bounds a snapped request that resolution trims; a
snapped axis carries only bounds, so any window costs O(1) to state.

Output resolution stays hourly (no `step` input). See `docs/v1-requirements.md` (Request / tool
contract, Time axis).

## Acceptance criteria

- [ ] `parameters` selects a subset of the 6 product params; omitting it returns all six. An
      **explicitly empty list is `bad-request`** (an empty request is meaningless; `None` keeps
      meaning "all served"); an empty *resolved* set (the no-provider profile) is
      `capability-mismatch` at the edge.
- [ ] `start` / `end` define a free hourly window from **ISO datetimes only**: naive reads as UTC,
      a bare date is `bad-request` with guidance, `start`'s containing tick is served
      (resolver-side cell containment), `end` is inclusive of the tick containing it,
      `start == end` returns a single tick, omitting `start` begins at the tick containing now,
      and a backwards window is `bad-request`.
- [ ] Omitting `end` fills the bound from the **folded reach end, read live** (a hint —
      resolution's intersection makes staleness harmless); `Settings.default_horizon` is gone;
      the served end is absolute (`start` clips, never shifts it).
- [ ] Bounds outside the served range yield the **servable part** — resolution serves
      `bounds ∩ the winner's live window` ([m4](./done/01-0100-snapped-t-request-mode.md)); a no-overlap
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
- [ ] **Divergent winner domains are assessed at this landing** (inherited from
      [m4](./done/01-0100-snapped-t-request-mode.md), [RFC 0009](../rfc/done/0009-20260725-m4-snapped-t-request-mode.md)
      fact 9 / decision 9). A request mixing direct and derived parameters resolves through **two**
      winners — the Provider and the wind `Calculator` — each issuing its own vendor fetch. Under
      snapped, each answer's T axis derives from its own response, so a window roll between the two
      fetches (or a vendor length change) makes the Arbiter's closed-projection check fail the whole
      request with `runtime-failure`. m4 pins the behaviour as loud and deliberate; **this ticket is
      where it becomes reachable from the edge**, ~~so it must land with a judgement recorded:
      accepted as rare-and-loud, mitigated, or escalated to
      [#30](../concerns.md#30-response-membership-under-runtime-degraded-fallback) /
      [#28](../concerns.md)~~ — **judged at the 2026-08-05 re-stage align: accepted as
      rare-and-loud, for exactly one ticket.** No mitigation is built — window-freezing and
      domain-folding stay rejected on [RFC 0009](../rfc/done/0009-20260725-m4-snapped-t-request-mode.md)
      decision 11's grounds, and retention is the mechanism, not a workaround:
      [006](./01-0115-retentive-store-freshness.md) follows this ticket directly in the queue
      (reordered at the same align) and collapses the second fetch **on the warm path** (a
      fully-fresh repeat is served with no provider call). The residue — a cold store still issues
      two disjoint-parameter fetches, since neither today's engaged-tap fetch nor 006's
      per-parameter refill widens across parameters — is owned by 006's **refill-scope** decision.
      The landing re-confirms this judgement against the shipped behaviour rather than re-opening
      it.
- [ ] **The edge's request representation is settled here, not assumed.** This ticket is where
      `build_selection` stops issuing exact `GridDomain` requests and issues snapped ones, which makes it
      a trigger for
      [#42](../concerns.md#42-two-request-representations-so-resolution-cannot-be-a-method): ~~either the
      request side keeps two representations (and `ground` stays a function taking the request), or the
      edge's migration is the moment it narrows to one. Record the call; the edge is the request author
      whose choice the rest inherit.~~ **The call, recorded at the 2026-08-05 re-stage align: the
      split stays.** The edge authors a `SelectionDomain` and `ground` remains a function — the
      second in-tree request author that would make narrowing load-bearing
      ([006](./01-0115-retentive-store-freshness.md)'s refill) does not exist yet, and the
      narrowing's costs (widening `SelectableAxis`, restating `resample`'s target, pre-deciding the
      refill representation) all remain as #42 lists them. Narrowing re-arises at 006 with its
      author in hand; this criterion is satisfied by the edge migration matching the recorded call.

## User stories addressed

- User story 2
- User story 3
- User story 10
