# One timeline algebra, two geometries

- **Status:** Done (2026-08-22)
- **Type:** AFK
- **Kind:** Maintenance
- **Plan:** [One timeline algebra RFC](../../rfc/done/01-0114-timeline-shape-generalization.md) — three
  green stages: extract the four answers in place (three new members; `capability` was already
  abstract on `Provider`), split base from `RollingTimeline`, then guard the family contract.
- **Blocks:** [station observation serving](../01-0124.0030-station-observation-serving.md) — its
  producer is the second geometry this ticket makes room for.
- **Outcome:** `TimelineProvider`'s algebra — fetch, interpret, tick check, grid build, crop —
  serves more than one geometry: it becomes the shared base of a family, with the rolling
  behaviour moved into `RollingTimeline`. Open-Meteo and TWC resolve exactly as before.

## Parent

Carved out of the [Mongo obs source](../01-0124-mongo-obs-source.md) at its serving plan
(2026-08-22), on the [composition lifetime](./01-0116-composition-lifetime.md) precedent: a
general seam that several producers will share is *chosen* on its own, not invented inside the first
implementation that needs it.

## Why a subclass family and not a sibling wrapper

The 0124 align resolved "a sibling wrapper beside `TimelineProvider`" from
[architecture § Provider](../../architecture.md#provider-leaf-manifold)'s rule (*a new geometry adds a
wrapper*). Planning measured what that would cost: of `TimelineProvider`'s ~243 lines, **~160 are
identical** for a station producer — `project`'s orchestration, `_interpret`, `_lattice_of`,
`_answered_geometry`, `_delivered`, `_point_of`, `_window_of`. A sibling would fork them, giving
every later fix two homes.

Only four answers differ, and they are the producer's own facts rather than separable objects:
where it lives, how a request lands on it, how it signs an answer, and — for a producer whose facts
are fetched rather than fixed — how it refreshes them. One of the four, the published capability, is
already an abstract member of `Provider`, so only three are new. Nothing else would ever construct
or consume such an object, and it would need the same `taps` / `step` / `clock` the provider already
holds.
That is a specialization, not a collaborator; `Provider` → `TimelineProvider` is already an
inheritance chain, so the rule's "adds a wrapper" reads here as *adds a member of the family*.

## What to build

`TimelineProvider` keeps every algebraic step and becomes the family's base; the rolling facts move
into `RollingTimeline`, which Open-Meteo and TWC construct. The four varying answers become the base's
declared extension points — the geometry a producer publishes, how a request grounds onto it, how an
answer is signed, and an await-able refresh that a producer with fixed facts does nothing in.

Grounding takes the **engaged parameter ids**, not the tap table: `_resolve` reads only
`tap.produces` today, and a geometry that is not a point series must be able to answer the same
question. This is what keeps the family open to the gridded-NWP and sounding wrappers
[edge/provider.md](../../edge/provider.md) already names as the next producer shapes.

**Out of scope:** any behaviour change, any new geometry (that is
[station observation serving](../01-0124.0030-station-observation-serving.md)), and the `Probe` seam,
which is untouched — this ticket splits *shape*, not *vendor face*.

## Acceptance criteria

- [x] Open-Meteo and TWC serve exactly as before, pinned by the existing deterministic and parity
      suites with no test edited beyond construction lines.
- [x] The shared algebra has one home: no method of `TimelineProvider` is duplicated in a family
      member, machine-checked by a guard test over the family's method names.
- [x] A family member declaring a non-separable geometry can ground a bounded-T request without the
      base being changed — proven by a fake member in tests, since the first real one is
      [station observation serving](../01-0124.0030-station-observation-serving.md).
- [x] The refresh extension point is a no-op for a fixed-facts producer, and costs it no call —
      pinned by counting, not by inspection.

## Parent scope addressed

Unblocks the parent's second and third slices without their inventing the seam.
