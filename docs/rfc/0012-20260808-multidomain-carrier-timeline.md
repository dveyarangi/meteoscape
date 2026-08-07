# RFC 0012 · 2026-08-08 · Multi-domain carrier and the timeline rework — implementation plan

Implementation plan for [multi-domain carrier and the timeline rework](../tickets/01-0115.0020-multidomain-carrier-timeline.md)
(slice 2 of the [retentive store](../tickets/01-0115-retentive-store-freshness.md)). Closes the
[provider edge record](../edge/provider.md)'s fold/carrier **naming checkpoint** — the names are
decided here, not deferred further.

**Scope in one line:** `agreed_geometries` (renamed, always a tuple), `CoverageGroup` (the carrier,
beside `CoverageRecord`), and a timeline `project` that answers **open asks** with its natural shape
— all live (bounded) paths byte-identical.

## Boundaries involved

| Boundary | Owner | What this does to it |
|---|---|---|
| `agreed_geometry` (`manifold/domain.py`) | [ADR-0001](../adr/0001-manifold-algebra-and-composition.md) / [ADR-0002](../adr/0002-data-model.md) | Renamed **`agreed_geometries`**, returns `tuple[EnumerableDomain, ...]`; gains `open: frozenset[AxisName]`. Law unchanged on bounded axes. |
| Carrier | ADR-0001 (closure), ADR-0007 (capability) | **`CoverageGroup`** minted beside `CoverageRecord` (`manifold/coverage.py`): a `Manifold` over records on differing native domains. |
| `TimelineProvider.project` (`nodes/providers/timeline.py`) | [edge/provider.md](../edge/provider.md) | Open asks: all taps engaged (natural fetch unit), no parameter crop, `CoverageGroup` answer. Bounded asks: exactly today's path. |
| ADR-0001 answer discipline | ADR-0001 | Amended at landing: *an answer may be wider than the ask on the parameter facet, never narrower; the natural fetch unit is the leaf's own.* |
| Edge (`mcp_app.py`), Arbiter, Calculators, Reservoir | — | **Untouched** — nothing in-tree authors an open member yet. |

## Facts that shape the implementation (verified 2026-08-08)

1. `agreed_geometry` has exactly two call sites, both in `timeline.py` (`_resolve` pre-fetch over
   footprints, `_answer` post-fetch over records) — the rename touches nothing else.
2. The parameter crop lives at `timeline.py:268` (`_as_delivered` keeping only
   `selection.parameters`); the Z fold is `_assemble`. Both are reached from `project`
   unconditionally today.
3. The MCP serializer emits every parameter block the root Coverage carries — an unconditionally
   wide answer would leak extra parameters onto the wire. This is why the natural fetch unit
   **rides open asks only** (decision 3); the live-path invariance criterion depends on it.
4. `TapTable.engaged_by` narrows taps; `variables` dedups vendor vars. Engaging the full table is
   the whole-offering fetch — one HTTP call either way (`open_meteo` taps share `hourly=` listing).

## Design decisions

1. **The fold: `agreed_geometries(grounded, open) -> tuple[EnumerableDomain, ...]`.** No new noun
   for a geometry group — a tuple is the group. Semantics: every resolution must be equal on every
   axis **not** in `open` (else `ValueError`, message naming the axis); resolutions differing only
   on `open` axes become distinct members, first-seen order, exact duplicates folded. A
   fully-bounded call (`open=frozenset()`) returns a 1-tuple — both call sites unwrap with a local
   `[single] = agreed_geometries(...)` destructure, which *is* the degenerate-single rule. `open`
   is computed by the caller holding the request:
   `frozenset(n for n in AXIS_ORDER if isinstance(d.axes[n], SnappedAxis) and d.axes[n].interval is None)`
   for a `SelectionDomain`, else empty — a small `open_axes(domain)` helper beside `ground`.
