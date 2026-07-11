## Parent PRD

`docs/v1-requirements.md`

## What to build

Replace the stub `Store` with the real **retentive in-memory `Store`** — a
`Writable`, `Countable` Manifold that declares its grid `Domain` (hourly + spatial) and is wired into
**both** positions (each `Source` and the best view). `project` runs the `Reservoir` pipeline:
`quantize` the request onto the store grid (snap + widen to whole assimilable units — a parameter's
timeline at a spatial cell), read the per-unit **{held, fresh, origin}** report, serve units that are
**fresh and single-origin**, and **refill the missing/stale units whole** from the child
(`child.project(store_shape)`), then `assimilate` (replacing whole units atomically).

Freshness is read straight off each `ParameterData`'s `expiration` (`fresh ⇔ expiration > now`). Refill
is **per-parameter and spatial** — a fresh parameter is reused while a stale one is refetched, each
parameter resolved independently; a parameter's `valid_time` window stays **single-origin** (temporal
miss or extension refetches the whole window). A separate **configurable retention interval** bounds
memory (housekeeping only; the `Arbiter` never serves stale entries — LRU declined). See
`docs/v1-requirements.md` (v1 invariants, Config & secrets) and `docs/architecture.md` (Reservoir,
Store).

**Decision to resolve in this issue:** the store-grid representation. A declared grid is the
anchored-regular member with **open extent** (`anchor + step`; ADR-0002), but `RegularAxis` fixes all
three of `(anchor, step, count)` — the exact-extent member. Mint the declared-grid representation
(e.g. an extent derived from the retention window, clock-anchored — the `RollingAxis` precedent), or
narrow what `quantize` actually requires (anchor + step, not enumeration). Until then the skeleton's
`StubStore.domain` raises `NotImplementedError` (a retention-free store declares no lattice).

## Acceptance criteria

- [ ] The retentive in-memory `Store` is wired into both positions (Source + best view) and declares its
      grid `Domain`.
- [ ] A fully-fresh repeat request is served with **no** provider call.
- [ ] A fresh parameter is reused while another (stale) parameter is refetched (per-parameter, TTL =
      `expiration`).
- [ ] A temporal miss or window-extension refetches the **whole** window single-origin (no `valid_time`
      splice).
- [ ] The retention interval is configurable and only bounds memory (never serves stale).
- [ ] Unit + mocked-transport integration tests cover fresh-serve, per-parameter partial refill, and
      whole-window single-origin refetch.

## Blocked by

- Blocked by `issues/20260623_v1/002-core-5-parameters.md`

## User stories addressed

- User story 5
- User story 14
- User story 15
