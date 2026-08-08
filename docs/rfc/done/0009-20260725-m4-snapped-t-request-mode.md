# RFC 0009 · 2026-07-25 · m4 — Snapped-T request mode: implementation plan

Implementation plan for [m4](../../tickets/done/01-0100-snapped-t-request-mode.md). The **mode** was settled at the
2026-07-25 align (recorded in the ticket; ADR-0002 already amended — Snapped is **bounds-only**: the
request fixes bounds, the resolver's grid supplies anchor *and* step,
`snapped → exact = anchor(grid) ⊕ step(grid) ⊕ bounds(request)`); the **algebra** that serves it was
settled at the 2026-07-26 review, and is what this plan is shaped around.

**Scope in one line:** the request-side vocabulary in `domain.py` (`SnappedAxis`, `SelectionDomain`
over a `SelectableAxis` union), **one resolution verb** — `ground(request, against)`, the
shape-correspondence computation ADR-0001 states — over **one axis operation**, `Axis.clip(bounds)`,
plus the native step `RollingAxis` needs to answer it; the Open-Meteo leaf then *declares geometry and calls `ground`
twice* instead of carrying snapped-mode code. Zero changes to `Selection`, `Capability`, `Arbiter`,
`Reservoir`, Gateway, or the MCP edge; one change in sampling (`_aligned_offsets` reports *why* a
crop is impossible).

**The leaf owns no snap arithmetic.** Every operation the mode needs — clamp to bounds, floor to the
resolver's own ticks, decline an axis with no cells, crop the values that came with a wider answer
— is one call against declared geometry. That is the property that makes 011's second provider a
declaration and 006's `quantize` a sibling of the same verb rather than a copy.

## Boundaries involved

