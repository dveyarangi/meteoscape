# RFC 0012 · 2026-08-08 · Multi-domain carrier and the timeline rework — implementation plan

Implementation plan for [multi-domain carrier and the timeline rework](../../tickets/done/01-0115.0020-multidomain-carrier-timeline.md)
(slice 2 of the [retentive store](../../tickets/done/01-0115-retentive-store-freshness.md)). Closes the
[provider edge record](../../edge/provider.md)'s fold/carrier **naming checkpoint** — the names are
decided here, not deferred further.

**Scope in one line:** `clip` without bounds (which is what makes a boundless ask resolvable at all),
`agreed_geometry` (request-derived licence, single return), `CoverageSet` (the carrier, beside
`CoverageRecord`), and a timeline `project` that answers **boundless asks** with its natural shape —
all bounded paths byte-identical.

## Boundaries involved

| Boundary | Owner | What this does to it |
|---|---|---|
| `Axis.clip` (`manifold/domain.py`, `manifold/cadence.py`) | [ADR-0002](../../adr/0002-data-model.md) | Takes `Interval \| None`; **no bounds = the axis entire**. One clock read on a `RollingAxis`. |
| `ground` | ADR-0002 / [ADR-0001](../../adr/0001-manifold-algebra-and-composition.md) | Loses its boundless arm — one `clip` call serves both snapped forms. |
| `agreed_geometry` (`manifold/domain.py`) | ADR-0001 / ADR-0002 | Keeps its name and single return; takes the `request: Domain` it resolves and derives its own licence (`open_axes`), under which differing resolutions validate instead of raising. Law unchanged on bounded axes. |
| Carrier | ADR-0001 (closure), [ADR-0007](../../adr/0007-capability-carries-its-domain.md) (capability) | **`CoverageSet`** minted beside `CoverageRecord` (`manifold/coverage.py`): a `Manifold` over records on differing native domains. |
| `TimelineProvider.project` (`nodes/providers/timeline.py`) | [edge/provider.md](../../edge/provider.md) | Boundless asks: all taps engaged (natural fetch unit), no parameter crop, `CoverageSet` answer. Bounded asks: exactly today's path. One pre-fetch decline replaces both unserved-parameter guards. |
| ADR-0001 answer discipline | ADR-0001 | Amended at landing: *an answer may be wider than the ask on the parameter facet, never narrower; the natural fetch unit is the leaf's own.* |
| Edge (`mcp_app.py`), Arbiter, Calculators, Reservoir | — | **Untouched** — nothing in-tree authors a boundless member yet. |

## Facts that shape the implementation (verified 2026-08-08)

1. **`RollingAxis` is not an `EnumerableAxis`** — a footprint's T becomes cells only inside `clip`
   ([cadence.py:48](../../../src/meteoscape/manifold/cadence.py)). The landed boundless arm
   ([domain.py:626](../../../src/meteoscape/manifold/domain.py)) demands an already-enumerable answering
   axis, so **an open T declines against every provider footprint** — the pre-fetch fold's own input.
   The landed test grounds a boundless member against a *delivered* `GridDomain`
   ([test_domain.py:369](../../../tests/deterministic/manifold/test_domain.py)), which is why the gap is
   invisible today. Decision 1 is what makes the ticket's first criterion reachable.
2. `agreed_geometry` has exactly two call sites, both in `timeline.py` (`_resolve` pre-fetch over
   footprints, `_answered_geometry` post-fetch over records) — the fold change touches nothing else.
3. Every footprint shares **one `RollingAxis` instance** (`_declare_footprints` builds the X/Y/T
   block once) and the provider takes **one `CadenceDef`**, so every per-parameter footprint grounds
   its T identically. A boundless X/Y cannot produce a resolution at all — the footprint's X/Y are
   `ContinuousAxis`, and a span has no cells — so it declines pre-fetch.
4. The parameter crop lives at `timeline.py:268` (`_as_delivered` keeping only
   `selection.parameters`); the Z fold is `_assemble`. `_as_delivered` reads `records[0]` **twice** —
   for the provenance plane *and* for the T lattice.
5. The MCP serializer emits a block per parameter the Coverage **carries**
   ([mcp_app.py:236](../../../src/meteoscape/api/mcp_app.py)), and nothing between leaf and wire narrows
   a single-winner answer (the `Reservoir` is a pass-through;
   [arbiter.py:167](../../../src/meteoscape/nodes/arbiter.py) returns the sole winner's Coverage
   verbatim). An unconditionally wide answer would put `wind_u`/`wind_v` — inputs the edge keeps out
   of its exposure — on the wire.
