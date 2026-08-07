# Retentive store and freshness

**Legacy id:** 006

- **Status:** Ready — moved ahead of
  [011 — Visual Crossing provider](./01-0120-visual-crossing-provider.md) on 2026-08-05 (003c's
  re-stage align): retention is the *mechanism* that collapses the mixed-request double fetch,
  whose divergence [003c](./done/01-0110-request-shaping.md) accepts for exactly one ticket on the
  strength of this ordering.
- **Depends on:** [002 — Core canonical parameters](./done/01-0030-core-5-parameters.md)
- **Outcome:** Fresh reuse, partial refill, and single-origin whole-window replacement.

## Parent PRD

`docs/v1-requirements.md`

## What to build

Replace the stub `Store` with the real **retentive in-memory `Store`** — a
`Writable` Manifold with **private per-axis lattices** (hourly + spatial; no public `domain` —
[ADR-0006](../adr/0006-materialization-granularity-and-store-shape.md)), **unit-granular** (units
`(parameter, per-axis cells, window)`; `assimilate` splits a native record into units), wired into
**both** positions (each `Source` and the best view). `project` runs the `Reservoir` pipeline:
`quantize` the request onto the store lattices (per axis: snap + widen to whole assimilable units — a
parameter's timeline at a spatial cell; identity on axes without a lattice; **`ANY` on axes the unit
spans wholly** — for v1's timeline store that is `T` and `Z`, see below), read the per-unit
**{held, fresh, origin}** report (**held** = the store's own `capability`; **fresh** =
`expiration > now` off each `ParameterData`'s provenance `summary` — no `is_current` operation
exists, [ADR-0001](../adr/0001-manifold-algebra-and-composition.md)), serve units that are **fresh and
single-origin**, and **refill the missing/stale parameters whole** from the child in **one** call
(`child.project(store_shape)`), then `assimilate` (replacing whole units atomically). The Source's
read-back relabels matched native cells onto the handed shape (the fact→product boundary).

**Native geometry must survive the fetch (session 0013).** `quantize` asks **`ANY`** on the axes the
unit spans entirely; by shape-correspondence ([ADR-0001](../adr/0001-manifold-algebra-and-composition.md))
the Provider then answers **multi-domain** — temperature at 2 m beside wind at 10 m — instead of
flattening onto one requested Z. This is what lets the store key units by **native** cells while still
paying for **one** vendor fetch; a fully-enumerable ask would force the flatten and destroy the cells
before they could be stored, and asking per parameter group would multiply vendor traffic for data one
call returns. **Which axes are `ANY` is derived from the unit definition, not hardcoded** — a grid
store would invert it (`X/Y` whole, `T` celled), so the `Reservoir` stays generic.

**`assimilate` consumes the answer, not a pre-sliced record.** The store slices it per parameter,
because only the store holds both halves of each unit `Selection` — `X/Y`+`T` from its private
lattice, the native cell from the answer. Having the `Reservoir` slice would leak the lattice out of
the store. *(Tentative — revisit the concrete shapes when building them here.)*

**Retire the eager flatten.** `open_meteo.project` currently ends in `_assemble(records, selection)`,
labelled an "interim fold". Under a fully-enumerable ask that is *correct* behaviour, not a shortcut —
which is why it must be the **ask** that changes. m4 sharpened the same point from the other side: it
states the law `_assemble` rests on — *native records must ground identically on every axis the
request pins or snaps* — and declines when they do not. `ANY` is precisely the licence to break that
law on one axis, so this ticket lifts it there and mints the multi-domain carrier that `ANY` justifies
(m4 deliberately did not: a carrier for a request that asked for one geometry only defers the fold to
callers that all want it folded). `_assemble` remains as the multi-domain answer's own
`project` (used when someone does hand it a fully enumerable Selection); it stops being applied
eagerly at fetch. ADR-0006 lists per-fetch flattening among its **rejected** options ("lossy on the
data plane; the store cannot answer availability honestly") — that rejection becomes live here,
because this is the ticket where anything is retained at all.

Freshness is read straight off each `ParameterData`'s `expiration` (`fresh ⇔ expiration > now`). Refill
is **per-parameter and spatial** — a fresh parameter is reused while a stale one is refetched, each
parameter resolved independently; a parameter's `valid_time` window stays **single-origin** (temporal
miss or extension refetches the whole window). A separate **configurable retention interval** bounds
memory (housekeeping only; the `Arbiter` never serves stale entries — LRU declined). See
`docs/v1-requirements.md` (v1 invariants, Config & secrets) and `docs/architecture.md` (Reservoir,
Store).

**Store-lattice representation — resolved at m4 (2026-07-26).** The question was whether to mint a
declared-lattice axis (open extent: `anchor + step`, where `RegularAxis` fixes all three of
`(anchor, step, count)`) or to narrow what `quantize` actually requires. It is the second, and m4
built the narrowing: **`Axis.clip(bounds)`**, abstract on the axis base — one question a retention
grid answers with the part of itself the request asks for, never with an enumeration. A store's
retention grid answers it the way `RollingAxis` does, materialising from the retention window at the
clock, so no new axis kind is minted and the representation stays the `Store`'s own business
([ADR-0006](../adr/0006-materialization-granularity-and-store-shape.md)).

**`quantize` is `ground`'s store-side sibling** ([RFC 0009](../rfc/done/0009-20260725-m4-snapped-t-request-mode.md)):
the same per-axis fold of a request against a lattice, enclosing where `ground` clips, and it is where
the fold's **`ANY`** case lands — the axis the unit spans wholly takes the answering axis whole.
Reading the request-side verb before writing this one is the cheapest way to keep the two from
diverging.

**Refill scope — decide at this ticket's align (minted 2026-08-05, 003c's re-stage).** Refill as
drafted above is per-parameter: a miss refills only the *requested* parameters, so a cold-store
mixed request (direct parameters through the Provider; `wind_u`/`wind_v` through the Calculator's
scoped Arbiter) still issues **two vendor fetches with disjoint variable sets** — the divergence
exposure [003c](./done/01-0110-request-shaping.md) accepted survives on that path. The alternative: a
miss refills the source's **whole offering** — one vendor call returns all its variables anyway, so
the first fetch would populate `wind_u`/`wind_v` and the second would hit the store even
stone-cold. Decide which, and record the traffic/behaviour trade. At the same align, **verify the
partial-warm edge**: one parameter fresh, another refetched, full-horizon bounds — the
window-extension-refetches-whole rule appears to prevent a retained window and a fresh one serving
two different T ranges, but "retention dissolves the divergence" leans on that and it has never
been checked.

