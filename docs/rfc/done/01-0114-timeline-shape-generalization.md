# One timeline algebra, two geometries — implementation plan

**Authored:** 2026-08-22
**Last amended:** 2026-08-22 (fourth validation pass)

Implements [one timeline algebra, two geometries](../../tickets/done/01-0114-timeline-shape-generalization.md):
`TimelineProvider` becomes the base of a wrapper family, with the rolling behaviour moved into
`RollingTimeline`. Pure refactor — no behaviour changes.

## Scope and boundaries touched

| Boundary | Owner | Change |
|---|---|---|
| Shape wrapper family | [architecture § Provider](../../architecture.md#provider-leaf-manifold), [edge/provider.md](../../edge/provider.md) | `TimelineProvider` becomes a base; four answers become its extension points |
| `open_meteo.py`, `twc.py` build faces | [ADR-0005](../../adr/0005-build-time-composition.md) | construct `RollingTimeline`; arguments unchanged |

**Not touched:** the `Probe` seam, `TapTable` / `interpret` / `decode`, `Provider` (the ABC),
`Capability`, every `Domain`, the binder, the Reservoir, and both vendors' declarations. No
`Selection` reaches a different code path than it does today.

## Why the base is a class and the members are subclasses

Settled at the 0114 align (2026-08-22) after measuring the alternative: the four answers are not
independently useful objects — nothing else would construct or consume one, and such an object would
need the same `taps` / `step` / `clock` the member already holds, duplicating every construction
argument. `Provider` → `TimelineProvider` is already an inheritance chain
([architecture § Provider](../../architecture.md#provider-leaf-manifold)), so a family member is what
"adds a wrapper" already meant for a geometry of a known delivery shape.

## Shapes

### The base — `nodes/providers/timeline.py`

`TimelineProvider` keeps `project`, `_interpret`, `_lattice_of`, `_answered_geometry`, `_delivered`,
`_point_of`, `_window_of`, and `source_key` **unchanged in body**, and adds **three** extension
points — not four:

```python
class TimelineProvider(Provider, ABC):
    # constructed with what the algebra itself needs: probe, taps, step, parameters, source_key
    # (no cadence, no clock, no spatial reach — those are one member's facts)

    @abstractmethod
    def resolve(self, request: Domain, parameters: Sequence[ParameterId]) -> GridDomain:
        """The geometry this producer answers `request` with — its own `ground` call(s).
        `parameters` arrives deduped in declaration order; see the ordering note below."""

    @abstractmethod
    def stamp(self, wanted: GridDomain) -> Provenance:
        """The origin plane for one fetch, given the geometry resolved for it."""

    async def refresh(self) -> None:
        """Bring fetched facts up to date. Fixed-facts members inherit this no-op."""
```

**The fourth answer needs no new member: `capability` is already abstract on `Provider`**
(`nodes/providers/base.py`), so the base simply stops implementing it and each member does. This is
also the *correct* home rather than a convenience — a member whose facts are fetched must be able to
publish a capability that changes after a refresh, and must publish `declared_origins` alongside its
reaches ([ADR-0003](../../adr/0003-provenance-and-origin.md)); a base that froze
`GranularCapability(reaches=...)` at construction, as today's code does, could do neither. The base
never reads `self.capability` on the request path, so nothing else moves.

Two shaping choices, both load-bearing:

- **`resolve` takes the engaged parameter ids, not the `TapTable`.** Today's `_resolve` reads only
  `tap.produces` (timeline.py:141-156), and the same question must stay askable by a member whose
  delivery is not a point series — the property
  [architecture § Provider](../../architecture.md#provider-leaf-manifold) now states. **They must
  arrive ordered and deduped, in declaration order** — derived from the tap tuple, *not* from
  `TapTable.parameters`, which is a `frozenset`. The reason is not stylistic: `agreed_geometry`
  returns `members[0]` (domain.py:856), and on an axis the request leaves open, resolutions may
  legitimately differ — Z does, since each tap declares its own level. Feeding a set would make the
  returned geometry's Z depend on iteration order. Nothing reads that Z today (`_point_of` reads
  X/Y, `_window_of` reads T), so this is a latent hazard rather than a live bug — which is exactly
  why the plan should not introduce it. Deduping is safe on its own terms: `_declare_footprints`
  already keys footprints by `tap.produces` (timeline.py:314), so two taps producing one parameter
  ground the same footprint twice today and fold to the same answer.
- **`stamp` takes the resolved geometry.** `RollingTimeline` ignores it and reads its cadence; a
  scatter member reads the place off X/Y to name which station produced the values. One signature,
  no member-specific argument. **`project` calls `stamp` after `retrieve`**, matching today's
  interpret-time clock read — stamping first would move `fetched_at` / `expiration` by retrieve
  latency. Frozen test clocks hide that; the "no behaviour change" criterion does not.

`refresh` is concrete-and-empty rather than abstract: a fixed-facts member should declare nothing to
inherit nothing, and `project` awaits it once before resolving.

### `RollingTimeline` — same module

The live member. Holds today's rolling facts verbatim — `cadence: CadenceDef`, `clock`,
`longitudes` / `latitudes` — and implements the answers with today's code moved unchanged:
`_declare_footprints(...)` plus the frozen `GranularCapability` become its `capability`, today's
`_resolve` body its `resolve`, today's `_stamp` body its `stamp`. It inherits the no-op `refresh`.
`clock` lives here, not on the base: after the split the algebra never reads it (`stamp` and
footprint declaration both moved). Cadence, archive window, and refresh interval each belong to a
member.

Its constructor takes exactly what `TimelineProvider(...)` takes today, so both build faces change
only the class name they call.

### Naming

The base keeps `TimelineProvider` — the docs already describe it as "the point-plus-hourly-series
family", which is what a base is. **The live member is `RollingTimeline`** (settled 2026-08-22): it
names the *geometry*, not the product — a continuous footprint whose window rides the clock, the
same fact `RollingAxis` already names. The collector's archived vendor runs sit in **per-point
collections at the station coordinates** (measured 2026-08-21) — scatter geometry on an archive
window, differing from an observation member in its **stamp alone**. A name reading "forecast"
would stop being true the moment those runs exist. Whether they become a thin subclass overriding
`stamp` or a construction fact of the scatter member is
[0134](../../tickets/01-0134-forecast-run-archive-source.md)'s align, not this plan's.

## Flow (unchanged, with the seam marked)

```
capability.serves(...)                  ← member, SYNC — admission, before project (arbiter.py:217)
project(selection)
  ├─ parameter guards, open_axes        ← base, unchanged
  ├─ await refresh()                    ← member; no-op for fixed facts
  ├─ wanted = resolve(domain, engaged)  ← member; reads what refresh just settled
  ├─ probe.retrieve(...)                ← base, unchanged
  ├─ provenance = Uniform(stamp(wanted)) ← after retrieve, matching today's interpret-time clock read
  ├─ _interpret(..., provenance)        ← base; `_interpret` has no `wanted` today
  └─ _answered_geometry / _delivered    ← base, unchanged
```

**Refresh sits after the parameter guards and before `resolve`** — a request naming unserved
parameters must not buy a refresh, and `resolve` must read what a refresh settled. The tap table is
static for every member (it is the canonical mapping, not a fetched fact), so no guard depends on
refreshed state.

## Stages (each ends green)

1. **Extract the extension points.** Rename `_resolve`/`_stamp` to the declared members, change
   `_resolve`'s parameter from `TapTable` to the engaged ids, thread the provenance from `project`
   into `_interpret`, and add the empty `refresh` with its `await`. `TimelineProvider` stays
   concrete and instantiable, so **every existing test passes untouched** — rearrangement inside one
   class, not yet a family. (Verified: no test references `_resolve`, `_stamp`, `_footprints`, or
   `_interpret` on the provider — measured across `tests/`.)
2. **Split base and `RollingTimeline`.** Move `cadence`, `clock`, `longitudes`/`latitudes`,
   `_declare_footprints`, the frozen `capability`, and the answer bodies into the member; make the
   base abstract and drop its `capability` implementation. The four construction sites
   (open_meteo.py:242, twc.py:258, and the two test helpers) change class name only. Both vendors' behaviour is pinned by their existing deterministic suites and by the
   opt-in parity harness.
3. **Guard the family contract.** A test asserting that each member's own attributes overlap the
   base's only in the permitted set — the three extension points, `capability`, and `__init__` —
   so a member re-implementing `_interpret` or `_delivered` fails. Stated as an intersection over
   `__dict__`s rather than a whitelist of all member names, ignoring the language's own dunders
   (`__module__`, `__doc__`, …), since members legitimately carry private helpers the base has
   never heard of. This is the "one home for the algebra" criterion, machine-checked rather than
   reviewed. A fake member whose **`capability` reach is a `ScatterDomain`** grounds a bounded-T
   (`SnappedAxis` on T, not an exact `GridDomain`) request by matching the place and calling
   `ground` against that place's separable stand-in — the pattern
   [station observation serving](../../tickets/01-0124.0030-station-observation-serving.md) will copy.
   An exact request would not prove the extension point: `ground` returns an `EnumerableDomain`
   by identity and never reads the answering geometry, so today's footprint path would succeed
   against a scatter. A fake that merely returned a `GridDomain` would not fail a copied rolling
   `resolve`, which `ground` refuses against non-separable geometry. A fixed-facts member's
   `refresh` issues **zero transport calls**, pinned by counting them on the recording transport
   the vendor suites already use — not by asserting the method body is empty.

Stage 1 is safe alone; stage 2 is the only one that moves code between classes; stage 3 adds no
production code. No stage leaves tests red.

## Verification against the ticket's criteria

Criterion 1 (vendors unchanged) → stages 1–2, existing suites plus parity. Criterion 2 (one home,
machine-checked) → stage 3. Criterion 3 (non-separable member grounds a bounded-T request) → stage 3's
fake member. Criterion 4 (refresh is free for fixed facts) → stage 3's call count.

## What `refresh` on the request path can and cannot reach

Admission is **sync and precedes projection**: the Arbiter asks `capability.serves(...)`
(arbiter.py:217) and only projects a candidate that answers yes (arbiter.py:187). So a refresh
awaited inside `project` **cannot rescue the request that needed it** — a request at a place the
current snapshot does not know is declined at admission, and `project` is never entered.

What it does reach: every *later* request. A projection at an already-known place refreshes the
snapshot, and a newly added place is admissible from then on. So "a station added to the collector
becomes servable without a restart" holds via ordinary traffic to known places — which the
correction workstream generates — but a source that is idle, or whose every request names an
unknown place, never advances. This is the honest bound on the align's serving-path re-read
decision, and it is 0124.0030's to live with; recorded here because this plan is where the `await`
is placed. Making admission itself trigger a refresh would require I/O inside a sync predicate,
which the `Capability` contract does not allow.

## Limitations and follow-ups

- **The fake member in stage 3 is the only non-separable geometry until 0124.0030.** That is
  deliberate — the same shape as the [scatter substrate](../../tickets/done/01-0124.0010-scatter-substrate.md)'s
  fake-tested contracts — but it means the extension point's *first real* exercise is that ticket.
- **`ArchiveAxis`, `ScatterDomain` reaches, and station stamping are not here** →
  [station observation serving](../../tickets/01-0124.0030-station-observation-serving.md).
- **A gridded or swath delivery still needs its own wrapper**, not a member of this family
  ([edge/provider.md](../../edge/provider.md) follow-ups); what this ticket buys such a wrapper is the
  precedent for how its own members would divide, not code.
