# Persisting SQLite Store

- **Status:** Planned (own align precedes) — minted at the 2026-08-10 beeline align.
- **Depends on:** [006 — Retentive store](./done/01-0115-retentive-store-freshness.md) (the
  Holding-granular contract this implements a second time)
- **Outcome:** Retained Holdings survive process restart and are shared across concurrent processes
  on one deployment — a second `Store` substrate behind the existing face, with no contract change.

## Parent

The release-01 bee-line requires every cache position to survive restart and redeploy
([delivery status](./README.md)); this supersedes the predecessor
[v1 requirements](../v1-requirements.md)' in-memory-only position. The durable design context is
[ADR-0006](../adr/0006-materialization-granularity-and-store-shape.md) and
[architecture § Store](../architecture.md#store--one-type-several-positions).

## The substrate ladder

The 2026-08-10 align named three rungs. They are **substrates**, not a new axis — ADR-0006 and the
architecture already say "implementations vary by substrate, persistence, and lattice structure
behind one write/read face":

| Rung | Substrate | For | Owner |
|---|---|---|---|
| 1 | `MemoryStore`, low retention | MCP stdio fast-use — process-lifetime, dies with the session, and *should* | delivered at [006](./done/01-0115-retentive-store-freshness.md) |
| 2 | `SQLiteStore` | regular deployment — survives restart and redeploy, shared across processes | **this ticket** |
| 3 | bulk / columnar | long-running research jobs — analytical scans, not point lookups | [#44](../concerns.md#44-dedicated-live-archive-store-for-throughput) |

Rung 3 is not a bigger rung 2: it is a different read shape. It stays with #44.

## Why this does not overturn "we don't own persistence"

[#44](../concerns.md#44-dedicated-live-archive-store-for-throughput) records the earlier stance that
meteoscape owns no historical persistence — "the framework doesn't own persistence, it projects
over whatever does". That stance is about **history**, and it survives intact:

- A **retention cache is derivable state.** Every Holding in it can be re-fetched from the vendor.
  Losing it costs money and latency, never information.
- An **archive is source-of-truth state.** Once a run's window passes, nothing reconstructs it —
  which is exactly why the archive stays the operator's collector.

Persisting a cache is therefore a substrate choice inside a contract that already permits it, not a
claim on anyone's data. #44 is **narrowed** to rung 3, not overturned.

Two facts make the mechanism cheap: the `Store` contract is **clockless and freshness-blind**, so a
Holding that comes back stale after a restart is just a stale Holding and the `Reservoir`'s existing
gate refills it — **persistence adds no freshness rule**. And the payload is plain data: a
`GridDomain`, a `ParameterData` (float sequence + optional bool mask), a `ParameterDef`, a
`Provenance`.

## The key must become self-describing

This is the one real design constraint the align surfaced, and it is a **correctness** matter, not a
tuning one:

```
_HoldingKey = (ParameterId, x_index, y_index, EnumerableAxis)
                            └───┬───┘         └──────┬──────┘
                     INDICES into a lattice     a VALUE OBJECT
                     derived from               carrying its own
                     StoreSpec.spatial_step     meaning ("[0,10] m")
```

`x_index=5` means "the 6th cell of a 0.0001° global lattice". Change `store_spatial_step` and index
5 names **a different place on Earth** — but the key still matches. In memory this is impossible
(fresh process, fresh lattice, fresh rows). Persisted, it is a silent wrong answer at a wrong
coordinate.

Note the asymmetry inside one key: the Z component is a value object and means the same thing
forever; X and Y are indices into state held elsewhere. So either the key becomes self-describing
(quantized coordinate rather than index — probably a scaled integer rather than a float, to keep
equality exact across serialization) or rows carry the lattice parameters they were keyed under and
a mismatch **orphans rather than serves**. This ticket's align picks one.

The aperture, by contrast, needs no such treatment: `Z` is already in the key and matches by
equality, so a changed aperture produces misses that fall through to the Sources and re-match
natively — [#25](../concerns.md#25-root-store-holding-reuse-across-vantage-windows)'s "exact-key
only… correct, just colder" arm. Dead rows are swept by `retention_interval`.

## Decisions this ticket's align owns

- ~~**The substrate.** Deliberately not chosen here.~~ **SQLite is the v1 persistent Store
  substrate:** it needs no daemon and gives the embedded library a durable out-of-box path. Its
  implementation must not conflate the two clocks: retention eviction is `retention_interval`,
  freshness is `expiration`, and Holdings are deliberately kept past expiry.
- **The key shape**, per the section above.
- **Store selection and embedding attachment.** `StoreFactory.create(spec, deferred)` is the single
  allocation site and currently hardcodes `MemoryStore`; that is enough while only one Store
  implementation exists. This second implementation is the trigger to decide both how an embedding
  host selects among shipped Store implementations and whether it may supply its own implementation.
  Shipped implementations must not require the host to declare or register them. No configuration,
  factory, registry, or public extension shape is selected ahead of this ticket's align; split that
  decision into a child ticket if it needs its own implementation slice. Provider/calculator plugin
  scaffolding does not answer it ([#26](../concerns.md#26-provider--calculator-plugin-scaffolding)).

## Acceptance criteria

- [ ] Retained Holdings survive a process restart: a request served from vendor data before the
      restart is served from Holdings after it, with no vendor call.
- [ ] Concurrent processes against one deployment share retention — a second process reads the
      first's Holdings.
- [ ] **Both store positions persist** — the best-view root and the per-Source stores (decided at
      the 2026-08-10 align).
- [ ] A lattice change (different `spatial_step`) can never serve a stale row for the wrong
      coordinate: rows either carry their lattice or key by coordinate, and a mismatch orphans.
- [ ] Freshness is unchanged: a Holding restored past its `expiration` is refilled exactly as an
      in-memory stale Holding is. No new freshness rule appears anywhere.
- [ ] The `Store` contract is untouched — the persisting substrate implements the same face, with
      no carve-out, and `MemoryStore` remains available and default for rung-1 use.

## Parent scope addressed

- Roadmap Phase 2 (operational substrate): retention tuning and store observability under operator
  control.