**Open-ended request member — decide at this ticket's align (minted 2026-08-07, 0112 landing).**
One-sided open bounds ("no bounds — whatever is available") designed together with `ANY` / the
whole-axis form: the MCP edge's omitted-`end` flip and the floor-narration sentence become
narration's own question again here, with retention landing in the same ticket. Reserved vocabulary
is 006's `ANY` (the deferred m4 form); do not mint the open-ended member alone.

**This ticket is a trigger for [#42](../concerns.md#42-two-request-representations-so-resolution-cannot-be-a-method).**
Refill requests are the second in-tree author of *exact* requests, which is what makes the request
side's two representations load-bearing rather than incidental — and the reason `ground` is a function
taking the request rather than a method on it. 003c recorded its half of the call on 2026-08-05 —
**the split stays and the edge authors `SelectionDomain`** — so the decision left here is whether
refill keeps building enumerable shapes (the split stays for good) or refill's arrival is the moment
the request side narrows to one representation and refill is written against that. Also re-read
[#22](../concerns.md#22-lattice-helpers-vs-domain--sampling-module-split) — `quantize` is the third
lattice-arithmetic site, which is that carve's trigger.

The e2e's second-call **re-fetch assertion** (documenting no-retention, session 0010) flips here.

## Acceptance criteria

- [ ] The retentive in-memory `Store` is wired into both positions (Source + best view) with its
      private per-axis lattices (identity on Z; unit keys carry the Z cell).
- [ ] `quantize` asks **`ANY`** on the axes the unit spans wholly (v1 timeline store: `T` and `Z`),
      and the Provider answers **multi-domain** — units land keyed by **native** Z (2 m, 10 m,
      surface, `[0,TOA]`), not by the request's Z, from a **single** vendor fetch.
- [ ] `assimilate` consumes the answer and slices it per parameter inside the store; no other node
      constructs a unit `Selection` or otherwise learns the store's lattice.
- [ ] `open_meteo.project` no longer flattens eagerly; a request whose Z differs from a prior one
      **reuses** the stored native units rather than refetching.
- [ ] A fully-fresh repeat request is served with **no** provider call.
- [ ] A fresh parameter is reused while another (stale) parameter is refetched (per-parameter, TTL =
      `expiration`).
- [ ] A temporal miss or window-extension refetches the **whole** window single-origin (no `valid_time`
      splice).
- [ ] The retention interval is configurable and only bounds memory (never serves stale).
- [ ] Unit + mocked-transport integration tests cover fresh-serve, per-parameter partial refill, and
      whole-window single-origin refetch.

## User stories addressed

- User story 5
- User story 14
- User story 15
