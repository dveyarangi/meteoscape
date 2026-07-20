# 006 — Retentive store and freshness

- **Status:** Planned
- **Depends on:** [002 — Core canonical parameters](./done/002-core-5-parameters.md)
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
which is why it must be the **ask** that changes. `_assemble` remains as the multi-domain answer's own
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

**Decision to resolve in this ticket:** the store-lattice representation. A declared lattice is the
anchored-regular member with **open extent** (`anchor + step`; ADR-0002), but `RegularAxis` fixes all
three of `(anchor, step, count)` — the exact-extent member. Mint the declared-lattice representation
(e.g. an extent derived from the retention window, clock-anchored — the `RollingAxis` precedent), or
narrow what `quantize` actually requires (anchor + step, not enumeration). Being private
([ADR-0006](../adr/0006-materialization-granularity-and-store-shape.md)), the representation is the
`Store`'s own business. The e2e's second-call **re-fetch assertion** (documenting no-retention,
session 0010) flips here.

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