6. `TapTable.engaged_by` narrows taps; `variables` dedups vendor vars. Engaging the full table is
   the whole-offering fetch — one HTTP call either way (`open_meteo` taps share `hourly=` listing).
7. `resample` sets the answer's domain to `selection.domain` and, where either side is not a
   `RegularAxis`, requires only equal length — so cropping a native Z point onto a vantage cell is an
   identity crop that **relabels**, which is exactly today's fact→product step.
8. Neither the `not engaged` guard (`timeline.py:97`) nor the post-fetch missing-parameter guard
   (`timeline.py:272`) is pinned by any test, and neither is reachable through the Arbiter, which
   projects a winner only with the parameters that winner admits.

## Design decisions

1. **`clip` without bounds is the axis entire; `ground` loses its boundless arm.** `ANY` is a snapped
   member, so it takes the same verb — with nothing to restrict it:

   ```python
   class Axis(ABC):
       @abstractmethod
       def clip(self, bounds: Interval | None) -> Axis | None:
           """The part of me within `bounds` — all of me when there are none, `None` when we
           do not meet."""
   ```

   Per kind: `RegularAxis`, `ContinuousAxis` return `self` for `None`; `IntervalAxis` returns `self`
   when `bounds is None or self.interval.intersects(bounds)`; `SnappedAxis` returns `self` (nothing
   bounds the boundless, and a snapped member is never asked for a part of itself); `RollingAxis`
   materializes its live window **once** and returns it whole or clipped:

   ```python
   def clip(self, bounds: Interval | None) -> RegularAxis | None:
       window = self.extent                                   # the single clock read
       materialized = RegularAxis(self.name, window.lower, self.step,
                                  (window.upper - window.lower) // self.step + 1, cellular=True)
       return materialized if bounds is None else materialized.clip(bounds)
   ```

   The single read is load-bearing: reading the extent in `ground` and again inside `clip` could
   straddle the availability quantum and silently trim the answer. `ground` becomes two arms:

   ```python
   member = request.axes[name]
   if not isinstance(member, SnappedAxis):
       axes[name] = member                                    # pinned — identity
       continue
   if answering is None:
       raise ValueError(f"a snapped {name.value} grounds only against separable geometry")
   part = answering.axis(name).clip(member.interval)          # no bounds → the axis entire
   if part is None:
       raise ValueError(f"no {name.value} within the requested bounds")
   if not isinstance(part, EnumerableAxis):
       raise ValueError(f"a snapped {name.value} needs cells; the answering {name.value} is a span")
   axes[name] = part
   ```

   Cells stay `ground`'s requirement, not `clip`'s (ADR-0002). **One decline message for both
   forms, and it is the sketch's** — `"a snapped {axis} needs cells; the answering {axis} is a
   span"` — because the boundless member *is* a snapped member; the landed test's
   `"an open t needs cells"` match assertion is updated to it. Identity is preserved wherever it
   held before: an already-enumerable answering axis returns `self` from `clip(None)`.