2. **The carrier: `CoverageGroup`, beside `CoverageRecord` in `manifold/coverage.py`.** It also
   mints `CoverageGroup.of(answer)` — identity on a group, a one-record wrap on a single Coverage —
   the normalization the `Reservoir` pipeline applies before `assimilate` (RFC 0013 d.4).

   ```python
   @dataclass(frozen=True)
   class CoverageGroup:
       """The multi-domain answer: single-domain records the request's open axes let differ.
       A Manifold — project with a fully enumerable Selection to fold onto one Coverage."""
       records: tuple[CoverageRecord, ...]

       async def project(self, selection: Selection) -> Manifold:
           # enumerable ask → the retired eager fold, applied lazily (the _assemble logic,
           # relocated here); any other ask raises CapabilityMismatch — its two consumers
           # (store.assimilate reads .records; closure callers fold) need nothing else.
       @property
       def capability(self) -> Capability:
           # per-parameter reach read from the owning record (ADR-0007 shape), parameters = union.
   ```

   **Invariant (constructor-checked): the records' parameter sets are disjoint** — a parameter
   lives on exactly one native domain per answer (true by tap construction: each tap declares one
   Z). "The owning record" and the capability union are only well-defined because of it; a
   violating group is a construction error, not a served answer.

   `_assemble` moves here (with its tests); `timeline.py` keeps no fold.
3. **Timeline `project` branches once, on the ask's openness — not on request *mode*.** With
   `open = open_axes(selection.domain)`:
   - `open` empty → today's path, unchanged end to end: engaged taps, single agreed geometry
     (destructured 1-tuple), `resample` crop, parameter crop. Closure intact.
   - `open` non-empty → **natural fetch unit**: the full tap table is engaged, the answer keeps
     every fetched parameter (no crop), records grouped by
     `agreed_geometries((ground(selection.domain, r.domain) for r in records), open)` →
     `CoverageGroup` with one record per agreed geometry. The pre-fetch fold runs with the same
     `open` (footprints differing on Z under an open Z are the licensed case; the fetch window
     reads T from any member — they agree on T by the fold's own law).
   This is not a mode branch in the forbidden sense: the leaf still writes no snap arithmetic and
   no request-shape gate; it reads one derived fact (`open`) the algebra defines.
4. **Naming checkpoint closed:** `agreed_geometries` (the `agreed_` stem survives; the plural is
   the group), `CoverageGroup` (a group of Coverages — says exactly what it holds, no new
   vocabulary). Recorded in the edge record at landing; glossary entry for the carrier added then.
5. **ADR-0001's answer-discipline sentence lands with this slice** (the license is first exercised
   here). The [pipeline slice](../tickets/01-0115.0040-reservoir-retention-pipeline.md) carries
   only the remaining doc syncs.

## Stages (each green)

Stages are landing milestones, not single red→green cycles: within each, work proceeds one
observable behavior → minimal implementation at a time per `/tdd`.

1. **Fold** — red: group semantics (bounded-axis disagreement raises; open-axis difference groups;
   duplicates fold; 1-tuple for closed asks). Green: rename + `open` parameter + tuple return;
   both call sites destructure the 1-tuple (behavior unchanged — every existing timeline test
   stays green).
2. **Carrier** — red: `CoverageGroup.project` under an enumerable Selection reproduces the folded
   answer (port the `_assemble` tests); capability parameters/reach. Green: mint the class, move
   `_assemble`.
3. **Open-ask answering** — red: direct provider tests — boundless Z/T ask → one vendor fetch,
   records keyed by native Z; parameter-subset ask with open axes → whole offering in the answer;
   bounded asks byte-identical (full suite). Green: the `project` branch of decision 3.
4. **Docs** — ADR-0001 sentence, edge-record checkpoint closure, carrier glossary entry.

## Out of scope / follow-ups

- No in-tree author of open members until `quantize` (RFC 0013); `CoverageGroup` reaches no store
  until the [pipeline slice](../tickets/01-0115.0040-reservoir-retention-pipeline.md).
- How `CoverageGroup` flows through Arbiter/Calculator on the best-view path is the pipeline
  slice's question, flagged in RFC 0014 — nothing here presumes an answer.
