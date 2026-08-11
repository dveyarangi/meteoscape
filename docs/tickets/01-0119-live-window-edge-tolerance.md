# Live-window edge tolerance

- **Status:** Ready
- **Plan:** [live-window edge tolerance RFC](../rfc/01-0119-live-window-edge-tolerance.md) — the declared axis answers
  retention for itself (`satisfied_by`): overlap for a clock-anchored window, containment for a static
  one.
- **Depends on:** [Reservoir retention pipeline](./done/01-0115.0040-reservoir-retention-pipeline.md)
  (the refill gate and read-back seams this ticket changes),
  [off-grid homogenization](./done/01-0117-off-grid-homogenization.md) (the read-back guards it must
  not weaken)
- **Blocks:** [TWC provider](./01-0120-twc-provider.md) — see
  [Why this blocks TWC](#why-this-blocks-twc)
- **Outcome:** A leaf whose declared live window reaches past the series its vendor actually delivers
  serves the overlap and refills once, instead of refetching on every request and faulting on the
  gap. The tolerance rides the existing Clip channel; static T axes stay exact.

## The premise

A forecast leaf declares its availability window from a `CadenceDef` — `[W, W + max_lead]`, where
`W = floor(now, shelf)` ([ADR-0003](../adr/0003-provenance-and-origin.md#run-identity-fetch-buckets-and-freshness--the-cadence)).
That declaration is an **estimate of what the vendor will serve**, computed before any fetch. The
vendor's delivered series is the **truth**, known only after one.

Until now the two happened to agree: Open-Meteo declares a daily Shelf and genuinely delivers
from the day boundary, so the estimate has never been wrong in the shipped tree. The declaration was
therefore treated as exact everywhere it meets holdings — which is the bug this ticket removes.

**The rule this establishes:** the **declared axis answers retention for itself**. A clock-anchored
window is satisfied by *overlap*; a static axis by *containment*. Neither the request nor the Holdings
can tell those apart, so the declaration must
([ADR-0002](../adr/0002-data-model.md#the-two-predicates-admission-and-retention)).

## What goes wrong today

Two independent defects, both on TWC's default path, neither visible on Open-Meteo.

**Defect 1 — the gate is unsatisfiable.** TWC's series begins at the **next** whole hour while a `1h`
quantum floors to the current one, so `now` itself always sits in the gap:

```
              11:00        11:42 (now)     12:00
declared       ├────────────────────────────────────────►   floor(now, 1h)
delivered                                 ├─────────────►   the vendor's first tick
               └────────── the gap ───────┘                 always contains `now`
```

`_required_coverage` intersects the request with the **declared** reach
([reservoir.py:113](../../src/meteoscape/nodes/reservoir.py)); `_missing` then asks whether the
**held** extent contains that ([:135](../../src/meteoscape/nodes/reservoir.py)). A default MCP
request's lower bound is `clock.now()` verbatim
([mcp_app.py:146](../../src/meteoscape/api/mcp_app.py)), which lies in the gap, so containment can
**never** hold: **every request costs one metered vendor call** and retention never serves a warm hit.

**Defect 2 — the quantum outranks the cadence.** Reach and expiry are both pure functions of the
clock, so the coverage test and the freshness test ask the same question at different granularities —
and the finer wins. Once the clock crosses an hour boundary the declared reach advances while the
Holding does not, so the gate refetches **hourly** whatever `cadence` says. This is independent of
defect 1 and survives any correction to the declaration, since a correctly-declared window advances
hourly too.

**Not a defect:** a request that *straddles* the gap already serves. `ground` asks the record's own
axis to clip itself ([domain.py:653](../../src/meteoscape/manifold/domain.py)) and a `SnappedAxis`
carries bounds only, so there is no request-side lattice demanding an exact match. Only a request
lying **wholly** inside the gap fails, as
`RuntimeFailure("Holdings cannot ground onto an admitted request")` — where a clean capability answer
belonged.

## Why this blocks TWC

TWC's `cadence` is a **polling policy against a monthly allotment**, and both defects make the true
call rate ignore it — defect 1 by a factor of every-request, defect 2 by a factor of twelve. Shipping
a metered primary behind a cache that cannot hit is the thing this ordering exists to prevent.

## What to build

The predicate pair on `Axis`, per
[ADR-0002](../adr/0002-data-model.md#the-two-predicates-admission-and-retention) — a containment
default, overridden by `RollingAxis` to overlap — and a `Reservoir` that asks it instead of comparing
extents itself.

- **Overlap, not "drop the check".** Dropping it entirely serves nothing once a Holding falls behind
  `now`, and never fills an archive's wider ask. Overlap keeps both safe.
- **Static sources inherit correctness.** The coming
  [archive](./02-0134-forecast-run-archive-source.md) and [obs](./02-0130-mongo-obs-source.md) sources
  hold *slices of a larger corpus*, where a wider ask genuinely needs more data. They get the exact
  default by type, not by being remembered.
- **T-only falls out, rather than being enforced.** `RollingAxis` is temporal-by-type, so no
  hand-written axis filter is needed; the spatial enclosing-cell guard from
  [007](./done/01-0117-off-grid-homogenization.md) stays fatal and untouched.
- **`cadence ≤ max_lead`.** A rolling Holding is refreshed only on expiry, so a longer cadence lets the
  held window fall entirely behind `now`. TWC's `hourly_6hour` (`max_lead = 5h`) against a 12 h default
  is exactly that trap → validated in its `build`.
- **No new axis flag and no interval-handling in the Reservoir.** The predicate takes axes and reads
  `.extent` internally, exactly as `matches` does.

## Acceptance criteria

- [ ] **A default request against a leaf whose series starts after the declared window opens refills
      at most once**, then serves warm — pinned by counting transport calls across two requests, not
      by inspecting the gate.
- [ ] A request straddling the gap serves the overlap, and the response's first tick is the vendor's
      first delivered tick.
- [ ] **The declared cadence, not the Shelf, governs refetch** (defect 2): advancing the
      clock past a shelf boundary but not past expiry makes **no** vendor call; advancing past expiry
      does. This is the criterion that keeps `cadence` meaningful, so it is pinned on its own.
- [x] **`CadenceDef.window_quantum` renamed `shelf`** per the [glossary](../glossary.md) — the field
      names the vendor's serving calendar, not a property of the window. **Landed 2026-08-11**, ahead of
      this ticket so TWC would not ship on the old name; behaviour-neutral, suite and `pyright` green.
- [ ] A request straddling the gap serves the overlap, and the response's first tick is the vendor's
      first delivered tick.
- [ ] A request lying wholly inside the gap produces a **clean capability answer, not a
      `RuntimeFailure`** — and against a warm store costs **no** vendor call, however many times it is
      asked. (A cold store still pays one first-touch fetch, which is retained and answers later asks.)
- [ ] A leaf whose T reach is a **static** axis keeps exact containment — pinned by a test, so the
      rolling behaviour cannot silently generalize to the archive and obs sources.
- [ ] A rolling Holding that has fallen **entirely behind `now`** still refetches — the case that
      makes overlap safe rather than permissive.
- [ ] A provider declaring `cadence > max_lead` fails when its `CadenceDef` is constructed, not at
      serve time — enforced centrally, since [011](./01-0120-twc-provider.md) lands after this ticket
      and its `hourly_6hour` offering (`max_lead = 5h`, 12 h default cadence) is exactly the trap.
- [ ] The spatial enclosing-cell guard is unchanged; 007's tests pass untouched.
- [ ] Open-Meteo's behaviour is unchanged — its declaration matches delivery and its quantum equals its
      cadence, so this ticket must be a no-op for it, pinned by the existing e2e re-fetch assertions.

## What this ticket does not decide

Both selected by the [live-window edge tolerance RFC](../rfc/01-0119-live-window-edge-tolerance.md):

- ~~**The repair shape at site 1.** Whether the gate relaxes containment to overlap, compares against
  the delivered extent, or drops the T-coverage test for boundless refills entirely.~~ **Selected: the
  declared axis answers for itself — `RollingAxis` by overlap, static by containment**
  ([ADR-0002](../adr/0002-data-model.md#the-two-predicates-admission-and-retention)). Dropping the
  test entirely fails an archive source, whose Holding is a *slice of a larger corpus*; keeping
  containment everywhere makes the Shelf outrank the declared cadence. Neither the request
  nor the Holdings can tell those apart, so the declaration must.
- ~~**What a wholly-in-gap request returns.**~~ **Selected: `CapabilityMismatch`** — substantively
  true, and it is what lets the Arbiter reach the backstop once
  [fall-through](./01-0121-second-provider-fallback.md) lands, where a `RuntimeFailure` would fail the
  whole request.
- Whether any of this narrows [#21](../concerns.md#21-serves-extent-vs-project-crop-ability), whose
  family this belongs to: admitted-by-extent then unserved. #21's own case is off-phase/different-step
  and stays open regardless.

## Parent PRD

`docs/v1-requirements.md`
