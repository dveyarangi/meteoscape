# 003a — `Capability.reach`

- **Status:** Ready
- **Depends on:** [002 — Core canonical parameters](./done/002-core-5-parameters.md),
  [002b — Derived wind](./done/002b-derived-wind-calculator.md)
- **Outcome:** A `Capability` can report the `Domain` it reaches, folded per axis by the composite
  algebra — the fact every surface needs to narrate an envelope or author a default window.

## Parent PRD

`docs/v1-requirements.md`

## What to build

Algebra-level only — **no surface change**. [003b](./003b-request-shaping.md) is the consumer.

`Capability` gains a per-parameter **`reach` `Domain`** alongside `serves`
([ADR-0004](../adr/0004-producer-resolution-and-capability.md), amended session 0013). It folds by the
same leaf/composite algebra as `serves`: leaf → its footprint; **derived → per-axis intersection** (a
Calculator needs *all* its inputs); reservoir → forwards its child's.

**A composite joins per axis, and the rule follows the request's own shape there.** Admission is
whole-request containment, and a request is a **point** on X/Y/Z but an **interval** on `valid_time`:

- **point axes → union** ("could anything serve here?"). An **outer bound**: folding drops inter-axis
  correlation, so `{Europe × 16 d, Americas × 10 d}` yields a span crossing the Atlantic. Read as
  *nothing outside is servable, not everything inside is*; a point inside it that no member serves
  fails at admission as an ordinary `capability-mismatch`. (Intersection would be empty for disjoint
  footprints, and useless.)
- **extent axes → intersection** ("is this whole span servable?" — one member must contain it all). A
  **guarantee**: the folded window is servable wherever the composite serves at all, which is what
  lets 003b author a default window from it.

So reach is **mixed by design** — spatially an outer bound, temporally a guarantee — and in both cases
**advisory**: `serves` remains the sole admission authority and **no admission path may consult
`reach`**. That discipline is the whole point; violating it silently over-serves through the spatial
bounding box.

**The T fold is conservative, deliberately.** Where a member is spatially universal it under-promises
— OM global × 16 d plus TWC × 10 d yields 10 d though OM serves 16 d everywhere. **Accepted, not
solved**: a surface promising 10 days of fully-served coverage makes a *correct* product statement,
callers can still request more explicitly and be admitted, and a longer product is another surface. If
it ever needs addressing, the lever is a config declaration — marking a provider explicitly
**fallback** so it is excluded from the reach promise — not location-aware machinery
([#29](../concerns.md#29-narrated-reach-per-axis-join-conservative-on-extent-axes)).

**This resolves a dangling contract claim.** ADR-0004 stated that an introspection envelope
"aggregates from **leaf reach**", but leaf footprints are private to `serves`, so no accessor existed
and the aggregation had no path. The amendment states the reach contract and its discipline directly
rather than enforcing it by omission.

### Supporting geometry

Per-axis `Interval` **union** and **intersection** must exist —
[`domain.py`](../../src/meteoscape/manifold/domain.py) currently lists `intersect` as a *declared
seam*, not built. This is geometry-core work, not an edge change, and it touches three standing
concerns:

- **[#22](../concerns.md#22-lattice-helpers-vs-domain--sampling-module-split)** — adding interval
  algebra to `domain.py` is exactly the growth that concern says to watch for. Decide during this
  ticket whether it stays or a thin `lattice.py` gets carved; do not split preemptively.
- **[#23](../concerns.md#23-spatial-vs-temporal-regularaxis-types)** — interval ops hit the same
  `float` vs `timedelta` dispatch `sub_lattice_offset` already crawls with `isinstance`. Building more
  of it either compounds the problem or earns the type split.
- **[#12](../concerns.md#12-curvilinear-domains)** — `intersect` is a declared seam there; this
  builds the enumerable/continuous case only.

A later consumer is already recorded: when admission generalizes from containment to **intersection**
([#13](../concerns.md#13-candidate-admission-containment-vs-intersection)), it needs these same
primitives.

## Acceptance criteria

- [ ] Per-axis `Interval` union and intersection exist and are property-tested over both coordinate
      kinds (spatial `float`, temporal `datetime`/`timedelta`), including empty and touching cases.
- [ ] `Capability` exposes a per-parameter `reach` `Domain`, implemented on `FootprintCapability`,
      `EnumerableCapability`, `UnionCapability`, and `DerivedCapability`, and forwarded by the
      `Reservoir`.
- [ ] A composite joins per axis: **point axes (X/Y/Z) union**, **extent axes (`valid_time`)
      intersect**. `DerivedCapability` intersects its inputs on every axis.
- [ ] Given `{Europe × 16 d, Americas × 10 d}` for one parameter, the union's reach spans both
      footprints spatially and reports **10 d** temporally.
- [ ] `reach` is consulted by **no** admission path; `serves` behaviour is unchanged by this ticket.
- [ ] Unit tests only — no surface or provider changes.

## User stories addressed

Enables user story 10 (envelope narration), delivered by
[003b](./003b-request-shaping.md).