| Boundary | Owner | What m4 does to it |
|---|---|---|
| `Domain` / axis surface (`manifold/domain.py`) | [ADR-0002](../../adr/0002-data-model.md) | Adds `SnappedAxis` (a `ContinuousAxis` subclass — decision 1), `SelectableAxis`, `SelectionDomain`, the module-level `ground` (decision 6), and **`clip` on the `Axis` base** (decision 7) — the one recorded-decision amendment m4 carries, widening the ADR's *universal axis* surface beyond set-algebra. The **domain** surface is untouched: resolution is a function, because being a request is a property of some representations only ([#42](../../concerns.md#42-two-request-representations-so-resolution-cannot-be-a-method)). Every axis kind implements `clip`; `ContinuousAxis` gains the docstring line naming its new subclass, mirroring `IntervalAxis`'s existing `VantageAxis` line. |
| Admission (`Capability.serves` → per-axis `matches`) | [ADR-0004](../../adr/0004-producer-resolution-and-capability.md) | **No code change** — `SnappedAxis.matches` (intersection) rides the existing request-side per-axis gate, exactly the `VantageAxis` precedent. Pinned by tests. |
| Arbiter | ADR-0004 | **Untouched in code.** Admission is single-winner-per-parameter, wholesale (#13 scoped position). Its multi-winner `_assemble` domain-equality check is *behaviourally* touched — see fact 9. |
| Calculator (`nodes/calculator.py`) | ADR-0004 | **Untouched.** It forwards `selection.domain` verbatim to its scoped Arbiter and takes the answer domain from the kernel's `cov.domain` (`wind_from_uv` returns it unchanged), so a snapped Selection rides through with no dispatch. It is, however, the v1 source of a *second fetch* per request (fact 9). |
| Open-Meteo leaf (`nodes/providers/open_meteo.py`) | [edge/provider.md](../../edge/provider.md) | Gains **no mode branch**, and *loses* code: `project` grounds the request against the geometry the leaf declares, then grounds it again against the delivered records and crops to that. Both modes take the same path (decision 9). **Revised 2026-08-02:** that code is *extracted*, not deleted — it becomes `TimelineProvider` in `providers/timeline.py`, and the file reduces to an `OpenMeteoProbe` plus its declarations (decision 12). |
| Provider shape (`nodes/providers/timeline.py`) | [edge/provider.md](../../edge/provider.md) | **Added 2026-08-02:** gains the verbs to match its existing nouns — `TimelineProvider` (the `Provider` implementation), the `TimelineProbe` `Protocol`, `TimelineDelivery`, and `TapTable`. Owns both `ground` calls, `agreed_geometry`, unit verification, `decode`, Z grouping, capability construction, provenance stamping, and the crop (decision 12). |
| Declared T geometry (`manifold/cadence.py`, `nodes/providers/timeline.py`) | [ADR-0003](../../adr/0003-provenance-and-origin.md), [edge/provider.md](../../edge/provider.md) | `RollingAxis` gains the **native series step** and the `clip` that materialises its live window into the lattice its series arrives on; the provider shape (`PointSeriesTap`) is where that step is declared (decision 8). `CadenceDef` is untouched — it times runs, it does not shape series. |
| Reservoir | [architecture §Reservoir](../../architecture.md#reservoir) | **Untouched** (pass-through pre-006). |
| MCP edge (`api/mcp_app.py`), Gateway | [architecture §Contract surfaces](../../architecture.md#contract-surfaces) | **Untouched** — m4 is product-invisible; the edge migrates to `SelectionDomain` at 003c. |
| Sampling engine (`manifold/sampling.py`) | ADR-0002 | **Newly load-bearing**: `resample`'s aligned crop is how the leaf trims values to the grounded answer, in both modes — no index math in any leaf. One code change: `_aligned_offsets` splits its single `None` outcome into *off-phase or different step* (still `NotImplementedError`, [#21](../../concerns.md#21-serves-extent-vs-project-crop-ability)) and *the target runs past the source* (a diagnosable shortfall — decision 9). |

## Facts that shape the implementation (verified 2026-07-25, re-read against code 2026-07-26)

1. **Admission needs no new code.** `FootprintCapability.serves` calls
   `footprint.matches(requested)`; `FootprintDomain.matches` requires the *request* to be
   `Separable` (structural, `runtime_checkable`) and folds `requested.axis(n).matches(declared)`
   per axis (`domain.py`). `SelectionDomain` exposing `axis()` is therefore admissible the moment
   it exists, and `SnappedAxis.matches` = intersection is the whole mode-dependence. `Interval`
   comparisons are boundary-inclusive (`<=` both ways in `contains`/`intersects`), so a request
   touching the window edge admits and yields a single tick.
2. **`Selection.domain` is already typed base `Domain`** (`manifold/core.py`) — no `Selection`
   change; internal store-shaped `GridDomain` Selections stay legal forever (ADR-0002 as amended).
3. **The normalizer already validates hourly regularity and array lengths**
   (`OpenMeteoNormalizer.normalize`: `tick != times[0] + HOURLY_STEP * i` → `RuntimeFailure`;
   per-var length checks). Assembly adds no vendor-shape validation of its own — the requested bounds
   are applied by clipping, not by checking (decision 7).
4. **The leaf's declared window and its vendor series share one lattice, by construction**:
   `CadenceDef.anchor` floors to Δ = 1 h (`max_lead` = 16 d), so the rolling window's edges are
   whole hours — the phase the vendor's hourly series lands on. `RollingAxis.clip`
   (decision 8) therefore materialises the lattice the answer actually arrives on — same phase, same
   step, and **`cellular=True`, as the normalizer already builds the delivered T axis** — which is what
   makes grounding *before* the fetch and *after* it agree on ticks. A provider whose declared window and
   delivered series disagreed on phase would ground to two different lattices and the crop would
   decline loudly rather than silently mis-index (decision 9) — the honest failure for a
   mis-declared provider, and the parity harness's job to catch.
5. **Two clock reads per snapped request are benign by design**: `RollingAxis.extent` reads it when
   the leaf grounds pre-fetch, and the existing post-fetch read stamps provenance. The answer is
   clipped to the *requested bounds* (fixed), never to the racy window, so a window that rolls
   between admission and fetch at worst trims the answer — except the raced-empty case, where
   `clip` finds no overlap at all and declines (decision 7).
6. **All existing `GridDomain` construction sites keep working**: the edge (`build_selection`),
   fakes (`sample_lattice`, `point_timeline_domain`), and the normalizer build `GridDomain`s;
   none is touched.
7. **`_forecast_request` / `_assemble` are module-level functions with exactly one call site each**
   — `OpenMeteoProvider.project`. **Corrected 2026-07-26:** no test calls either directly (every
   leaf test goes through `provider.project`; `test_selection_maps_to_forecast_request` asserts on
   the *captured transport request*, not on the function). A signature change therefore touches
   `project` and nothing else — no test call sites to update.
8. **No re-export layer**: `manifold/__init__.py` is docstring-only; consumers import from
   `manifold.domain` directly. New types need no export wiring.
9. **Multi-winner requests already exist in v1, and snapped makes their domains divergence-prone**
   (found 2026-07-26; the reason decision 11 exists). The shipped profile answers a mixed request
   from **two** producers — the Open-Meteo Producer for its direct parameters and the wind
   `Calculator` for `wind_speed`/`wind_direction` — and the Calculator resolves through its own
   scoped Arbiter, issuing a **second, independent vendor fetch** (`test_forecast_hourly_e2e_and_refetch`
   pins `route.call_count == 4` for two requests). That lands in `Arbiter._assemble`, which raises
   `RuntimeFailure("closed-projection invariant broken: winner domains differ")` on `cov.domain !=
   domain` (`arbiter.py`). Under **enumerable** requests divergence is impossible — both winners
   assemble onto `selection.domain`. Under **snapped** each answer's T axis is derived from its own
   vendor response, so the two diverge if the window rolls between the fetches (narrow: `Metronome`
   floors `now()` to the hour, so only an hour boundary crossing moves it) or if the vendor returns
   different lengths for two identical calls. This is **not** the "second provider with diverging
   reach" case the ticket defers — it is live in the current single-provider profile.
10. **`resample` is the only aligned-crop implementation, and m4 makes it reachable.** Today its
    sole caller is `CoverageRecord.project` (`coverage.py`), which no request path invokes; m4 calls
    it from leaf assembly (decision 9). Two facts shape that: its first guard rejects a
    non-`EnumerableDomain` selection domain — fine, because the crop target is always the
    *grounded* domain, never the request — and `_aligned_offsets` returns a single `None` for two
    unrelated situations (source and target off-phase or on different steps; target extending past
    the source's end). Only the first is genuinely unimplemented, so m4 splits them.
11. **`pyright` runs in standard mode** over `src` and `tests` (`pyproject.toml`, no
    `typeCheckingMode` override) with no `# type: ignore` budget beyond the existing
    `Interval`-variance suppressions — so every new type must narrow structurally, not by assertion
    (decision 4a).

## Design decisions

The align (2026-07-25) settled the **mode**: what a snapped request says and who resolves it
(decisions 1–5). The 2026-07-26 review settled the **algebra** that serves it (decisions 6–10): one
verb a leaf calls against the geometry it declares, instead of every leaf growing mode code. Decisions of record live in the ticket; these are their implementation-binding
forms.

1. **`SnappedAxis` is `ContinuousAxis` with intersective `matches` — temporal-only, validated.**
   **Hierarchy refined 2026-07-26** (the align said "a *sibling* of `ContinuousAxis`"; it is a
   **subclass**, which satisfies every constraint the align actually stated and adds none). The
   pattern is ADR-0002's own, one level down: `IntervalAxis` is described there as *"the base of the
   request `VantageAxis` (which only overrides `matches`)"* — `SnappedAxis : ContinuousAxis` is the
   exact dual of `VantageAxis : IntervalAxis`, span-shaped instead of cell-shaped. So the
   request-side aperture types now form one documented family rather than two unrelated mintings.

   ```python
   @dataclass(frozen=True)
   class SnappedAxis(ContinuousAxis):
       interval: Interval[datetime]          # narrowed from the base's bare `Interval`

       def __post_init__(self) -> None: ...  # aware-datetime + ordering validation
       def matches(self, declared: Axis) -> bool:
           return self.interval.intersects(declared.extent)
   ```

   - **Inherits** `name`, the `interval` field, and `extent` (which already returns the interval —
     no override needed, so decision 1's old "`extent` returns `bounds`" clause disappears).
   - **Narrows** the field to `Interval[datetime]`. **Verified 2026-07-26 with the project's own
     `pyright`** (standard mode, scratch probe): narrowing an inherited frozen-dataclass field
     raises no `reportIncompatibleVariableOverride`, *and* `SnappedAxis(name, Interval(1.0, 2.0))`
     is a type error. The temporal-only rule is therefore **static**, not merely runtime — strictly
     better than the sibling shape, which could only check it in `__post_init__`.
   - **Keeps** the runtime `__post_init__`: `ValueError` unless both edges are timezone-**aware**
     `datetime`s with `lower <= upper` (tz-awareness is invisible to the type system, and equal
     bounds stay legal — the "current conditions" instant).
   - **The field is `interval`, not `bounds`.** A frozen-dataclass subclass cannot rename an
     inherited field, and `VantageAxis` sets the precedent of carrying the role in the docstring
     rather than the field name. "Bounds" remains the *prose* term throughout the ticket, ADR-0002,
     and the glossary; `.interval` is how code spells it.
   - **Not an `EnumerableAxis`** — unchanged and load-bearing: `ContinuousAxis` is not one either,
     so the "never claims enumerability" invariant the align insisted on is inherited, not restated.
   - **Safe against dispatch:** `isinstance(x, ContinuousAxis)` is now true for a `SnappedAxis`.
     Verified — **no production code dispatches on `ContinuousAxis`** (the only isinstance uses are
     `RegularAxis` in `sampling.py` and test assertions on *footprint* axes, which are never
     snapped). `ContinuousAxis`'s docstring gains the "base of the request `SnappedAxis`" line,
     mirroring `IntervalAxis`'s existing `VantageAxis` line — a one-line doc edit, and the same edit
     ADR-0002 already documents for the pair.
2. **`SelectableAxis = RegularAxis | VantageAxis | SnappedAxis`** (a `type` alias in
   `domain.py`). Plain `IntervalAxis` (exact-layer Z addressing) joins the union when alias
   desugaring gets its driver (roadmap Phase 4) — not now.
3. **`SelectionDomain`** is a frozen dataclass `(axes: Mapping[AxisName, SelectableAxis])`,
   direct `Domain` subclass (never `EnumerableDomain`), validated by the existing
   `_validate_four_axes`; `axis(name)` returns the member (structurally `Separable`);
   `matches(other)` composes per-axis over a `Separable` other exactly like
   `FootprintDomain.matches` (total: `False` for non-separable), `intersect` raises
   `NotImplementedError` like its peers. Nothing anywhere narrows `Selection.domain` to it.
   **Fold duplication is deliberate (decided 2026-07-26):** this makes a *third* verbatim copy of
   the per-axis fold (`GridDomain.matches`, `FootprintDomain.matches`). Extracting the shared helper
   touches two load-bearing types for a three-line fold that this mode does not change, so it is a
   recorded `/denoise` follow-up rather than m4 work. Note the receiver direction is *declared*-side, so
   `SelectionDomain.matches` is **unreachable in v1** (a `SelectionDomain` is never a
   `Capability`'s domain); it exists to satisfy the `Domain` ABC and is pinned only for totality.
4. **The leaf serves one snapped placement — and it *declares* that, rather than guarding it.**
   Snapped T resolves here; snapped X/Y does not. But the leaf states this the way it states
   everything else about itself: its footprint declares a T that clips to a lattice (`RollingAxis` —
   decision 8) and X/Y that clip to spans, which temporal bounds do not meet in the first place.
   `ground` keeps what the answering axis clips to when that
   has cells and declines when it does not (decisions 6–7), so *"this leaf resolves a snapped T and
   nothing else"* is a **consequence of the declaration**, not a hand-written gate. No shape-inspecting
   helper exists, and [011](../../tickets/01-0120-twc-provider.md)'s second provider inherits
   the behaviour by declaring its own geometry.
   Two things this drops on purpose: the *non-snapped-T-inside-a-`SelectionDomain`* rejection (it was
   never unservable — an all-enumerable `SelectionDomain` is an exact request wearing the
   request-side type, and `ground` passes it straight through), and any leaf-side opinion about which
   *enumerable* kind sits on X/Y/Z (a `VantageAxis` on X is read as `extent.lower`, exactly as in a
   `GridDomain` today — pre-existing behaviour, unchanged).
   **4a — the leaf narrows once, where it must.** `ground` returns an `EnumerableDomain`, so nothing
   downstream needs `assert isinstance` to recover enumerability (fact 11). The leaf still narrows to
   `Separable` at the one place that reads per-axis coordinates to build `latitude=`/`longitude=`
   query params — the same check it performs on requests today, now applied to the grounded answer.
5. **Fetch bounds are a ground, not arithmetic.** `project` grounds the request against the leaf's
   own declared geometry and hands the *grounded* domain to the request mapper:

   ```python
   wanted = agreed_geometry(ground(selection.domain, fp) for fp in footprints_of(taps))
   request = _forecast_request(wanted, taps)     # reads the resolved T extent and the X/Y point
   ```

   Four things the mode needs are all one `clip` of the rolling axis, so none of them is written
   here: the clamp to the live window (the materialised lattice **is** the window), the floor of both
   bounds onto the resolver's own ticks, end-inclusivity (*last tick ≤ end*), and the raced-empty decline. The
   mapper therefore holds no `floor_to`, no `HOURLY_STEP`, no T-mode branch and no clock — it maps an
   already-resolved geometry onto vendor query params, which is all it was ever for. The two clock
   reads stay as fact 5 describes; the pre-fetch one happens inside `RollingAxis.extent`, where
   ADR-0003 already put the build-time `Clock`.
6. **`ground` is the shape-correspondence computation, and it is a function in `manifold/domain.py`.**
   ADR-0001 says an answer mirrors its question's shape; `ground` is that sentence as one operation:

   ```python
   def ground(request: Domain, against: Domain) -> EnumerableDomain:
       """The answer geometry `request` asks for, resolved against `against`'s geometry."""
   ```

   - **Returns `EnumerableDomain`, not `GridDomain`.** What every caller needs is *indexability* — a
     `Coverage` domain, a crop target, a storable unit. Which enumerable representation satisfies it
     is the resolver's business, so an irregular-point geometry later needs no signature change.
   - **A function, not a method** (decided 2026-08-03). Callers hold `Selection.domain`, typed base
     `Domain` (fact 2), and must not branch on representation to learn whether resolution is needed —
     so exactly one dispatch exists, and it lives in the module that owns representations. It has
     three arms: a `SelectionDomain` resolves; an `EnumerableDomain` **is returned unchanged**, since
     an exact request is already its own answer, and *that identity is what collapses the leaf's mode
     branch* (decision 9); a declared geometry is a `ValueError`, because a footprint is what requests
     ground *against*. A base-`Domain` method would instead make every representation that is not a
     request carry a stub — including test doubles — and each new one carry another.
     **The end-state is a method again, once the request side narrows to one representation**
     ([#42](../../concerns.md#42-two-request-representations-so-resolution-cannot-be-a-method) owns that
     path and its triggers: 006's refill, 003c, or an embedder-facing builder). m4 deliberately does
     not force it, because narrowing needs `SelectableAxis` widened and `resample`'s target restated.
   - **Takes a `Domain`, not a per-axis mapping.** What a request resolves against is always some
     node's geometry: a footprint before the fetch, a delivered `Coverage`'s domain after it, a store
     lattice at 006. One argument shape serves all three, and no caller disassembles a geometry to
     feed it.
   - **A per-axis fold, mode-dispatched by axis kind** — the ticket's non-duplication constraint,
     now on the resolution side as it already is on the admission side: enumerable members pass
     through by identity (the vantage Z cell rides exactly as today), snapped members take what the
     answering axis clips to, and 006's `ANY` will take the answering axis whole. Mode *combinations* are never code paths.
   - **`ValueError` when a member cannot resolve.** The reason a resolution fails is the caller's
     knowledge, not the algebra's: a vendor answering a foreign window and a mis-quantized store are
     different failures, reported differently, by different callers.
   - **Total, the way `matches` is total.** Resolving a snapped member requires a per-axis read of
     `against`, so a non-`Separable` answering geometry (#12's future station list) is a `ValueError`,
     never a crash — while a fully pinned request grounds against *anything*, because identity reads
     nothing. Verified against the shipped leaf: grounding is stable across its per-parameter
     footprints and across native records with **different Z cells**, because a request that pins Z
     passes it through by identity — so `agreed_geometry` (decision 10) fires only when the T lattices
     genuinely disagree, which is the case it exists for.
7. **The bounds clamp, they do not police** — `Axis.clip`, `ground`'s per-axis mechanism. A snapped
   member carries bounds and nothing else, so the **answering axis says what part of itself those
   bounds ask for**: `clip(bounds: Interval) -> Axis | None`, **abstract on the `Axis` base**. A
   clipped lattice keeps its anchor and step; the bounds decide only where it starts and stops: back
   to the tick whose *cell* contains the lower bound, forward to the last tick within the upper. A
   vendor loose with `start_hour`/`end_hour` (or a stale proxy) is therefore **trimmed, not
   rejected**, and a lattice falling short of the bounds is an **honest shorter answer** — the two
   failure modes the mode exists to stop treating as errors.
   **Abstract on the base, not a facet on some axes** (decided 2026-08-02, superseding the
   `Snappable` / `regular()` shape). Restricting an axis to bounds is plain axis algebra: it is what
   006's `quantize` needs, what any later crop needs, and it is meaningful for *every* axis kind. A
   facet would have named the caller instead of the operation, and would have made two questions
   (*can you be snapped-to?* then *hand me your lattice*) out of one. Abstract means each kind answers
   for its own geometry, `ground` holds no `isinstance` crawl, and a new axis kind must state its
   answer rather than inherit a wrong one:

   | answering axis | `clip(bounds)` |
   |---|---|
   | `RegularAxis` | the sub-lattice inside the bounds — same phase, same step, `cellular` carried through; `None` when no tick survives |
   | `IntervalAxis` / `VantageAxis` | itself when the bounds reach into its single cell, `None` otherwise — one cell is not subdivided |
   | `ContinuousAxis` (and `SnappedAxis`, inherited) | the overlapping span: a span restricted is still a span, and no cells appear from nowhere |
   | `RollingAxis` | its live window materialised as the lattice its series arrives on, then clipped (decision 8) |

   **`ground` owns enumerability; `clip` does not.** `clip` returns *whatever kind of geometry the
   restriction leaves*, because that is the honest answer to a question about axes; needing **cells**
   is a property of grounding (its return is an `EnumerableDomain`), so the one verb that needs them
   checks for them. That gives two declines with genuinely different sentences, both `ValueError` out
   of `ground` and `CapabilityMismatch` at the leaf: **`None`** — bounds and axis are disjoint, there
   is nothing to trim into (raced-empty pre-fetch, a foreign window post-fetch, and a snapped X/Y,
   whose bounds are `datetime` by type and so meet no spatial axis); **a non-enumerable part** — the
   axis has no cells to snap to (a leaf declaring T as a plain span rather than a lattice).
   This is where ADR-0002's *"only a regular axis can be snapped-to"* now lives — as a property of
   what `clip` hands back, read once, rather than as a facet the request side must interrogate first.
   Worth stating plainly, because it changes what the rule *is*: nothing in the machinery forbids a
   snapped X/Y — it stays unserved because **`SnappedAxis` is temporal by type**, so its bounds do not
   address a spatial axis at all (and, behind that, no leaf declares an enumerable X/Y either). The ADR
   sentence is amended to say that at stage 6.
   **m4 adds no coordinate-kind narrowing after all** (this revises the earlier claim that it adds
   one). The index math lands on `RegularAxis`, which is coordinate-generic: `(bound − anchor) / step`
   is a plain `float` for `timedelta`s and floats alike, and `anchor + i·step` types alike, so `clip`
   is one expression under the module's existing `# type: ignore[operator]` — no `datetime` branch,
   nothing like `sub_lattice_offset`'s `isinstance` crawl.
   [#23](../../concerns.md#23-spatial-vs-temporal-regularaxis-types) is therefore touched only as a
   *deferred* question: what a spatial user must settle is **float phase tolerance** (the reason
   `sub_lattice_offset` carries `LATTICE_TOLERANCE`), and m4's T path never meets it because
   `timedelta` arithmetic is exact. Snapped X/Y costs a tolerance policy in one expression, not a
   second `clip`.
8. **`RollingAxis` answers `clip` by materialising, which requires it to know its native step.** A
   footprint's T axis is deliberately clock-relative (`extent` = `valid_time(now())`); `clip` turns
   that live window into the lattice the series actually arrives on — anchor at `extent.lower`, the
   declared step, `cellular=True` as the delivered axis is (fact 4), and the count that fits — then
   clips *that*. Two things this pins:
   - **The series step is not the cadence.** `CadenceDef` times *runs* (Δ, latency, `max_lead`); the
     step is how densely one run samples time. They coincide at 1 h for Open-Meteo and would not for
     a 6-hourly run publishing an hourly series, so conflating them would make that provider
     undeclarable. `CadenceDef` stays untouched.
   - **The step is a declaration of the provider *shape*, and `RollingAxis` requires it.** It rides
     with the tap vocabulary in `providers/timeline.py`, where `HOURLY_STEP` already lives, and the
     footprint builder hands it to `RollingAxis` as a required field — not per-`PointSeriesTap`,
     because T is *structural* to that shape (the tap's own docstring says so) and per-parameter
     steps would let two parameters of one shape disagree about time. Required rather than optional
     so that a `RollingAxis` never invents a lattice it does not have: a provider whose series is
     genuinely irregular declares a different T axis, whose `clip` yields no cells, and is declined by
     the algebra reading that declaration.
9. **One assembly path, cropped by `resample`.** `_assemble` grounds the request against what the
   fetch actually delivered, then crops the values to the result:

   ```python
   answer = agreed_geometry(ground(selection.domain, r.domain) for r in records)  # decision 10
   served = CoverageRecord(...)                                                 # as parsed, vendor lattice
   return served if served.domain == answer else resample(served, Selection(answer, parameters))
   ```

   **Both modes take it.** For an exact request `ground` is the identity and the crop is a no-op, so
   the branch that used to exist is now an equality that happens to hold. That also replaces the old
   `len(values) == len(sel.domain)` assertion with something strictly better: the same fact, checked
   by the component that owns index math and *reported* rather than asserted
   ([#31](../../concerns.md#31-positional-alignment-is-asserted-never-checked)'s check class re-aimed at
   the answer). Provenance, parameters, and Z-relabeling are untouched.
   **`_aligned_offsets` splits its `None`,** because one value currently covers two unrelated
   situations and only one of them is unimplemented:
   - *Off-phase, or a different step* — not croppable by index arithmetic at all. Stays
     `NotImplementedError`; stays [#21](../../concerns.md#21-serves-extent-vs-project-crop-ability)'s.
   - *The target runs past the source's end* — a **shortfall**, and fully diagnosable: the crop is
     well-defined over the overlap and short by a known count. The leaf reads it as *a vendor
     delivered less than it declared*. Filling that tail as `present=False` with `nan` values — the
     padding the presence mask already exists to describe — is the named site at
     [#30](../../concerns.md#30-response-membership-under-runtime-degraded-fallback), not m4's work.
10. **Native records must agree on every axis the request pinned or snapped.** (Headline corrected
    2026-08-02 — it previously read *"the axes the request left open"*, which inverts the body: an axis
    left open is precisely the licence to differ.) `_assemble` folds many native
    records into one co-domained `Coverage`, and that is *required*, not incidental: ADR-0001's
    closure gives one `project` one answer geometry, and the only licence for a multi-domain answer
    is an axis the request left to the producer entirely — 006's `ANY`, which does not exist yet.
    So every axis the request pins or snaps must ground identically across records. m4 states that
    law as a named fold that raises, instead of implicitly trusting the first record — and puts it in
    `domain.py` beside `ground`, **not** in the leaf: the law binds every producer that folds records
    (011's second provider included), and 006 is where it is *lifted* for an `ANY` axis, so one module
    owns both the rule and its exception. `ValueError` like `ground`, translated by the caller.
    **The multi-domain carrier is 006's and is deliberately not minted here.** Wrapping records in a
    carrier, for a request that asked for a single geometry, only defers the fold to the caller — and
    every v1 caller wants it folded (the Arbiter's equality check, the Calculator's kernel, 006's
    refill). When `ANY` lands, the carrier arrives with the axis that justifies it.
11. **Winner-domain divergence is recorded and pinned, not engineered around (decided 2026-07-26).**
   Fact 9's case — two winners, two independent fetches, two vendor-derived T axes — stays a loud
   `RuntimeFailure` from the Arbiter's existing equality check. m4 changes **no** Arbiter code and
   adds **no** fold. What it adds is honesty: a deterministic test feeding two divergent canned
   responses to the two producers and asserting the loud failure (stage 6), the corrected
   attribution in Scope limits, and a **Race** entry in
   [#40](../../concerns.md#40-composing-servable-requests-at-the-embedding-edge)'s Arm-1 table.
   Rejected alternatives and why: *freezing one window per request* needs a per-request context the
   architecture does not have (the `Clock` is a build-time dependency, ADR-0003) and still would not
   cover vendor-length divergence; *folding winner domains to a common lattice* is a per-cell
   reconciler ([#28](../../concerns.md), out of scope by the ticket). The exposure is real but starts
   at **003c** (m4 is product-invisible), and [006](../../tickets/01-0115-retentive-store-freshness.md)'s
   retention collapses the second fetch — so the owner is 003c's landing, recorded there and at
   [#30](../../concerns.md#30-response-membership-under-runtime-degraded-fallback).
12. **The leaf splits into a shape wrapper and a vendor `Probe` (decided at the 2026-08-02 align;
   folded into m4).** Decision 4 already made the leaf *declare* rather than gate; this finishes the
   thought by observing that two independent things vary — the **geometry family** (a point plus an
   hourly series) and the **vendor** (endpoint, auth, query encoding, envelope keys, variable names) —
   and giving each its own type. `TimelineProvider` implements `Provider` and owns everything
   algebraic; `TimelineProbe` is an injected `Protocol` — inheriting nothing, the `Transport`
   precedent — that builds one request and parses one envelope.
   **Why m4 and not after:** stages 4–5 are rewriting exactly this code. Landing them in
   `open_meteo.py` and then extracting means writing the same edit twice, with a stale Edge record in
   between.
   **Why the shape owns the geometry:** the repo already ruled this — `timeline.py` holds
   `PointSeriesTap`, whose docstring says *"X/Y and T are structural to the shape"*, and decision 8
   puts the series step there for the same reason. The shape module had the nouns and none of the
   verbs.
   **The seam is typed by value, not by manifold.** A Probe speaks `Interval`, `RegularAxis`,
   `ParameterData`, `ParameterId`, `VendorVar` and never `Domain`, `Selection`, `Coverage`,
   `Capability`, `Provenance`, or `Clock` — each exclusion removing a way to be wrong rather than
   warning against it (a Probe with no `Clock` cannot mis-stamp provenance; one that never narrows a
   `Domain` cannot misclassify a shape error as a fault). Guardable by an import-direction test
   modelled on `test_parity_reader_guard.py`.
   `TimelineDelivery` is **vendor-keyed and pre-decode** — `(valid_time, series, reported_units)` —
   because the vendor↔parameter map is many-to-many (`_WIND_VARS` feeds both `wind_u` and `wind_v`),
   so no `ParameterId` key is truthful before `decode`. It is a deliberate structural twin of parity's
   `ReferenceTimeline` and **must never be unified with it**: `parity.comparison` imports no
   Meteoscape code precisely so readers stay guard-clean.
   **What the split enables but does not deliver.** The wrapper's constructor arguments — `taps`,
   `step`, `cadence` — are **per-offering** facts, and m4 passes them as the leaf's module constants,
   which is the honest v1 state at one offering per provider. It makes an offering-parameterized leaf
   a private table keyed by `spec.name` rather than a rewrite, but the query's missing vendor model
   token stays missing, so a second Open-Meteo offering is still unbuildable after this lands →
   [#20](../../concerns.md#20-provider-multi-resolution-offerings-offering-aware-selection).
   **Costs accepted:** m4's blast radius widens to `MANIFEST.build` and every leaf test's construction
   site, `Clock` leaves the vendor object entirely, and the shape abstraction is extracted from **one**
   instance with 011 as the only confirming case and not yet written. Full contract:
   [edge/provider.md](../../edge/provider.md).

## Code shapes

### `manifold/domain.py`

```python
class Axis(ABC):
    # name / extent / matches unchanged

    @abstractmethod
    def clip(self, bounds: Interval) -> Axis | None:
        """The part of me within `bounds` — `None` when none of me is.

        Pure axis algebra: what comes back is whatever the restriction leaves (a span stays a span,
        a lattice stays a lattice at its own phase, a clock-relative window materialises). Callers
        that need cells check for them.
        """


@dataclass(frozen=True)
class RegularAxis(EnumerableAxis):
    def clip(self, bounds: Interval) -> RegularAxis | None:
        # A cellular tick owns the span that follows it, so a bound inside a cell keeps that cell;
        # an instant tick is kept only when the bounds contain the tick itself.
        low = (bounds.lower - self.anchor) / self.step
        first = max(0, floor(low) if self.cellular else ceil(low))
        last = min(self.count - 1, floor((bounds.upper - self.anchor) / self.step))
        if first > last:
            return None
        return RegularAxis(self.name, self.anchor + first * self.step, self.step,
                           last - first + 1, self.cellular)


@dataclass(frozen=True)
class IntervalAxis(EnumerableAxis):
    def clip(self, bounds: Interval) -> IntervalAxis | None:
        """One cell is not subdivided: it survives whole, or not at all."""
        return self if self.interval.intersects(bounds) else None


@dataclass(frozen=True)
class Interval[C: (float, datetime)]:
    # contains / intersects unchanged
    def intersection(self, other: Interval[C]) -> Interval[C] | None:
        """The span both cover — `None` when they do not meet."""


@dataclass(frozen=True)
class ContinuousAxis(Axis):
    def clip(self, bounds: Interval) -> ContinuousAxis | None:
        """A span restricted is still a span — no cells appear from nowhere."""
        overlap = self.extent.intersection(bounds)
        return None if overlap is None else ContinuousAxis(self.name, overlap)


class Domain(ABC):
    # matches / intersect unchanged

    @abstractmethod
    def ground(self, against: Domain) -> EnumerableDomain:
        """The answer geometry this domain asks for, resolved against `against`'s geometry.

        Shape-correspondence (ADR-0001) as one operation: pinned axes pass through, snapped axes
        adopt the answering lattice within their bounds. `ValueError` when a member cannot resolve —
        why that matters is the caller's knowledge, not this layer's.
        """


@dataclass(frozen=True)
class GridDomain(EnumerableDomain):
    # ...
    def ground(self, against: Domain) -> EnumerableDomain:
        return self          # an exact request is already its own answer


@dataclass(frozen=True)
class SnappedAxis(ContinuousAxis):
    """Bounds-only request axis: the resolver's grid supplies anchor and step (ADR-0002).

    `ContinuousAxis` with intersective `matches` — the span-shaped dual of `VantageAxis`.
    Temporal-only: the narrowed `interval` makes a float-coordinate snapped axis a type error.
    """
    interval: Interval[datetime]

    def __post_init__(self) -> None:
        # tz-awareness is invisible to the type system; ordering is a value rule
        for edge in (self.interval.lower, self.interval.upper):
            if edge.tzinfo is None:
                raise ValueError(...)
        if self.interval.upper < self.interval.lower:
            raise ValueError(...)

    def matches(self, declared: Axis) -> bool:
        return self.interval.intersects(declared.extent)   # type: ignore[arg-type]

    # `name`, `extent` and `clip` inherited unchanged — a snapped axis is asked *for* nothing;
    # it is the bounds another axis is clipped to.


type SelectableAxis = RegularAxis | VantageAxis | SnappedAxis


@dataclass(frozen=True)
class SelectionDomain(Domain):
    """Request-side representation: SelectableAxis per axis; structurally Separable,
    never enumerable, never nominally narrowed-to (Selection.domain stays Domain)."""
    axes: Mapping[AxisName, SelectableAxis]

    def __post_init__(self) -> None: _validate_four_axes(self.axes)
    def matches(self, other: Domain) -> bool: ...   # per-axis like FootprintDomain; total
    def intersect(self, other: Domain) -> Domain: raise NotImplementedError
    def axis(self, name: AxisName) -> SelectableAxis: return self.axes[name]

    def ground(self, against: Domain) -> EnumerableDomain:
        """Pinned members pass through; a snapped member takes what the answering axis clips to."""
        answering = as_separable(against)
        if answering is None:
            raise ValueError("a request grounds only against separable geometry")
        axes: dict[AxisName, EnumerableAxis] = {}
        for name in AXIS_ORDER:
            member = self.axes[name]
            if not isinstance(member, SnappedAxis):
                axes[name] = member                       # pinned: the ask is the answer
                continue
            part = answering.axis(name).clip(member.interval)
            if part is None:
                raise ValueError(f"no {name.value} within the requested bounds")
            if not isinstance(part, EnumerableAxis):      # grounding is what needs cells
                raise ValueError(f"a snapped {name.value} needs cells; the answering axis has none")
            axes[name] = part
        return GridDomain(axes=axes)


def agreed_geometry(grounded: Iterable[EnumerableDomain]) -> EnumerableDomain:
    """The single geometry a set of resolutions agree on — `ValueError` when they disagree.

    One `project` answers with one geometry (ADR-0001): several native records, or several declared
    footprints, may only differ on an axis the request left entirely to the producer — which is 006's
    `ANY`, and does not exist yet.
    """
```

Placement: `clip` on each axis beside that axis's `matches`, the abstract one on `Axis`;
`Interval.intersection` beside `intersects`; `SnappedAxis` immediately after
`ContinuousAxis` — required, not cosmetic, since it subclasses it, and it puts the pair on the page
exactly as `IntervalAxis` / `VantageAxis` already sit; `SelectionDomain` after `FootprintDomain`,
the alias between them.

### `manifold/cadence.py`

`RollingAxis` gains a required `step: timedelta`, so a footprint's clock-relative T window can answer
a snapped request (decision 8). **Four construction sites** take the new field — `_build_footprints`
(the leaf, from `timeline.HOURLY_STEP`), `fakes.footprint_capability`, and two in `test_domain.py` —
all of them one argument wider, none of them structural:

```python
def clip(self, bounds: Interval) -> RegularAxis | None:
    """A clock-relative window resolves to the lattice its series arrives on, then to the bounds."""
    window = self.extent          # the one clock read
    return RegularAxis(self.name, window.lower, self.step,
                       (window.upper - window.lower) // self.step + 1, cellular=True).clip(bounds)
```

### `nodes/providers/open_meteo.py` → `providers/timeline.py`

The snapped-mode code is *the two `ground` calls*, and neither knows the mode. Per decision 12 they
land on `TimelineProvider`, not on the vendor leaf:

```python
# project(): resolve what the request asks of this provider, against what this provider declares
wanted = agreed_geometry(ground(selection.domain, fp) for fp in footprints_of(taps))
request = _forecast_request(wanted, taps)      # T extent + the X/Y point → query params
...
# _assemble(): resolve it again, now against what the fetch delivered
answer = agreed_geometry(ground(selection.domain, r.domain) for r in records)
```

**The same fold at both ends** (decision 10). The leaf's footprints are per-parameter
(`_build_footprints`, differing only in Z), so *which* declared geometry resolves the request is a
real question, not a detail: one fetch can only answer one geometry, so the requested taps must
ground alike or the request is declined. Post-fetch, the delivered records must do the same. Both
`ground` call sites translate `ValueError` → `CapabilityMismatch`.

What leaves the file: the mode branch, the `floor_to` / `HOURLY_STEP` arithmetic and the `datetime`
re-check on request bounds (the axis types guarantee them now), the raced-empty guard (`clip` decides
it), the `GridDomain`-only assembly guard, and the `len(values) == len(sel.domain)` assertion
(`resample` owns it).

**Revised 2026-08-02 (decision 12): it leaves the file entirely, not just the function.** Both `ground`
calls, the fold, the crop, unit verification, `decode`, Z grouping, capability construction, and
provenance stamping move to `TimelineProvider` in `providers/timeline.py`. What remains here is a
`TimelineProbe` — `BASE_URL`, the tap table, `CADENCE`, one query builder, one envelope parse — plus a
`MANIFEST.build` that composes the two. So the sketch above is the *wrapper's* `project`, not this
file's.

**This supersedes fact 7's "no test call sites move."** That was true of a signature change; it is
false of an extraction. `MANIFEST.build` and every leaf test's construction site move, the leaf tests
address `TimelineProvider` with an injected Probe (still mocking the **`Transport`**, never the Probe
— [edge/provider.md](../../edge/provider.md)), and the deterministic assertions themselves are unchanged,
which is the stage's real proof.

`agreed_geometry` is **not** in this file: it lives in `manifold/domain.py` beside `ground`
(decision 10). The law it enforces is not provider-specific — it binds any producer folding several
native records into one answer, [011](../../tickets/01-0120-twc-provider.md)'s second provider
included — and [006](../../tickets/01-0115-retentive-store-freshness.md) *lifts* it on `ANY` axes, so the law
and its exception belong to one module. The leaf imports it and translates its `ValueError`.

### `tests/deterministic/fakes.py`

One new helper, mirroring `point_timeline_domain`:
`snapped_point_domain(*, lon=1.0, lat=2.0, start, end) -> SelectionDomain` (X/Y count-1
`RegularAxis` at step `1.0`, Z `VantageAxis(Interval(0.0, 10.0))`, T `SnappedAxis`).

**Verified 2026-07-26 — this is the edge's own shape**, not an invented one: `build_selection`
(`api/mcp_app.py`) builds exactly `RegularAxis(X, lon, 1.0, 1, False)`,
`RegularAxis(Y, lat, 1.0, 1, False)`, `VantageAxis(Z, Interval(0.0, 10.0))`, differing only in T.
So the fake is the snapped counterpart of the production request, and 003c's edge migration is a
T-axis swap on a shape already pinned. Also verified: `serialize_coverage` requires a `GridDomain`
Coverage domain — `ground` builds exactly that from a `SelectionDomain` (the *declared* return is the
wider `EnumerableDomain`, decision 6), so the snapped answer serializes with no edge change.

## Flows

**Snapped request (engine-level, v1 wiring):** test/embedder builds
`Selection(SelectionDomain(..., T=SnappedAxis(bounds)), params)` → `Gateway.resolve` →
`Arbiter.project`: per-parameter `serves` → `FootprintDomain.matches` → per-axis gate (T
intersects the live `RollingAxis` window; X/Y containment; Z vantage as today) → single winner →
pass-through `Reservoir` → leaf: `ground` against its declared geometry gives the fetch window
(`bounds` clipped to the live rolling lattice) → normalizer (existing semantic + regularity
validation) → `ground` again against the delivered records → `resample` crops to it →
`CoverageRecord` on {request X/Y/Z, delivered T within bounds}. Wider vendor data is trimmed;
shorter vendor data is a shorter honest answer.

**Snapped request spanning a Calculator (the shipped profile's shape — fact 9):** a request mixing
direct and derived parameters produces **two** winners → `Arbiter._assemble` → the Open-Meteo
Producer and the wind `Calculator` each `project` the same snapped Selection → the Calculator
forwards it verbatim to its scoped Arbiter → the same leaf, a **second independent fetch** →
`wind_from_uv` returns `cov.domain` unchanged → two `CoverageRecord`s whose domains must compare
equal at `arbiter.py`'s closed-projection check. Equal when both fetches see the same window and
the vendor answers identically (always, under a canned transport); divergent otherwise → whole-request
`RuntimeFailure` (decision 11).

**Enumerable request:** every path byte-identical to today (edge included).

**Failure surface (complete).** Every leaf-side decline is one `ValueError` out of `ground`,
translated at the call site — which is why the list is short:

- No producer intersects the bounds → `CapabilityMismatch` at the Arbiter (today's message).
- **Snapped against an axis that clips to no cells** (a leaf declaring T as a plain span) →
  `ground` declines →
  `CapabilityMismatch`, pre-fetch. This is the whole of the old "malformed shape" class; an
  all-enumerable `SelectionDomain` is now simply served (decision 4).
- **Nothing left after the clip** — the window rolled past the bounds before the fetch (raced-empty),
  the delivered series is disjoint from them, or the bounds address a different coordinate kind than
  the axis they ask of (a **snapped X/Y**: temporal bounds never meet a spatial axis, so admission
  already declines it and `ground` says the same thing) → `CapabilityMismatch`, pre- and post-fetch
  respectively.
- **Requested taps, or delivered records, that ground differently** → `CapabilityMismatch`
  (decision 10): one fetch answers one geometry.
- Vendor garbage — gapped or non-hourly times, length mismatch, missing parameters →
  `RuntimeFailure` (normalizer, unchanged). A vendor that delivered *fewer* ticks than it declared is
  **not** garbage: it is the shortfall crop (decision 9).
- **Divergent winner domains across the two fetches of one request → `RuntimeFailure`** at the
  Arbiter's existing closed-projection check (fact 9 / decision 11 — pinned, not introduced here).

`BadRequest` is unreachable (no edge change). No new error categories, no logging changes
([#14](../../concerns.md#14-resolution-trace-and-observability) unowned here).

## Implementation stages

Each stage ends with `uv run ruff check . && uv run ruff format --check . && uv run pyright &&
uv run pytest` green.

1. **`SnappedAxis`** — RED (`tests/deterministic/manifold/test_domain.py`): runtime validation
   (`ValueError` on a naive-datetime or reversed interval; equal bounds legal — the "current
   conditions" instant). **A float interval is no longer a runtime test** — decision 1 makes it a
   *type* error, so it is pinned by `pyright` in CI, not by `pytest`; asserting it at runtime would
   require constructing the unconstructible. `extent` needs no test of its own beyond one identity
   assertion (it is `ContinuousAxis`'s, inherited): the behavioural pin is `matches` — intersection
   (overlap admits, disjoint rejects, boundary-touch admits, containment *not* required) against
   `ContinuousAxis` and `RollingAxis` declared extents (`fakes.STOPPED`) — plus one test that a
   `SnappedAxis` does **not** satisfy `isinstance(x, EnumerableAxis)`, which is now an inherited
   property rather than a stated one and therefore worth pinning explicitly. GREEN: the class.
2. **`SelectionDomain` + admission pinning** — RED: four-axes validation; `axis()`;
   `matches` totality (non-separable → `False`); then the composition tests expected to pass
   with *no code beyond stage 1–2 types* — `FootprintDomain.matches(selection_domain)` admits
   an overlapping snapped T and rejects no-overlap, X/Y containment still gates, and
   `Arbiter.project` with a `FakeProvider` (`fakes.footprint_capability`) admits a snapped
   Selection / raises `CapabilityMismatch` on no overlap. These pins *are* the
   non-duplication proof: if any needs engine code, the shape is wrong. GREEN: the class +
   `snapped_point_domain` fake.
3. **The algebra: `clip`, `ground`, the rolling lattice** — RED in `test_domain.py` and
   `test_cadence.py`, all of it domain-level, none of it provider-shaped. `clip`, per axis kind:
   `RegularAxis` on both edges, on and off the tick, cellular flooring vs instant ceiling on the lower
   edge, `cellular` carried through, instant bounds, disjoint → `None`; `IntervalAxis` whole-or-`None`;
   `ContinuousAxis` returning a narrowed span (**the pin that a declared span has no cells to take**);
   and cross-kind intervals never meeting, so temporal bounds against a spatial axis are *disjoint*
   rather than a `TypeError` — which also removes that crash from admission's `matches`.
   Then `ground`: enumerable members through *by identity*, a snapped member taking the clipped
   lattice, `ValueError` on each of the two declines (disjoint; a part with no cells), `ValueError`
   against non-separable geometry, an enumerable request returned unchanged, and a declared geometry
   as the request declined. `RollingAxis.clip` yielding the lattice its window spans under
   `StoppedClock`, and moving when the clock does; `agreed_geometry` returning the agreed geometry and
   raising on a disagreement.
   GREEN: `Interval.intersection`, `clip` on every axis kind, `ground`, `agreed_geometry`, and
   `RollingAxis`'s required step (with the four construction sites that pass it).
4. **Leaf fetch bounds, via `ground`** — RED (`tests/deterministic/nodes/providers/test_open_meteo.py`,
   mocked transport, `StoppedClock`): bounds inside the window → `start_hour`/`end_hour` at the
   resolver's own ticks; bounds straddling both window edges → clamped to it; mid-hour bounds →
   both edges snapped inward (end-inclusivity); `bounds.upper` before the window →
   `CapabilityMismatch` with **no vendor call**; a snapped X → `CapabilityMismatch`, no vendor call.
   All assertions read the **captured transport request**, as every existing leaf test does (fact 7).
   GREEN: the `project` grounding and the request mapper's narrowed signature.
   **Revised 2026-08-02 (align): this is an *extraction* stage, not a deletion stage.** The code that
   leaves `open_meteo.py` does not vanish — it moves to `providers/timeline.py` as `TimelineProvider`,
   and what remains vendor-side becomes a `TimelineProbe`
   (`retrieve(at=point, over=window, variables=…) -> TimelineDelivery`). `open_meteo.py` keeps only
   `BASE_URL`, the tap table, `CADENCE`, one query builder, and one envelope parse; `MANIFEST.build`
   composes `TimelineProvider(probe=OpenMeteoProbe(...), taps=…, step=HOURLY_STEP, cadence=…)`.
   Same code deleted from the leaf, different destination — doing it after m4 would mean writing the
   mode into `open_meteo.py` and immediately moving it. Rationale and the full seam contract:
   [edge/provider.md](../../edge/provider.md).
5. **Assembly and crop** — RED: in `test_sampling.py` for the split (`_aligned_offsets` distinguishing
   off-phase from shortfall; `resample` cropping a longer source and reporting a target that runs
   past it), then in the leaf tests for the wiring: canned response matching the fetch window →
   Coverage on {request X/Y/Z, delivered T} with the payload passed through; response *wider* at
   either end → trimmed axis **and** trimmed values; response *shorter* → honest shorter Coverage;
   response disjoint from the bounds → `CapabilityMismatch`; two records disagreeing on T →
   `CapabilityMismatch` (decision 10); non-hourly times → `RuntimeFailure` (normalizer pin, kept).
   The enumerable-path tests must stay green **unchanged** while their implementation moves onto the
   shared path — that is the stage's real assertion. GREEN: assembly without its dispatch, the
   `resample` split.
   **Also this stage (2026-08-02 align):** the tick lattice is **derived from the delivered
   `valid_time` and checked against the declared step**, replacing the normalizer's inline regularity
   check — so *declared geometry matches delivery* becomes a computation rather than a promise. Unit
   verification, conversion, `decode`, and Z grouping move to the wrapper, driven by the tap table; a
   Probe declares whether it self-reports units, and one that declares it but reports nothing is a
   `RuntimeFailure`. RED additions: a Probe returning an off-step or gapped series →
   `RuntimeFailure`; a Probe returning a key it was not asked for → `RuntimeFailure`; the
   declares-but-omits units case.
6. **Engine e2e + divergence pin + docs + status** — RED
   (`tests/deterministic/test_e2e_forecast.py`): (a) a woven server profile resolved through
   `Gateway.resolve` with a snapped Selection over the canned transport (bypassing the MCP edge,
   which stays enumerable) → full payload assertions, **including a derived wind parameter** so the
   two-winner Calculator path (fact 9) is exercised, not just the single-winner one; (b) the
   **divergence pin** — the same woven profile with a transport answering the two fetches with
   *different* hour counts → `RuntimeFailure` naming the closed-projection invariant, asserting the
   failure is loud and whole-request (decision 11; no Arbiter code changes for it); plus one
   live-suite run `uv run pytest tests/parity` **unchanged** (m4 acceptance: parity is untouched).
   GREEN — docs at landing:
   [ADR-0002](../../adr/0002-data-model.md) gains **`clip` in the universal axis surface** (the
   recorded-decision amendment m4 carries — that base was set-algebra only) and `ground` as the
   resolution verb over it, a function rather than part of the universal *domain* surface, with
   [#42](../../concerns.md#42-two-request-representations-so-resolution-cannot-be-a-method) named as the
   condition under which it becomes a method; its *"only a regular axis can be snapped-to"* sentence is **restated as a
   consequence**: an axis can be snapped-to when clipping it leaves cells, and the surface forbids
   nothing — v1 serves no snapped X/Y because `SnappedAxis` is temporal by type (and no leaf declares
   an enumerable X/Y behind that) (decision 7). Also
   the `SelectionDomain` /
   `SelectableAxis` representation, and one clause in its axis paragraph: the sentence that already
   reads *"`IntervalAxis` … the base of the request `VantageAxis` (which only overrides `matches`)"*
   gains its span-shaped dual, `ContinuousAxis` as the base of `SnappedAxis` (decision 1), stated
   where the pattern is defined.
   [ADR-0001](../../adr/0001-manifold-algebra-and-composition.md)'s shape-correspondence paragraph names
   the operation that computes it.
   [ADR-0004](../../adr/0004-producer-resolution-and-capability.md) admission language becomes
   mode-dependent (containment for enumerable, intersection for snapped);
   [#13](../../concerns.md#13-candidate-admission-containment-vs-intersection) records the scoped v1
   position. [006](../../tickets/01-0115-retentive-store-freshness.md)'s open store-lattice question closes
   on `Axis.clip`, and its `quantize` is restated as `ground`'s store-side sibling.
   [architecture §Request modes](../../architecture.md#request-modes)'s Z bullet carries the same
   *"only a regular axis can be snapped-to"* clause and takes the same restatement: snapped Z stays
   inapplicable because v1 has **no axis kind that declares irregular native levels**, so nothing
   there clips to cells.
   [#21](../../concerns.md#21-serves-extent-vs-project-crop-ability) narrows to the off-phase case alone;
   [#30](../../concerns.md#30-response-membership-under-runtime-degraded-fallback) gains the named
   padding site; [#23](../../concerns.md#23-spatial-vs-temporal-regularaxis-types) records that m4 adds
   **no** coordinate-kind narrowing (`RegularAxis.clip` is one generic expression) and that what the
   spatial case costs is a float phase-tolerance decision;
   [#40](../../concerns.md#40-composing-servable-requests-at-the-embedding-edge)'s Arm-1 table is
   re-classified for the raise sites this RFC actually leaves behind.
   **[edge/provider.md](../../edge/provider.md) drops its `Status: Normative (tentative)` qualifier and
   every **⚠ pending — m4** marker**: the record already states the declaration law unconditionally and
   specifies the mechanism in full under *Resolution*, so the landing edit is to drop that block's
   pending banner and its transitional-violation paragraph (the leaf's `_snapped_bounds` / `floor_to`
   code, gone by then), and to attach the stage-5
   validators to the *declared geometry matches
   delivery* and *records must agree* invariants — the latter still lacking any pin for records that
   each resolve but resolve **differently**. The same edit clears the **⚠ pending — m4 stages 4–5**
   markers on the Probe/wrapper split (Implemented face, the value-type seam, the units-declaration
   invariant) and folds Roadmap stage 1. The [glossary](../../glossary.md)'s new *Probe* and *Tap table*
   entries land with it; [architecture §Provider](../../architecture.md#provider-leaf-manifold) already
   carries the split.
   Roadmap stage 1 is removed by the same edit. The
   [glossary](../../glossary.md) gains *Ground* (disambiguated from the vertical datum) and *Clip*; the
   [003c ticket](../../tickets/done/01-0110-request-shaping.md) records divergence as a landing risk
   it owns, and carries
   [#42](../../concerns.md#42-two-request-representations-so-resolution-cannot-be-a-method) as a decision
   its migration forces; [delivery status](../../tickets/README.md) m4 row → Done and execution-order note; ticket +
   this RFC → `done/`.

## Edges touched

Added 2026-07-26: [m5](../../tickets/done/01-0090-edge-records.md) landed the Edge-record convention and
`/align`'s Edge challenge rule *after* this RFC was written, so the challenge is discharged here.

- **[MCP surface](../../edge/mcp.md) — untouched, no Contract or Invariant edit at landing.** m4 is
  product-invisible: `build_selection` keeps issuing enumerable `GridDomain` requests, the schema
  and payload are unchanged, and the record's Roadmap stage 1 (free `start`/`end` windows) is
  **003c's** to move into Contract, not m4's. The one relevant new fact is a non-change: the
  snapped request grounds to a `GridDomain` (decision 6), so the record's serialization
  invariants continue to hold verbatim when 003c flips the edge.
- **[Provider surface](../../edge/provider.md) — the edge this RFC actually reshapes** (record
  established 2026-08-02, after this RFC's revision). Decisions 4, 6, and 8 are a **compatible**
  contract change at that edge: a leaf stops inspecting request shape and instead *declares* geometry,
  which widens what it serves without narrowing anything it served before (the enumerable path is
  byte-identical, decision 9). The record states that law unconditionally today — it is already true of
  the shipped leaf's declarations — and marks the mechanism **⚠ pending — m4 stages 3–5**, with the
  leaf's surviving `_snapped_bounds` / `floor_to` code named as the transitional violation stage 4
  extracts. Stage 6's docs list carries the marker-clearing edit.
- **[Embedding surface](../../edge/embedding.md) — Roadmap only, still `Stub`.** m4 mints the
  `SelectionDomain` / `SnappedAxis` vocabulary that stage 3 (request-composition ergonomics) is
  about, and [#40](../../concerns.md#40-composing-servable-requests-at-the-embedding-edge) already
  records what a builder over it could promise. No Invariant becomes promisable — the facade is
  still unselected at [#39](../../concerns.md#39-python-embedding-surface-and-public-failures) — so
  the landing edit is the #40 Arm-1 rows listed in stage 6, nothing more.

## Compatibility and rollout

- **Zero caller-visible change**: the MCP schema, semantics, and payloads are untouched; no
  config or env change; no migration. The mode becomes reachable only to embedders/tests until
  003c rewires the edge.
- The deterministic suite must stay green after every stage. The enumerable request path's *tests*
  are the invariant here, not its code: stage 5 moves that path onto the shared grounded-and-cropped
  implementation, and the pins that guard it must pass unedited.

## Scope limits and follow-ups

- **003c** consumes the mode (edge parsing, reach-filled default `end`, narration) — its ticket;
  the live snapped end-to-end run is 003c's landing probe.
- **006** inserts the store-side half: its `quantize` is `ground`'s sibling in the other direction
  (enclose rather than clip) over the same `Axis.clip`, which is how its open store-lattice question
  closes. The [#22](../../concerns.md#22-lattice-helpers-vs-domain--sampling-module-split) carve moves
  *closer* here without firing — `clip` is a second lattice-arithmetic site in `domain.py` beside
  `sub_lattice_offset`, so `quantize` is the trigger 006 should re-read.
- **One request representation** — m4 leaves two (exact and selection), which is why `ground` takes the
  request as an argument instead of being a method on it.
  [#42](../../concerns.md#42-two-request-representations-so-resolution-cannot-be-a-method) owns the
  end-state and its triggers; **006** is the most likely one, since it authors the second in-tree
  exact-request path.
- **Snapped X/Y** = mint the spatial sibling type + edge wiring (Grid-realization driver) and settle
  float phase tolerance in `RegularAxis.clip` (decision 7,
  [#23](../../concerns.md#23-spatial-vs-temporal-regularaxis-types)); **open-ended bounds**
  (`upper = None`) deferred to
  [#30](../../concerns.md#30-response-membership-under-runtime-degraded-fallback)'s
  diverging-reach trigger; **plain `IntervalAxis` in `SelectableAxis`** waits for alias
  desugaring (Phase 4).
- **New `CapabilityMismatch` raise sites must be classified** into
  [#40](../../concerns.md#40-composing-servable-requests-at-the-embedding-edge)'s Arm-1 inventory as
  they land. m4's are: *snapped against an axis that clips to no cells* — still a **Shape** case, but no
  longer dissolvable by a shape-safe constructor alone, because whether it is servable depends on the
  provider's declared geometry (an Arm-2 `Capability` read); *nothing survives the clip* and
  *taps or records grounding differently* — **Race** cases, never dissolvable at the edge.
- **Divergent winner domains.** Live in the *current single-provider* profile, because the wind
  `Calculator` issues a second independent fetch within one request (fact 9) — not the deferred
  "second provider with diverging reach" case, which remains separate. Deliberately unhandled
  (decision 11): no Arbiter change, no per-cell fold. Pinned by a stage-6 test, classified **Race** at
  #40, owned at **003c**'s landing (where the mode first becomes reachable from the edge) and
  revisited at [#30](../../concerns.md#30-response-membership-under-runtime-degraded-fallback).
- **`/denoise` follow-up:** the per-axis `matches` fold now exists verbatim in three types
  (`GridDomain`, `FootprintDomain`, `SelectionDomain`). Extracting one module-level helper is
  mechanical and covered by existing tests, but it is orthogonal to the mode (decision 3).