2. **The fold: `agreed_geometry(grounded, *, request) -> EnumerableDomain`.** The name and the
   single return stay: no consumer reads the differing resolutions as a value — records carry
   their own domains, and the carrier (decision 3) is built from records. The licence to differ is
   a **fact of the request**, not a caller decision, so the fold derives it itself
   (`open_axes(request)`); a call site cannot state a licence its request does not grant.

   Semantics: resolutions must be **equal on every axis the request does not leave entirely to the
   producer**, and the first disagreement raises `ValueError` **naming the axis**; an empty input
   raises (unchanged message). Resolutions differing only on open axes are licensed; the fold
   validates them and returns the **first** resolution — authoritative on every bounded axis,
   which is all any caller reads (a group return was rejected: its tail members had no reader, and
   `[single] = ...` destructures at every call site were noise). Separability is the precondition
   of comparing *differing* members, never of publishing agreeing ones: duplicates fold on whole
   equality alone, so an exact non-separable request — which grounds by identity against every
   footprint ([#12](../../concerns.md#12-curvilinear-domains)'s target role) — folds without exposing
   axes; only distinct members must expose them to confine their difference to the open set, and a
   distinct member without axes raises.

   The open set itself stays a public fact beside `ground` — decision 4's `project` branches on it:

   ```python
   def open_axes(domain: Domain) -> frozenset[AxisName]:
       """The axes a request leaves entirely to the producer — empty for anything but a Selection."""
       if not isinstance(domain, SelectionDomain):
           return frozenset()
       return frozenset(
           name for name in AXIS_ORDER
           if isinstance(member := domain.axes[name], SnappedAxis) and member.interval is None
       )
   ```
3. **The carrier: `CoverageSet`, beside `CoverageRecord` in `manifold/coverage.py`.**

   ```python
   @dataclass(frozen=True)
   class CoverageSet:
       """The multi-domain answer: single-domain records the request's boundless axes let differ.

       A Manifold — project it with a fully enumerable Selection to fold onto one Coverage.
       """

       records: tuple[CoverageRecord, ...]
       _capability: Capability = field(init=False, repr=False, compare=False)

       def __post_init__(self) -> None:
           # One pass: the disjointness check and the capability it makes well-defined.
       async def project(self, selection: Selection) -> Manifold: ...
       @property
       def capability(self) -> Capability: ...
   ```

   **Invariant (constructor-checked): the records' parameter sets are disjoint** — a parameter lives
   on exactly one native domain per answer (true by tap construction: each tap declares one Z). "The
   owning record" and the capability union are only well-defined because of it; a violating group is
   a construction error, not a served answer.

   `capability` is a **`GranularCapability`**
   ([RFC 0015](./0015-20260808-per-parameter-materialized-capability.md)). One entry per parameter —
   `GranularCapability(reaches={pid: (record.capability.parameters[pid], record.domain) for record
   in records for pid in record.ranges})` — whence `reach(pid)` answers the owning record's
   enumerable domain and `parameters` is the disjoint union. The timeline store (slice 3)
   advertises through the same form.

   **`project` folds by cropping each record onto the target and merging** — not by unioning ranges
   and cropping once:

   ```python
   async def project(self, selection: Selection) -> Manifold:
       from .sampling import resample
       if not isinstance(selection.domain, EnumerableDomain):
           raise CapabilityMismatch("a coverage group folds onto an enumerable Selection only")
       unheld = selection.parameters - self._capability.parameters.keys()
       if unheld:
           raise CapabilityMismatch(f"coverage group does not hold {sorted(unheld)}")
       cropped = [
           resample(record, selection.with_params(wanted))
           for record in self.records
           if (wanted := selection.parameters & record.ranges.keys())
       ]
       return cropped[0] if len(cropped) == 1 else _merged(cropped, selection.domain)
   ```

   `_merged` builds one `CoverageRecord` co-domained on `selection.domain` — the cropped records'
   ranges and `ParameterDef`s unioned in record order, over the plane below. Three properties follow
   from that shape rather than from remembering them, which is why it is the shape (fact 4 and
   fact 7):

   - **No record is privileged.** Each parameter's values are cropped against *its own* record's
     lattice, so a group whose records differ on T is folded honestly instead of being stacked on
     `records[0]`'s ticks; a record whose Z cell count disagrees with the target is refused by
     `resample` instead of being silently mis-indexed.
   - **The provenance plane is built from the owning records.** `_merged` keeps a single plane when
     every cropped record carries an equal one — the one-fetch `Uniform` case, pinned by
     `test_open_meteo.py`'s `isinstance(coverage.provenance, Uniform)` — and otherwise emits
     `PerParameter` from each parameter's owning record `summary`.
   - **Fault classification stays where the knowledge is.** The carrier declines
     Manifold-conventionally with `CapabilityMismatch`; a `Shortfall` from an under-covering record
     propagates, and the *timeline wrapper* translates it at its boundary (decision 4). The generic
     type never encodes vendor-fault knowledge it cannot have. (A bare `Shortfall` escaping a
     `project` is the interim state concern [#30](../../concerns.md#30-response-membership-under-runtime-degraded-fallback)
     dissolves by padding that tail.)

   **The Z relabel is the carrier's, and it smears deliberately.** Cropping a native record onto the
   target relabels its Z cell onto the target's (fact 7) — the leaf's fact→product step, unchanged.
   It is honest only because admission gated each parameter against its own native Z footprint before
   the leaf was reached. The composed path's version is different and stays the `Reservoir`'s: a
   source Reservoir *selects* per parameter the record whose Z cell matches the handed vantage
   ([RFC 0014 d.2](./0014-20260808-reservoir-retention-pipeline.md)). Two relabels, two positions,
   neither derived from the other.

   `_assemble`, `_as_delivered`, and `_cropped` are deleted with their tests ported here; `timeline.py`
   keeps no **assembly** fold. It does keep the post-fetch `agreed_geometry` call, which is the
   law's statement and never a value (decision 4).
4. **Timeline `project` branches once, on the ask's boundlessness — not on request *mode*.**

   ```python
   async def project(self, selection: Selection) -> Manifold:
       if not selection.parameters:                      # pre-fetch: a decline costs no vendor call
           raise CapabilityMismatch(f"{self._source} Selection requests no served parameters")
       unserved = selection.parameters - self._taps.parameters
       if unserved:
           raise CapabilityMismatch(f"{self._source} does not serve {sorted(unserved)}")
       boundless = open_axes(selection.domain)
       engaged = self._taps if boundless else self._taps.engaged_by(selection.parameters)
       wanted = self._resolve(selection.domain, engaged)      # first resolution; bounded axes exact
       longitude, latitude = self._point_of(wanted)
       delivery = await self._probe.retrieve(
           longitude=longitude, latitude=latitude,
           over=self._window_of(wanted), variables=engaged.variables,
       )
       records = self._interpret(delivery, engaged, longitude=longitude, latitude=latitude)
       answer = self._answered_geometry(records, selection)   # the law's statement, both arms
       group = CoverageSet(tuple(records))
       if boundless:
           return group                                  # the natural shape, uncropped
       return await self._delivered(group, answer, selection.parameters)
   ```

   - **`_resolve` keeps its shape**: it grounds each engaged tap's footprint, folds under the
     request's own licence, translates the fold's `ValueError` into `CapabilityMismatch` as today,
     and narrows to `GridDomain` (v1 mints no other enumerable representation), so `_point_of` /
     `_window_of` read it at the type they already take. `_answered_geometry` is the same edit on
     the post-fetch side. `_interpret`'s return annotation narrows to `Sequence[CoverageRecord]` —
     it already builds only records, and the group constructor takes them at that type.
   - **One decline, pre-fetch, in the right category.** The two guards it replaces (fact 8) were
     the same fact — an ask engaging nothing this leaf serves — one reported in the wrong category
     (`not engaged`, an unservable request called an upstream fault) and one reported late
     (post-fetch missing-parameter). The empty-ask arm keeps today's wording with the category
     corrected, and covers what the collapse would otherwise leave open: with `unserved` empty for
     an empty ask, the boundless arm would engage the whole table and pay a vendor call for a
     selection asking nothing. Nothing else can leave a requested parameter unanswered: `interpret`
     yields a value for every engaged tap or raises. The check also cannot be read off `engaged`
     any more, since a boundless ask engages the whole table.
   - **`boundless` empty → today's path, unchanged end to end**: the engaged taps, the single
     agreed geometry, `resample` crop, parameter crop. Closure intact.
   - **`boundless` non-empty → the natural fetch unit**: the full tap table is engaged and the answer
     keeps every fetched parameter. This is the parameter-facet reading of what a boundless axis
     already says — *answer at your own shape* — so the widening is licensed by the ask, not by what
     happens to be croppable downstream (fact 5 is the consequence, not the reason). A bounded,
     fully specified ask keeps getting exactly what it named, retention or no retention.
   - **The fetch window is read from the fold's return**, sound because bounded axes are exact on
     it and the shape closes the rest: X/Y can never be boundless here (they would have declined
     pre-fetch) and one `CadenceDef` per instance means every footprint's T materializes
     identically (fact 3). Z is where resolutions legitimately differ and is not read. **A future
     shape with per-parameter cadences loses that guarantee and must fold its own window — the
     comment at the read says so.**
   - **Post-fetch, `agreed_geometry` validates rather than reorganizes.** `by_level()` already
     yields one record per native domain, so the `CoverageSet` is the records as-is and the fold's
     value is consumed only in the bounded arm. A boundless member is never *exact*, so a short
     delivery grounds shorter and is honest (the `Shortfall` path belongs to enumerable asks alone,
     unchanged).
   - **`_delivered` is the wrapper's whole fault boundary**, keeping today's leaf classifications:

     ```python
     async def _delivered(self, group, answer, parameters) -> Manifold:
         try:
             return await group.project(Selection(domain=answer, parameters=parameters))
         except Shortfall as exc:
             raise RuntimeFailure(f"{self._source} delivered less than it declared: {exc}") from exc
     ```

     The carrier's `CapabilityMismatch` arms are unreachable from here — the ask is the grounded
     enumerable answer and the pre-fetch guard already settled the parameters — so no broad catch
     stands over them.

   This is not a mode branch in the forbidden sense: the leaf still writes no snap arithmetic and no
   request-shape gate; it reads one derived fact (`open_axes`) the algebra defines.
5. **Naming checkpoint closed:** `agreed_geometry` keeps its singular name — one answer geometry
   is the law, and the fold returns exactly one; `CoverageSet` (a set of Coverages — says exactly
   what it holds, no new vocabulary). Recorded in the edge record at landing; glossary entry for
   the carrier added then.
6. **Three sentences land in the architecture docs with this slice** (stage 5), each decided at this
   RFC's align: ADR-0001's answer discipline (the licence is first exercised here); ADR-0002's
   `clip`-without-bounds reading and its fold paragraph; the glossary's `Clip` entry. The
   [pipeline slice](../../tickets/done/01-0115.0040-reservoir-retention-pipeline.md) carries only the
   remaining doc syncs.
7. **One existing fixture is corrected rather than preserved** (decided at stage 3, the one exception
   to *bounded paths byte-identical*). With `_as_delivered` gone, each record is cropped by `resample`
   against the ask itself, so a **pinned** Z is compared lattice-to-lattice and a 10 m wind record
   cannot answer a request pinning Z at 2 m — the alignment read admits no negative offset. A
   **vantage** Z still relabels by identity (fact 7), which is the mode every composed path uses:
   admission gates each parameter against its own Z footprint, so a 2 m pin never reaches the wind
   taps through the Arbiter. `test_wind_fetch_requests_shared_vendor_vars_once` therefore asks at the
   wind's own native level. Teaching the sampler to relabel across differing pinned lattices was
   rejected — that alignment law is what catches genuine mis-indexing.

## Stages (each green)

Stages are landing milestones, not single red→green cycles: within each, work proceeds one
observable behavior → minimal implementation at a time per `/tdd`.

1. **Clip without bounds** — red: each axis kind answers `clip(None)` with itself entire (a rolling
   axis with its live window materialized at the series step; a span still a span); a boundless T
   grounds against a **rolling footprint** into that whole window; a boundless member against a
   declared span still declines. Green: the `Interval | None` widening across the five
   implementations and `ground`'s two-arm form; the landed decline-message assertion moves to the
   shared wording.
2. **Fold** — red: licence semantics (disagreement on a bounded axis raises naming the axis; a
   difference on a boundless axis validates and the first resolution is returned; duplicates fold;
   empty input raises). Green: request-derived licence, single return unchanged in shape, so every
   existing timeline test stays green.
3. **Carrier** — red: `CoverageSet.project` under an enumerable Selection reproduces the folded
   answer (port the `_assemble` tests); records on differing T lattices each crop against their own;
   a mismatched cell count is refused rather than mis-indexed; the plane is `Uniform` when the
   records agree and `PerParameter` when they do not; overlapping parameter sets are rejected at
   construction; capability parameters and reach; a non-enumerable ask declines. Green: mint the
   class; delete `_assemble` / `_as_delivered` / `_cropped` and delegate through `_delivered`.
4. **Boundless answering** — red: direct provider tests — a boundless Z/T ask yields one vendor
   fetch with records keyed by native Z; a parameter-subset ask with a boundless axis carries the
   whole offering; a request naming an unserved parameter — or none at all — declines
   `CapabilityMismatch` **with no vendor call**; bounded asks byte-identical (full suite). Green:
   the `project` branch and the collapsed guard.
5. **Docs** — the three sentences of decision 6; the edge-record checkpoint closure and its
   `project` sketch (which this rework makes stale); the carrier glossary entry; and a re-read of the
   edge record's "which fold can actually fire" paragraph against the landed shape (the post-fetch
   fold's *raising* arm stays structurally unfirable on bounded axes — one stamped lattice — while
   boundless axes now license differences rather than fire it).

## Out of scope / follow-ups

- `CoverageSet.of` — the one-record normalization — lands with its only caller, the pipeline
  ([RFC 0014](./0014-20260808-reservoir-retention-pipeline.md) d.1); the store slice's tests
  construct groups directly.
- No in-tree author of boundless members until `quantize`
  ([RFC 0013](./0013-20260808-timeline-store.md)); `CoverageSet` reaches no store until the
  [pipeline slice](../../tickets/done/01-0115.0040-reservoir-retention-pipeline.md).
- How `CoverageSet` flows through Arbiter/Calculator on the best-view path is the pipeline slice's
  question, flagged in RFC 0014 — nothing here presumes an answer.
- Padding a short tail as `present=False`, which retires both the `Shortfall` raise and the
  wrapper's translation of it → [#30](../../concerns.md#30-response-membership-under-runtime-degraded-fallback).
