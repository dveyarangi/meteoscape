# Live-window edge tolerance — implementation plan

**Authored:** 2026-08-11

Implementation plan for [live-window edge tolerance](../tickets/01-0119-live-window-edge-tolerance.md).

**Scope in one line:** the declared axis answers retention for itself — a clock-anchored window
satisfied once its horizon reaches the ask's start, a static one by containment — and the `Reservoir`
asks instead of comparing extents.

**What this is really testing:** whether the rule can live where the knowledge is. If a consumer still
has to branch on axis kind afterwards, the predicate is in the wrong place; record that rather than
working around it.

## What the durable docs now say (landed 2026-08-11, before this RFC)

This RFC describes no architecture the docs do not carry:

1. **[ADR-0002 § The two predicates](../adr/0002-data-model.md#the-two-predicates-admission-and-retention)** — admission dispatches on the **request**, retention on the **declaration**, and the dispatch sides must differ: a rolling producer's Holdings materialize as an ordinary lattice, indistinguishable from an archive slice, and the request arrives snapped in both cases. Rolling is satisfied **once its horizon reaches the ask's start** (explicitly *not* mere overlap), static by **containment**, and the cadence-must-not-exceed-`max_lead` corollary is stated there.
2. **[ADR-0003 § availability window](../adr/0003-provenance-and-origin.md#run-identity-fetch-buckets-and-freshness--the-cadence)** — `W` is a **phase declaration**: it anchors the materialized lattice, so it must sit on a shelf boundary. *Which* boundary is separate; flooring is the shipped choice, and the leading-edge over-declaration it causes is absorbed by retention.
3. **[architecture.md](../architecture.md)** — both Reservoir passages now name the predicate. They previously read "missing or **stale**" with no coverage clause at all: **the containment test in the code was never in the architecture.**
4. **[glossary](../glossary.md)** — *Retention predicate*, beside *Admission predicate*.

## Boundaries involved

| Boundary | Owner | What this does to it |
|---|---|---|
| `Axis` — universal surface | [ADR-0002](../adr/0002-data-model.md) | **One predicate added** (`satisfied_by`) with a total containment default; `RollingAxis` overrides it. No other kind changes. |
| Admission (`matches`) | [ADR-0004](../adr/0004-producer-resolution-and-capability.md) | **Untouched.** Nothing about what is admitted moves. |
| `Reservoir` — retention policy | [architecture.md](../architecture.md), [ADR-0001](../adr/0001-manifold-algebra-and-composition.md) | Stops holding the rule and stops unwrapping intervals: **`_required_coverage` is deleted**. `capability` still forwards the source's unchanged ([reservoir.py:98](../../src/meteoscape/nodes/reservoir.py)). |
| The refill gate — "covers-or-refetch-whole" | [006 align](../tickets/done/01-0115-retentive-store-freshness.md) | **Revised for rolling sources** → [below](#what-this-revises). Static sources keep it exactly. |
| `ground` / `clip` / `agreed_geometry` | [ADR-0002](../adr/0002-data-model.md) | **Untouched.** Already tolerant: a `SnappedAxis` carries bounds only and `ground` asks the record's own axis to clip itself ([domain.py:653](../../src/meteoscape/manifold/domain.py)). No algebra added. |
| Failure semantics at the serving seam | ticket, [#39](../concerns.md#39-python-embedding-surface-and-public-failures) | An ask a refill cannot satisfy becomes `CapabilityMismatch`, not `RuntimeFailure`. |
| Spatial read-back guards | [0117](../tickets/done/01-0117-off-grid-homogenization.md) | **Untouched and still fatal.** T-only, and it follows from `RollingAxis` being temporal-by-type — not from a hand-written axis filter. |
| MCP edge contract | [edge/mcp.md](../edge/mcp.md) | **Unchanged.** A narrower-than-asked answer is already how that edge discloses reach. |

## The two defects, and why one predicate closes both

Both are live on TWC's default path the day it becomes primary; neither is visible on Open-Meteo.

**Defect 1 — the unsatisfiable gate.** TWC's series starts at the *next* whole hour while `W` floors
to the current one, so `now` always sits in a declared-but-undelivered gap. A default request's lower
bound is `clock.now()` verbatim ([mcp_app.py:146](../../src/meteoscape/api/mcp_app.py)), so
containment is never satisfiable and **every request refetches**.

**Defect 2 — the Shelf outranks the cadence.** Reach and expiry are both pure functions of the
clock, so the containment test and the freshness test ask the same question at different
granularities — and the finer one always wins:

```
t0 = 11:42  fetch → holding [12:00, 12:00+239h], expires 23:42   (cadence 12h)
t  = 12:05  declared reach advances to [13:00, 13:00+239h]        (shelf 1h)
            over.upper = 13:00+239h  >  held.upper = 12:00+239h  → REFETCH
```

**The Reservoir refetches hourly regardless of the configured cadence** — the 12 h policy is
decorative. This is independent of defect 1 and survives any correction to the *declaration*, since a
correctly-declared window advances hourly too.

**Defect 2's exact trigger is `shelf < cadence`** — that is when the reach advances before
freshness expires. Open-Meteo declares a `24h` Shelf against a `1h` cadence
([open_meteo.py:53-58](../../src/meteoscape/nodes/providers/open_meteo.py)), so expiry always fires
first and the coverage test never bites; TWC declares `1h` against `12h`, so it bites eleven times out
of twelve. That is the whole reason this has never shown in the shipped tree, and it is checkable
rather than asserted.

Four cases decide the rule. The fourth is why the rolling arm is **not** plain overlap
*(corrected on the second validation pass — an earlier draft of this RFC said `intersects`)*:

| | containment (today) | drop the test | overlap | **horizon ≥ ask start** |
|---|---|---|---|---|
| **A** ask starts before the Holding (defect 1) | refetch — storm | serve ✓ | serve ✓ | serve ✓ |
| **B** clock crossed a shelf boundary, Holding fresh (defect 2) | refetch — cadence overridden | serve ✓ | serve ✓ | serve ✓ |
| **C** Holding fallen entirely behind `now` | refetch ✓ | serve nothing — **fault** | refetch ✓ | refetch ✓ |
| **D** ask lies wholly *inside* the gap | refetch every ask | refetch every ask | **refetch every ask** | satisfied ✓ |
| **E** archive: wider ask than the held slice | refetch ✓ | never fills — **wrong** | **wrong** | n/a — static arm |

**Case D is the one that kills overlap.** An ask lying entirely below the Holding never overlaps it, so
`intersects` reports "missing" forever: the refill returns the same series, the next ask repeats it, and
this RFC's own stage-3 criterion ("a second such ask makes no child call") becomes unsatisfiable. The
correct rolling rule follows from monotonicity — the window only moves *forward*, so the only way a
Holding can fail is by **not having reached the ask yet**:

```
satisfied  ⇔  want.lower <= held.extent.upper
```

Case E is why the rule cannot be flat in the Reservoir and must dispatch on the declared axis: for a
static corpus a Holding is a *slice of something larger*, and only the declaration knows that.

## Facts about our own tree (verified 2026-08-11)

1. **Admission is intersective for snapped T.** `requested.axis(n).matches(declared[n])` ([domain.py:458](../../src/meteoscape/manifold/domain.py)) with `SnappedAxis.matches` = `intersects` ([domain.py:317](../../src/meteoscape/manifold/domain.py)). A request need only *overlap* the declared window — so a late declaration rejects nothing that overlaps, and an ask wholly inside the gap is the only thing admission itself excludes.
2. **The timeline refill is boundless on T** — `quantize` overrides deferred axes with `SnappedAxis(name, None)` ([store.py:198](../../src/meteoscape/nodes/store.py)); the timeline store defers `{T, Z}`. **But this is a per-store fact, not universal:** an archive store shapes Holdings differently, which is exactly why the predicate must be kind-dispatched rather than assuming whole-fetch Holdings.
3. **The store returns the Holding whole** ([store.py:133-143](../../src/meteoscape/nodes/store.py)), so `held.capability.reach(pid)`'s T axis **is** the delivered series.
4. **`valid_time` floors** ([cadence.py:31](../../src/meteoscape/manifold/cadence.py)), and `RollingAxis.clip` anchors the materialized lattice at the window's lower bound ([cadence.py:56](../../src/meteoscape/manifold/cadence.py)) — the mechanical basis for ADR-0003's phase rule. It runs on the real fetch path via `_resolve` ([timeline.py:141-149](../../src/meteoscape/nodes/providers/timeline.py)).
5. **A provider's footprint T *is* a `RollingAxis`** ([timeline.py:318](../../src/meteoscape/nodes/providers/timeline.py)), and composition passes the producer's own `Domain` through rather than synthesising one ([architecture.md § Reach](../architecture.md)), so the kind survives to both Reservoir positions.
6. **`matches` already takes an `Axis` and reads `.extent` internally** ([domain.py:112](../../src/meteoscape/manifold/domain.py)) — the convention the sibling follows, and what lets the Reservoir stop touching intervals.
7. **The test fakes already declare a rolling T** and accept a `CadenceDef` override ([fakes.py:96-109](../../tests/deterministic/fakes.py)). A **static** T fixture also already exists — `test_parameter_whose_reach_left_the_window_is_not_served_from_holdings` builds a `FootprintDomain` with a `ContinuousAxis` on T ([test_reservoir.py:548](../../tests/deterministic/nodes/test_reservoir.py)), which is the pattern the static-arm test reuses. That test is itself **unaffected**: its second parameter's reach does not intersect the ask, so admission drops it before the gate is reached.
8. **`test_window_extension_refetches_the_whole_holding`** ([test_reservoir.py:485](../../tests/deterministic/nodes/test_reservoir.py)) pins containment for a T-deferred store; under the new rule it goes from two child calls to one → [what this revises](#what-this-revises).
9. **`CoverageSet` enforces one owning record per parameter** and builds its `GranularCapability` from it ([coverage.py:63-75](../../src/meteoscape/manifold/coverage.py)), so `held.capability.reach(pid)` is unambiguous. The plan depends on this; it is an invariant, not a coincidence.
10. **Both shipped cadences already satisfy `cadence ≤ max_lead`** — Open-Meteo `1h ≤ 383h` ([open_meteo.py:53-58](../../src/meteoscape/nodes/providers/open_meteo.py)), the fake `1h ≤ 7d` ([fakes.py:41-45](../../tests/deterministic/fakes.py)) — so the invariant can be enforced centrally without breaking the tree.
11. **`_t_extent` exists twice**, in `reservoir.py` and independently in [mcp_app.py:195](../../src/meteoscape/api/mcp_app.py). Only the Reservoir's is collapsed here; the edge's copy is untouched (duplication pre-dates this and belongs to [#22](../concerns.md#22-lattice-helpers-vs-domain--sampling-module-split)).

## Code shape

### 1. The predicate pair (`domain.py`, `cadence.py`)

```python
class Axis(ABC):
    def matches(self, declared: Axis) -> bool:
        """Whether this *requested* axis matches a *declared* axis — default: full containment."""
        return declared.extent.contains(self.extent)

    def satisfied_by(self, held: Axis, needed: Axis) -> bool:
        """Whether `held` answers `needed` as completely as I will ever answer it (ADR-0002).

        Admission's sibling, dispatched on the declaration rather than the request. Default — a
        static axis does not move, so a Holding is a slice of something larger and a wider ask is
        genuinely unanswered until more is fetched.

        `needed` must be bounded: an `ANY` member has no extent, and the caller skips the check
        entirely in that case rather than passing one here.
        """
        want = needed.extent.intersection(self.extent)
        return want is None or held.extent.contains(want)
```

```python
class RollingAxis(Axis):
    def satisfied_by(self, held: Axis, needed: Axis) -> bool:
        """Satisfied unless my horizon has fallen behind the ask — reach-advance IS staleness here.

        My window is a pure function of the clock, so it only ever moves forward: the one way a
        Holding can fail an ask is by not having reached it yet. What it lacks *below* its own start
        was never published, and what it lacks *above* arrives with time, which `expiration` already
        governs — demanding containment would make my *Shelf*, not the declared cadence, the real
        refetch interval.

        Deliberately weaker than overlap: an ask lying wholly below the Holding is satisfied, because
        refetching moves the window further away. That ask is unservable, not unfetched, and the
        serving seam reports it as `CapabilityMismatch` rather than buying a useless fetch per call.
        """
        want = needed.extent.intersection(self.extent)
        return want is None or want.lower <= held.extent.upper
```

The intersection sits **inside**, which is what deletes `_required_coverage`. `matches` carries a
`# type: ignore[arg-type]` for the same generic-`Interval` reason; expect the same here.

### 2. The gate asks instead of comparing (`reservoir.py`)

```python
def _missing(self, admitted, held, selection) -> frozenset[ParameterId]:
    # Under ANY on T a Holding is the whole of one fetch, so freshness alone governs.
    needed = None if AxisName.T in open_axes(selection.domain) else _t_axis(selection.domain)
    missing: set[ParameterId] = set()
    for pid in admitted:
        if pid not in held.capability.parameters:
            missing.add(pid)
            continue
        if needed is not None and not _t_axis(self.source.capability.reach(pid)).satisfied_by(
            _t_axis(held.capability.reach(pid)), needed
        ):
            missing.add(pid)
            continue
        if _owning(held, pid).provenance.summary(pid).expiration <= self._clock.now():
            missing.add(pid)
    return frozenset(missing)
```

`_t_axis` is the axis-returning form of `_t_extent` — the same `as_separable(...).axis(AxisName.T)`
read, stopping one step earlier. **`_request_t_bounds` and `_t_extent` collapse into it** and
`_required_coverage` is deleted: one method and one helper fewer, no intervals in the Reservoir, no
axis-kind branch.

**One thing the predicate must not silently swallow.** `_required_coverage` today raises
`RuntimeFailure` when request and reach do not meet at all; under `satisfied_by` that becomes
`want is None → satisfied`. Since `serves` has already admitted the parameter, no overlap is an
**engine invariant break**, so it keeps an explicit assert in the Reservoir rather than vanishing into
a `None` arm.

### 3. A refill that cannot satisfy the ask says so (`reservoir.py`)

An ask lying wholly inside the gap is admitted (fact 1 — intersective admission is against the
*declared* window, which spans the gap), and no refill can serve it. Today it reaches `ground`, clips
to `None`, and surfaces as `RuntimeFailure("Holdings cannot ground onto an admitted request")`
([reservoir.py:177](../../src/meteoscape/nodes/reservoir.py)).

After the refill, if the Holdings still do not meet the ask, raise **`CapabilityMismatch`** naming the
asked window and what is held. A pre-check, not a reinterpretation of `ground`'s `ValueError`, which
is raised for several unrelated reasons and whose messages are not a contract
([edge/provider.md](../edge/provider.md)). It is kind-agnostic — "does not meet at all" needs no axis
knowledge — and **all-or-nothing in v1**, because every parameter shares one T reach
([reservoir.py:161](../../src/meteoscape/nodes/reservoir.py)); the diverging case stays
[#30](../concerns.md#30-response-membership-under-runtime-degraded-fallback)'s.

`CapabilityMismatch` rather than `RuntimeFailure` because it is substantively true, and because it is
what lets the Arbiter reach the backstop once
[fall-through](../tickets/01-0121-second-provider-fallback.md) lands — Open-Meteo, day-anchored,
genuinely *can* serve those hours.

## What this revises

**006's align chose "covers-or-refetch-whole"** for the partial-warm edge
([006 ticket](../tickets/done/01-0115-retentive-store-freshness.md)), and fact 8's test pins it. For a
**rolling** source that decision is now wrong, for the reason ADR-0002 records: a Holding there is a
whole fetch, so "partially warm" can only arise from the clock advancing — and how often to take newer
data is what the cadence exists to say. **For static sources the decision stands unchanged**, which is
what the containment default preserves.

`test_window_extension_refetches_the_whole_holding` must therefore be **rewritten, not deleted**: its
`_Widening` fake models a vendor extending its horizon with the clock stopped, which a clock-anchored
window cannot do. Re-point it at the case that *is* real — the Holding falling behind `now` — and keep
a sibling asserting the static arm still refetches on a wider ask.

## Stages

### Stage 1 — the predicate pair *(red → green)*

Axis-level tests in `tests/deterministic/manifold/`, before any Reservoir change — cheapest place to
pin the rule, hardest to misread:

**The `window_quantum` → `shelf` rename already landed** (2026-08-11, ahead of this ticket, so TWC
would not ship on the old name): the field and its docstring, Open-Meteo's `CADENCE`, four cadence
tests renamed with it, and the `mcp_app` test site. Behaviour-neutral — 308 deterministic tests and
`pyright` green. Nothing remains for this stage; the glossary's *Shelf* entry is the term's home.

One test per row of [the four cases](#the-two-defects-and-why-one-predicate-closes-both), because each
encodes a different reason:

- **static**, unsatisfied by Holdings short at *either* edge (case E); satisfied when they contain what
  it offers;
- **rolling A** — satisfied by Holdings short at the leading edge;
- **rolling B** — satisfied by Holdings short at the horizon while the ask has started; the assertion
  that keeps cadence in charge, with a comment saying so;
- **rolling C** — **unsatisfied** by Holdings entirely behind the ask; the case that stops the rule
  being merely permissive. **This is the only home for that proof**: the `cadence ≤ max_lead` invariant
  (stage 4) makes it unreachable through a real `CadenceDef`, so the predicate handles it defensively
  and no Reservoir-level test can construct it without violating the invariant;
- **rolling D** — **satisfied** by Holdings entirely *above* the ask. Counter-intuitive and therefore
  the one most likely to be "fixed" into overlap later, so its test carries the reason: refetching
  moves a rolling window further away, so the ask is unservable rather than unfetched;
- both arms clamp `needed` to their own extent first: an ask running past the declared reach does not
  make Holdings unsatisfying, because the axis never offered it;
- the `want is None` arm asserted directly, since the Reservoir's assert depends on it being reachable
  only as an invariant break.

Then the two methods.

### Stage 2 — the gate asks *(red → green)*

Reservoir tests with a source whose declared window opens **before** its delivered records (fact 7 —
`footprint_domain(clock, cadence=…)`, `1h` Shelf, records anchored an hour later):

- **defect 1** — two successive asks whose lower bound sits in the gap produce **exactly one** child
  call;
- **defect 2** — advance the clock past a shelf boundary but not past expiry; assert **no** second
  call. This is the one that proves cadence outranks the Shelf;
- advance past **expiry**: assert the refetch does happen;
- a straddling ask **serves**, first tick = first *delivered* tick;
- **static T stays exact** — a source declaring static T, held short, **does** refill;
- the **no-overlap assert** survives the deletion of `_required_coverage`.

Then `_missing`, the `_t_axis` collapse, the deletion, and the rewrite of fact 8's test.

### Stage 3 — the serving seam *(red → green)*

- an ask wholly inside the gap raises `CapabilityMismatch`, not `RuntimeFailure`, naming the window —
  assert type **and** reason;
- a second such ask makes **no** child call.

### Stage 4 — guards and records *(green)*

- **space stays strict** — 0117's enclosing-cell assertions unchanged;
- **Open-Meteo is a no-op**, and provably rather than hopefully: its `24h` Shelf exceeds its
  `1h` cadence, so expiry always fires before the reach advances and the old containment test never
  bit (fact 10). Assert via the existing e2e re-fetch expectations, which must not move;
- **`cadence ≤ max_lead`** — the ADR-0003 corollary. **Enforced in `CadenceDef.__post_init__`, not in
  a provider's `build`** *(corrected on the second validation pass: the earlier draft put it in TWC's
  `build`, which cannot work — `twc.py` does not exist until 011, which lands **after** this ticket)*.
  Central enforcement is better anyway: the constraint is universal, and fact 10 confirms both shipped
  cadences already satisfy it, so nothing breaks. TWC's `hourly_6hour` offering (`max_lead = 5h`)
  against a 12 h default then fails at boot when 011 lands, which is where that trap should surface.

Records: tick the ticket into `done/`; delivery-status row and retentive-cache capability line;
discharge the `⚠` in [edge/provider.md](../edge/provider.md); record the #21 family note.

## Limitations and follow-ups

- **A rolling source can now serve a horizon shorter than it narrates**, by up to one cadence, until
  expiry. That is a cache TTL behaving like a cache TTL: `valid_time` discloses what was served and
  `exp` says when to return. The [MCP edge](../edge/mcp.md) already treats answers that stop early as
  honest disclosure.
- **Operator cadence, vendor expiry as fallback** is the right long-term freshness shape and is not
  built here → [ideas: freshness](../ideas.md#freshness). The blocker is unchanged: `expiration` is
  also the refetch trigger, so adopting TWC's ~5-minute value *is* setting the polling interval to five
  minutes. With `cadence_hours` always defaulted, the fallback never fires today.
- **The declared extent is re-read per parameter**, since `RollingAxis.extent` reads the clock on every
  access and `_missing` loops parameters. Under an advancing clock two parameters can therefore see
  windows microseconds apart. This is **pre-existing** — `_required_coverage` reads it per parameter
  today — but it sits against `RollingAxis.clip`'s own warning never to re-derive a window from the
  axis. Not fixed here; a single per-request read is the obvious repair once a diverging-reach
  capability makes it observable → [#30](../concerns.md#30-response-membership-under-runtime-degraded-fallback).
- **This does not narrow [#21](../concerns.md#21-serves-extent-vs-project-crop-ability)** — its
  off-phase / different-step case is untouched; only the family membership is recorded.
- **A wholly-in-gap ask still costs one fetch when the store is cold** — the parameter is absent, so
  the gate refills before anything can be known. First-touch cost, not a leak.
- **No `TODO` markers are introduced.** The predicate pair is the intended long-term shape, and the
  static default is what the archive sources will exercise.
