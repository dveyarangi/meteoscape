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
parameter's timeline at a spatial cell; identity on axes without a lattice, v1: Z — the cell joins
the unit key), read the per-unit **{held, fresh, origin}** report (held cells matched with the same
cell arithmetic as `serves`), serve units that are **fresh and single-origin**, and **refill the
missing/stale units whole** from the child (`child.project(store_shape)`), then `assimilate`
(replacing whole units atomically). The Source's read-back relabels matched native cells onto the
handed shape (the fact→product boundary).

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
