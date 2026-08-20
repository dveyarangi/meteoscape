# Max-reach tail serving

- **Status:** Planned (trigger-gated)
- **Type:** HITL
- **Depends on:** [second-provider fallback](./done/01-0121-second-provider-fallback.md) (the
  wholesale priority fall-through this widens),
  [vendor-call ledger](./01-0130-vendor-call-ledger.md) (prices the redundant refetch, one of the
  two triggers)
- **Trigger:** real demand for the beyond-primary tail, or the ledger pricing the redundant
  tail-ask refetch. Until one fires, the decided v1 shape stands and this ticket does not start.
- **Outcome:** A window reaching past the priority winner's holdings is served by a longer-reaching
  producer instead of being declined, and the redundant metered call on that path stops.

## Parent

Carved out of [#49](../concerns.md#49-spanning-asks-serve-the-primary-max-reach-is-unbuilt-policy),
which keeps the decided v1 shape and cites this ticket for the escape. The narration side of the same
seam is [#29](../concerns.md#29-narrated-reach-what-a-profile-promises).

## What goes wrong today

**The decided shape is not the defect.** Under intersective snapped admission a window spanning past
the priority winner's reach still admits it, and the winner answers with its own clipped span,
disclosed through `valid_time`. With a ~10 d primary under a composed ~16 d reach, every default ask
serves ~10 d. That was decided 2026-08-17 and stands.

**The defect is the tail ask.** Once a primary is configured, a window whose bounds fall past the
primary's holdings cannot reach the longer-reaching backstop through the root store at all:

```
ask: t ∈ [now, now+14d]          composed reach ~16 d      primary reach ~10 d
  │
  ├─ root Reservoir: retention sees the composed (rolling, long-horizon) declared
  │  axis as unsatisfied  →  refill
  │
  ├─ refill quantizes with ANY  →  the bounded window is destroyed before selection
  │     store.py:199 — the natural-fetch-unit decision of 0115
  │
  ├─ priority selection runs on an unbounded ask  →  buys the PRIMARY again
  │     └── one redundant metered vendor call, every time
  │
  ├─ holdings still end at ~10 d
  │
  └─ serving seam: capability-mismatch          reservoir.py:112-128, :146-153
```

Two costs: the backstop is unreachable exactly where it is needed, and a metered provider is billed
for a call whose result cannot satisfy the ask. The narrated horizon — the composed upper bound
([#29](../concerns.md#29-narrated-reach-what-a-profile-promises)) — over-promises the tail whenever
primary ≠ dominant, so the surface invites the ask it cannot serve.

**Why this is not a reconciler knob.** A per-request or per-profile "serve the window whole"
preference was considered and rejected: the root Reservoir's refill deliberately opens T, so the
bounded window is gone before producer selection runs. Ordering-by-window would be dead code on the
product path. The mechanism has to live where the bounds still exist.

## What to build

A path by which an ask past the priority winner's reach is answered by a producer that reaches it,
with no redundant call to the producer that cannot. What that path *is* belongs to this ticket's
align — the candidates below are the ones #49 accumulated, none chosen.

The redundant metered call must stop whichever mechanism wins: a refill that cannot satisfy the ask
is not worth its vendor spend, and this is the first place the project pays for a call it knows will
be short.

## Decisions this ticket's align owns

- **Where the bounds survive refill.** The root refill could keep the ask's T bounds for *selection*
  while the winner's own source-Reservoir still fetches its natural unit — this touches 0115's
  boundless-answer licence, so it cannot be decided without re-reading that licence.
- **Whether narration re-scopes to the primary's reach.** It would stop the over-promise at the
  edge, but moves producer knowledge to the surface, which
  [#29](../concerns.md#29-narrated-reach-what-a-profile-promises) resists on stated grounds.
- **Whether this is offering/reach-aware selection instead** —
  [#20](../concerns.md#20-provider-multi-resolution-offerings-offering-aware-selection)'s shape,
  which would subsume this case rather than special-case it.
- **Whether the tail is served whole or spliced.** Serving the composed span from one non-primary
  producer is not the same as amending the primary's near window with the backstop's tail; the
  latter is [#28](../concerns.md#28-reconciler-interface-selection-ordering-vs-per-cell-fold)'s
  per-cell fold and may make this ticket a consequence rather than a peer.

## Acceptance criteria

- [ ] A window reaching past the primary's holdings, with a backstop that reaches it, returns data
      for the servable span rather than `capability-mismatch`.
- [ ] That request issues **no** call to a producer whose declared reach cannot cover the ask —
      pinned by counting transport calls per producer, not by inspecting the selection path.
- [ ] The decided v1 shape is unchanged for asks *within* the primary's reach: the primary still
      wins and still answers its own clipped span.
- [ ] What the surface narrates and what a tail ask actually serves agree, or the disagreement is
      stated at the edge as a documented bound.
- [ ] The align's resolutions land in their durable homes, and
      [#49](../concerns.md#49-spanning-asks-serve-the-primary-max-reach-is-unbuilt-policy) retires
      into them.

## Out of scope

- **Nodata-padding a short answer to the requested window** —
  [#30](../concerns.md#30-response-membership-under-runtime-degraded-fallback)'s question, and it
  needs the same widenings from the other direction.
- **Cross-run combination** → [#9](../concerns.md#9-cross-run-combination).
- **Changing what a within-reach spanning ask serves** — that is the decided shape, not this work.
