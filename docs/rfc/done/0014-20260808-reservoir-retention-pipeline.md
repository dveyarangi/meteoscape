# RFC 0014 · 2026-08-08, amended 2026-08-09 · The Reservoir retention pipeline — implementation plan

Implementation plan for [the Reservoir retention pipeline](../../tickets/done/01-0115.0040-reservoir-retention-pipeline.md)
(slice 4 of the [retentive store](../../tickets/done/01-0115-retentive-store-freshness.md)). Retention goes
live; the only slice that changes observable behavior.

*Amended 2026-08-09 (plan-impl close-out):* stages 2–3 merged (one `Reservoir` class cannot land
source and root separately); stage-1 tests call private `_read_back`; target-fold `ValueError` →
`RuntimeFailure`; Weaver+clock landed in architecture / ADR-0005; factual corrections against the
built tree (helper names, Arbiter return shape, fact 10's pin).

**Scope in one line:** `Reservoir.project` becomes the load → gate → refill (store-authored
fetch-order) → assimilate → reload → read-back pipeline, with the `Reservoir` gaining its
injected `Clock`; the stores are already wired (slice 3, inert) — this slice makes them serve;
the e2e re-fetch assertion flips.

## Boundaries involved

| Boundary | Owner | What this does to it |
|---|---|---|
| `Reservoir` (`nodes/reservoir.py`) | [ADR-0001](../../adr/0001-manifold-algebra-and-composition.md), [ADR-0006](../../adr/0006-materialization-granularity-and-store-shape.md) | The pipeline (decision 1). `capability` keeps forwarding the child's unchanged. |
| Unit definitions per position | [ADR-0006 §fact→product boundary](../../adr/0006-materialization-granularity-and-store-shape.md), [ADR-0002](../../adr/0002-data-model.md), [#25](../../concerns.md#25-root-store-holding-reuse-across-vantage-windows) | **Source store defers `{T, Z}`** — the timeline **shape's** fact, not the position's (a volumetric shape would snap Z; ADR-0006 as amended 2026-08-09: deferral is position-*bounded*, producer-*decided*); **root store — and a stored Calculator's — defers `{T}`, Z passes identity** into the unit key, which *is* position-forced (product units — #25's recorded residue). Decision 2; mechanized as the factory's `deferred` argument (wired at slice 3). |
| `Weaver` (`nodes/weaver.py`) | [ADR-0005](../../adr/0005-build-time-composition.md) | Slice 3 already passes `deferred` and wires inert `MemoryStore`s. **This slice** injects the `Clock`: `Weaver(stores, clock)`, `wire_source(..., clock)`, `Reservoir(store, source, clock)` — same instance `compose` hands binders and `StoreFactory` ([architecture.md](../../architecture.md), ADR-0005). |
| Arbiter winner agreement (`nodes/arbiter.py`) | [ADR-0004](../../adr/0004-producer-resolution-and-capability.md), [edge/provider.md](../../edge/provider.md) | **Untouched** — priority assembly's whole-request equality check stays its own (decision 3). |
| MCP / e2e behavior | [edge/mcp.md](../../edge/mcp.md) | Repeat requests stop re-fetching; the wire shape is unchanged (serve crops). `route.call_count` flips 4 → 1, and two other e2es move with it (decision 6). |
| Vendor query window | [edge/provider.md](../../edge/provider.md) | **Widens**: the refill's `ANY` T makes the leaf ask its whole live window instead of the request's slice — the retention mechanism itself, and an edge-visible change (decision 6). |
| Landing docs | edge/provider.md, delivery README | The pending-006 block flips to current state; ADR-0001's answer-discipline sentence and ADR-0006/0002 unit defs already landed — this stage is edge + delivery + ticket/RFC archive (RFC 0013 and 0014 both under `rfc/done/`, linked as `./0014`). |

## Facts that shape the implementation (verified 2026-08-08; fact 10 corrected 2026-08-09)

1. **`CoverageSet` travels exactly one hop — Provider → source store.** Only a *source* store
   defers Z; the ask the Arbiter sees (the root store's shape) carries `ANY` on T and the request's
   **vantage** Z, so every winner answers a single-domain Coverage (the source Reservoir has
   already absorbed the group and relabeled Z). The Arbiter and Calculators never meet the carrier
   — no group handling is added to either.
2. A Calculator under an open-T ask receives full-timeline inputs from its scoped Arbiter and
   computes pointwise as today; `wind_u`/`wind_v` share one native domain, so its inputs are
   conformable by construction.
3. All winners of one request draw on the same underlying store in v1 (single source), so their
   full-timeline extents agree; genuine multi-source divergence stays the existing whole-request
   `RuntimeFailure`. *Landed 2026-08-09:* the e2e that pinned it became
   `test_snapped_mixed_request_shares_one_vendor_geometry` (retention collapses the dual fetch), and
   the invariant was re-homed to the fold where it lives —
   `test_winner_domains_that_differ_fail_the_whole_request` in `test_arbiter.py`, reachable with no
   network and no store, guarding [#43](../../concerns.md#43-narrow-answering-providers-re-open-mixed-request-run-divergence)'s
   re-opening case.
4. [007](../../tickets/01-0117-off-grid-homogenization.md) owns the *nearest*-cell kernel, the
   on-grid identity crop, and the `0.0001°` default step. This slice's X/Y read-back is the
   **containing-cell relabel** — same containment math as `quantize`, no new arithmetic — and is
   temporary by design.
5. **A bounded ask's required coverage reads the child's *current* live window** (`reach`'s
   `RollingAxis` reads the clock), so a held unit stops covering once the window rolls past its
   stored end — a correct whole-unit refetch, not a defect.
   [0112](../../tickets/done/01-0112-day-anchored-availability-window.md)'s day-anchoring keeps that
   window identical across a day, so same-day repeats serve tripless (the parent ticket's
   load-bearing-anchor note, mechanized here). Boundless asks have no required coverage at all —
   decision 5.
6. **Concurrency posture, named rather than lucky**: two concurrent requests can both miss and
   both refill — an accepted double fetch, not corruption, because `assimilate` replaces whole
   units atomically (last writer wins, single-origin preserved) and serving reads post-warm
   holdings. No locking or request coalescing in v1; a coalescing seam, if throughput ever wants
   one, is `Metronome`'s within-tick note ([clock.py](../../../src/meteoscape/clock.py)), not the
   store's.
7. **`resample` refuses to relabel, and names this node as the owner** (verified 2026-08-09
   against the built store). Held units and the ask disagree on the point axes by construction —
   a unit's X is the provider's `RegularAxis(x, 32.5, step 1.0, 1)`, the store's fetch-order tick
   is `RegularAxis(x, 32.5, step 0.0001, 1)`, and the user's own member is a *different
   coordinate* up to a cell away. `sub_lattice_offset` answers `None` for both pairings (differing
   step; off-phase), so [`resample`](../../../src/meteoscape/manifold/sampling.py) raises
   `NotImplementedError("… requires Reservoir homogenization")`. That refusal is the guard, not a
   gap: re-addressing a value measured at one coordinate to another is a **claim**, and the crop
   engine declines to make it silently. Decision 2 makes the claim explicitly, here. **Widening
   `sub_lattice_offset` to align count-1 axes regardless of step is rejected**: it would make the
   substitution free and invisible system-wide, dissolving the one guard that keeps read-back
   fidelity reviewable ([#5](../../concerns.md#5-read-time-homogenization-fidelity),
   [007](../../tickets/01-0117-off-grid-homogenization.md)).
8. **A cold mixed request costs exactly one vendor call, and a warm repeat none** — the source
   `Reservoir` instance is *shared*: `wire_source` builds one per registered Source and the
   Calculator's scoped Arbiter filters the same `Producer` objects
   ([weaver.py](../../../src/meteoscape/nodes/weaver.py)), so the Calculator's `wind_u`/`wind_v`
   `Selection` reaches the store the temperature fetch just warmed. With the whole tap table as
   the natural fetch unit under a boundless ask, that first trip lands all six parameters. The
   e2e's `route.call_count` therefore goes **4 → 1** across its two requests, not the "2-then-
   cached" this RFC predicted before the fetch-unit property was settled.
9. **Divergent held T windows are unreachable in v1, by two independent properties** — worth
   naming because the read-back fold would otherwise have to reconcile them. At a **Source**: any
   refill answers with the provider's whole offering, so `assimilate` replaces *every* unit at
   that cell from one fetch — units there cannot carry different windows (the property a
   narrow-answering provider breaks →
   [#43](../../concerns.md#43-narrow-answering-providers-re-open-mixed-request-run-divergence)). At
   the **root**: the request carries bounded T (the MCP edge always sends an interval,
   [mcp_app.py](../../../src/meteoscape/api/mcp_app.py)), so `ground` clips every unit to the *same*
   bounds on the same hourly phase — divergence normalizes away. A future boundless-T author (the
   embedding surface, [#39](../../concerns.md#39-python-embedding-surface-and-public-failures)) is
   the trigger that makes this reachable at the root.
10. **Required coverage is never empty where it is computed** — `bounds ∩ reach` could in
    principle not meet, but a bounded request that misses the child's window entirely fails
    *admission* first (`SnappedAxis.matches` is intersective, so the Arbiter never nominates a
    winner; pinned by
    `test_history_window_is_capability_mismatch_with_no_vendor_call` — `capability-mismatch` and
    `call_count == 0`). Partial overlap yields the servable part, which is non-empty by
    definition. So this is an **assert**, not a branch — a `None` intersection here means
    admission let something through that it should not have. (The out-of-range e2e is a different
    pin: `call_count == 1` against the clipped live window, and it survives retention unchanged —
    decision 6.)
11. **The stored-Calculator position gets the pipeline but stays unexercised** — `CalculatorDef.
    stored` defaults `False` and no v1 profile sets it ([config.py](../../../src/meteoscape/config.py)),
    so only two stores are ever allocated (the weaver test pins exactly that). The third position
    is correct by construction rather than by test, and its spec binding remains
    [#27](../../concerns.md#27-stored-calculator-store-binding)'s open question. Named so the
    coverage gap is a known one.
12. **A child delivering less than it declares yields a short answer, exactly as it does today** —
    slice 4 changes nothing here, because the answer geometry grounds against the *delivered*
    records, not the declaration. The deterministic fixtures are such a child on purpose
    (`_canned_forecast` returns 168 ticks against a 384-hour declared reach) and need no
    resizing. Declaration-versus-delivery mismatch remains parity's business
    ([#41](../../concerns.md#41-parity-evidence-is-unenforced-and-unrouted)), never the pipeline's:
    decision 5 is what keeps it out.

## The seam with RFC 0013 — what this pipeline assumes of the store

Each row is a promise the pipeline leans on; if [RFC 0013](./0013-20260808-timeline-store.md)
moves, this table says what breaks here.

| The pipeline assumes | Promised at |
|---|---|
| `project` is total over raw asks — translation internal, unheld omitted, empty `CoverageSet` normal, stale included | 0013 d.5 |
| A tick is a **fixed point** of `quantize`, so the fetch-order a parent hands down re-quantizes cleanly at the child position | 0013 d.1, fact 6 |
| An identity-axis member matches units by **value equality** on `z_key` — vantage-keyed root units answer only their own vantage (#25's residue) | 0013 d.5 |
| `assimilate` replaces **whole units**; a spliced `valid_time` is unrepresentable | 0013 d.4 |
| The gate reads the **returned holdings'** capability (per-ask exact), never `store.capability` (narration only, [#47](../../concerns.md#47-a-stores-capability-narrates-plural-holdings-truncate-to-one-reach)) | 0013 d.7 |
| `quantize` authors the fetch-order, and its `ANY` axes are what license the child's native multi-domain answer | 0013 d.9, [ADR-0006](../../adr/0006-materialization-granularity-and-store-shape.md) |

## Design decisions

1. **The pipeline** (`Reservoir.project(selection)`) — *amended 2026-08-09: the store-side
   `report` verb dissolved; the store's `project` is the holdings query and the gate is this
   node's policy over what it returns
   ([ADR-0006](../../adr/0006-materialization-granularity-and-store-shape.md))*:

   ```python
   servable = selection.parameters & self.source.capability.parameters.keys()
   if not servable:
       raise CapabilityMismatch("no producer admits any requested parameter")  # Arbiter's sentence

   held = await self.store.project(selection)                       # RAW ask — the store translates
                                                                    # onto its boxes internally;
                                                                    # stale included, unheld omitted,
                                                                    # empty normal (RFC 0013 d.5)

   # Boundedness: AxisName.T in open_axes(selection.domain). No shared t_bounds / t_extent API —
   # locally: snapped T.interval when bounded; reach(p).axis(T).extent; Interval.intersection /
   # contains. Provenance: the owning record in held.records (p in r.ranges), then
   # r.provenance.summary(p).expiration.
   over = {p: request_t ∩ reach_t(p) for p in servable} if T_bounded else None

   missing = frozenset(
       p for p in servable
       if p not in held.capability.parameters
       or (over is not None and not held_t_extent(p).contains(over[p]))  # ⊉
       or owning_record(held, p).provenance.summary(p).expiration <= self._clock.now()
   )
   if missing:
       shape = self.store.quantize(selection.domain)                # the fetch-order — quantize's
                                                                    # ONLY public use; lattices
                                                                    # stay store-private
       answer = await self.source.project(Selection(domain=shape, parameters=missing))
       await self.store.assimilate(CoverageSet.of(answer))          # normalize child answer
       held = await self.store.project(selection)
       if not held.capability.parameters:
           raise RuntimeFailure("refill produced no holdings")      # engine fault
   return self._read_back(held, selection)                          # serve everything post-warm
   ```

   Serving happens **after** assimilation from the store alone — one code path, which is what makes
   same-`issue_time` across a mixed request a structural property rather than a test hope.

   **Corrected at review, 2026-08-09 — this sketch had an admission hole.** It computes `over` (the
   per-parameter `request T ∩ reach`), lets a parameter whose intersection is *empty* fall through
   the `missing` fold unrefilled, and then serves **everything held**. With diverging per-parameter
   reaches that answers from holdings nothing would refresh — and grounding such a record can fail
   the whole request rather than merely leak it. As landed, admission gates **both** ends: `project`
   computes the admitted set once and passes it to `_read_back(held, selection, admitted)`, which
   intersects the served parameters and filters the records it grounds. Degenerate in v1 (one shared
   T reach per provider), live at the first diverging-reach set
   ([#30](../../concerns.md#30-response-membership-under-runtime-degraded-fallback)); the contract now
   lives in [architecture §Reservoir](../../architecture.md#reservoir) and is pinned by
   `test_parameter_whose_reach_left_the_window_is_not_served_from_holdings`.
   **Two empty outcomes, two different errors** (pass 4 — both would otherwise surface as
   `agreed_geometry`'s "no geometry to agree on", a leak from the wrong layer):
   - **`servable` is empty** — the child declares none of the asked parameters. That is the
     request being unservable, so `CapabilityMismatch`, the same verdict and category the Arbiter
     gives ("no producer admits any requested parameter").
   - **`servable` is non-empty but `held` is still empty after the refill** — the child either
     answered nothing while raising nothing, or answered something that failed to land. Both are
     engine faults rather than request faults: `RuntimeFailure`.
   `CoverageSet.of(answer: CoverageRecord | CoverageSet) -> CoverageSet` — identity on a group,
   a one-record wrap on a record — is minted **here**, with this line its only caller. The child
   is typed `Manifold`; the Arbiter is annotated `-> Manifold` too: `_assemble` returns a
   `CoverageRecord`, and the single-winner path **passthroughs** whatever the child returns. After
   this slice a source `Reservoir` always returns a merged `CoverageRecord` from read-back, and a
   Calculator returns a `CoverageRecord`; before assimilation the `Reservoir` therefore
   `isinstance`-narrows to `CoverageRecord | CoverageSet` and raises `RuntimeFailure` otherwise —
   a lazy non-record `Coverage` has no business being assimilated (sampling happens at the leaf,
   ADR-0001), and that is an engine fault rather than a request one.
2. **Read-back = relabel, then fold** — three steps, in this order (2026-08-09; the earlier
   "per-axis relabel + crop" named the outcome but no mechanism, and the obvious one does not
   work — fact 7). **`_relabel_onto` and `_read_back` are private methods on `Reservoir`**
   (plan-impl align): stage-1 tests construct a `Reservoir` and call `_read_back(held, selection)`
   with a hand-built `CoverageSet` while `project` is still pass-through. No public read-back API,
   no test-only hook.

   ```python
   try:
       target = agreed_geometry(                               # the geometry this answer answers
           (ground(selection.domain, r.domain) for r in held.records),
           request=selection.domain,
       )                                                       # same fold TimelineProvider uses
   except ValueError as exc:
       raise RuntimeFailure(...) from exc                      # engine invariant — admission and
                                                               # the store already decided these
                                                               # units answer this ask
   relabelled = tuple(self._relabel_onto(r, target) for r in held.records)
   served = frozenset(held.capability.parameters)              # what is HELD, not what was asked
   return await CoverageSet(relabelled).project(Selection(target, served))
   ```

   **The fold's parameter set is the held one, not the asked one** (pass 4).
   `CoverageSet.project` raises `CapabilityMismatch` for any asked parameter its records do not
   carry ([coverage.py](../../../src/meteoscape/manifold/coverage.py)), so passing
   `selection.parameters` would turn a legitimate omission into a refusal — contradicting this
   slice's own criterion that an unserved parameter is omitted. Passing the held set is also what
   *propagates* omission outward: the caller reads the answer's parameters, never assuming they
   echo the request (ADR-0001's one-directional parameter binding).

   - **The target** is `ground` per held unit, folded by `agreed_geometry` — the identical pattern
     `TimelineProvider._answered_geometry` already uses, at the identical question ("what geometry
     does this answer answer with"). `ground` supplies each axis: a bounded T clips the unit's
     timeline to the request window, a boundless T takes it whole, and the point axes pass through
     as the request's own members — which is precisely the relabel target. Both return
     `EnumerableDomain`, so `CoverageSet.project`'s enumerable requirement is met. A `ValueError`
     from either is an engine fault here (unlike the leaf, which maps it to `CapabilityMismatch`):
     post-warm holdings that cannot ground against an already-admitted ask broke an invariant →
     **`RuntimeFailure`**.
   - **`_relabel_onto`** rewrites a record's **count-1 point axes (X, Y, Z)** to the target's,
     leaving `ranges` and `provenance` untouched: one index per axis, so no value moves and no
     arithmetic runs — only the address changes. It asserts each of the three is count-1 (v1
     records are point-shaped; a gridded provider would split first — the #31 posture). It carries
     one **`TODO (temporary)`** seam, owned by
     [0117](../../tickets/01-0117-off-grid-homogenization.md): that ticket replaces containing-cell
     relabel with the nearest-neighbour kernel and an on-grid identity crop, and this function is
     the single site it edits. This is where the
     **fact→product boundary** is crossed at a Source — a value measured at 2 m answering the
     vantage the request named — and where a grid tick becomes the asked point; the root's units
     are already vantage-shaped, so Z is an identity rewrite there.
     **No Z re-match is performed, and that is not an omission.** ADR-0006 describes read-back as
     *selecting* the native record whose Z cell matches the handed vantage; in v1 that selection
     is **degenerate and already decided upstream** — one tap declares one Z per parameter, so a
     parameter has at most one unit (RFC 0013 d.6's assert is the tripwire if that ever changes),
     and admission has *already* tested that unit's native Z against this vantage (the Arbiter
     checks `serves` on the Provider's footprint, which is where the unit's Z came from). Adding a
     filter here would re-ask a settled question; the assert is what keeps the reasoning honest.
   - **The fold** is then the existing carrier: with the point axes now *equal*, `resample` aligns,
     crops T, and `CoverageSet._merged` assembles the parameters onto one Coverage with the right
     provenance plane (`Uniform` when one fetch stamped them all, else `PerParameter`). No second
     merge is written.

   Read in one line: **relabel is the claim, the fold is the arithmetic** — and they stay separate
   so the claim has one reviewable home.
3. **Priority assembly keeps demanding full agreement.** Open members widen *admission* (an open
   member `matches` everything — already true from RFC 0011) but not *assembly*: under the
   `priority` reconciler every winner independently grounds the same request, so winner domains
   must be **equal on every axis, open or not** — the existing whole-request equality check in
   `Arbiter._assemble`, unchanged. It deliberately does not borrow `agreed_geometry`: that fold
   derives its licence from the request, and this demand is the priority reconciler's assembly
   law, not the request's (a `splice` reconciler will own a different one, as it owns its
   `compose_domains`). Per-axis relaxation for genuinely divergent multi-source reaches stays
   future work ([#30](../../concerns.md#30-response-membership-under-runtime-degraded-fallback) /
   [#9](../../concerns.md#9-cross-run-combination)); nothing here forecloses it.
4. **Wiring**: landed at slice 3 — `StoreFactory.create(spec, deferred)` position-parameterized,
   `StubStore` deleted, the graph carrying inert `MemoryStore`s. This slice's only construction
   change: the **`Reservoir` gains an injected `Clock`** for its freshness gate —
   `Reservoir(store, source, clock)` — which the **`Weaver` carries too** (`Weaver(stores, clock)`;
   `wire_source(registered, stores, clock)` — three `Reservoir` call sites). Architecture and
   [ADR-0005](../../adr/0005-build-time-composition.md) already state that signature: `compose` builds
   one `Clock` and hands it to binders, `StoreFactory`, and the Weaver ([server.py](../../../src/meteoscape/server.py)).
   The `Store` contract stays clockless — freshness is the reader's policy, and the `Reservoir` is
   the reader (2026-08-09 align). A materialized source still wires storeless (ADR-0006,
   untouched); the stored-Calculator site's root-spec reuse stays
   [#27](../../concerns.md#27-stored-calculator-store-binding)'s question.
5. **Coverage is checked only where the request bounds T** (2026-08-09 pass 3, replacing an earlier
   rule that compared a boundless ask against the child's declared window). An `ANY` member has no
   `extent` — asking "does the held unit cover the ask?" is undefined there, and the earlier rule
   had to *invent* a stand-in (the child's declared reach), which is the tell. The honest reading:
   `ANY` means **"everything you have"**, and a unit is by construction the whole of one fetch's
   answer, so it satisfies that ask the moment it exists. Under a boundless T, therefore, **only
   freshness governs**; `over` is `None` and the covers clause is skipped.

   Bounded T (the root, and every edge-authored request) keeps the covers check in full — that is
   where a held window genuinely can fail to contain the asked hours, and where
   covers-or-refetch-whole earns its name.

   Two things this settles, both of which the earlier rule got wrong:
   - **The cold mixed request really is one fetch.** The temperature trip's `wind_u`/`wind_v` units
     are fresh, so the Calculator's `Selection` serves from the store instead of failing a
     coverage test it could never pass.
   - **Nothing needs the day-roll argument.** The earlier rule was defended as self-healing when
     the day-anchored window rolls; but `expiration` is per-run and far shorter than a day, so a
     unit is already stale before the window moves. Freshness was covering that case all along.

6. **Two behavioral flips, not one** — the wire schema, units, provenance fields, and error
   taxonomy stay untouched, but **the outbound vendor query widens** alongside the call counts
   (2026-08-09 pass 2; this decision previously claimed the flips were "confined to call counts
   and reuse", which is false):
   - **Call counts and reuse.** The re-fetch e2e becomes the fresh-reuse test: `route.call_count`
     **4 → 1** across its two requests (fact 8). A new e2e pins the cold mixed request
     explicitly: one fetch, calculator inputs served from the store, one `issue_time` across every
     assembled parameter.
   - **The vendor is asked for its whole live window, not the request's slice.** The refill ask
     carries `ANY` on T, so `_window_of` resolves to the provider's entire rolling window — that
     *is* the retention mechanism (fetch whole, store absorbs, serve crops), and the served answer
     is unchanged because read-back crops. But it is visible at the Provider surface and must land
     in [edge/provider.md](../../edge/provider.md) with the `⚠ pending — 006` flip: a cold request
     now costs the full horizon rather than its own slice, traded for every later request in that
     window costing nothing.

   **Test ripple beyond the re-fetch test** (pass 2 — so no one meets it as a surprise):
   `test_snapped_selection_resolves_through_the_woven_profile` asserts both `call_count == 2` and
   the *narrow* vendor query (`start_hour == 14:00`, `end_hour == 17:00`); under retention it
   becomes one call asking the day-anchored live window, and its "mid-hour bounds floor onto the
   leaf's own ticks before the vendor is asked anything" premise moves from the vendor query to
   the **answer geometry**, which is what that test actually guards. By contrast
   `test_out_of_range_bounds_fetch_exactly_the_clipped_window` **survives unchanged** — its
   clipped window already *is* the whole live window — and that coincidence is worth stating so
   the test is not "fixed" into agreement with its neighbour.

## Stages (each green)

Stages are landing milestones, not single red→green cycles: within each, work proceeds one
observable behavior → minimal implementation at a time per `/tdd`.

One `Reservoir` class turns **both** positions on together, and the e2e `call_count` flip needs
both (shared source warm + root serve). Source vs root criteria are therefore **test groups
inside one pipeline stage**, not separately shippable greens (plan-impl align 2026-08-09).

1. **Read-back** — the claim, before any pipeline reads it. Red: tests construct a `Reservoir`
   and call `_read_back` with a hand-built `CoverageSet` — `_relabel_onto` rewrites count-1 X/Y/Z
   and leaves values and provenance identical; a relabelled carrier folds through
   `CoverageSet.project` where the raw one raises (fact 7's regression, pinned as a test so the
   guard's removal would be caught); T crops to a bounded window and passes whole under `ANY`;
   multi-parameter merge keeps one `issue_time`; a forced target-fold `ValueError` surfaces as
   `RuntimeFailure`. Green: private `_relabel_onto` + `_read_back`. `project` stays
   pass-through — suite green throughout.
2. **Pipeline live** — red then green in one landing: `Reservoir(store, source, clock)`;
   `Weaver` / `wire_source` / `compose` hand the clock; full
   load → gate → refill → assimilate → reload → `_read_back`.
   - **Source-group:** fresh repeats without a vendor call; Z-reuse (a request whose Z differs but
     still admits — engine-level, since the MCP edge pins one vantage — reuses the native unit);
     whole-unit refetch after a window miss; an unserved parameter omitted; a wholly-unservable
     request refused as `CapabilityMismatch`.
   - **Root-group:** the cold mixed request (one fetch, store-served calculator inputs, one
     `issue_time`) on the existing fixtures, unresized (decision 5); vantage-keyed root units
     (#25 residue pinned as a test).
   - **E2e:** `route.call_count` **4 → 1**; snapped-selection vendor-window assertions move to
     answer geometry; out-of-range e2e unchanged.
3. **Landing** — retention-interval e2e (never serves stale; bounds memory only); docs: the
   provider edge record's `⚠ pending — 006` block flips to current state (its premise — a
   pass-through `Reservoir` — dies here), ADR-0006's flatten rejection marked live, delivery
   README rows, both tickets and this RFC to `done/` with links repaired (incl. RFC 0013's
   `./0014` → `../0014`). Per-position unit-definition architecture already lives in ADR-0006/0002
   — nothing architectural waits on this stage. Closing [0115.0030](../../tickets/done/01-0115.0030-timeline-store.md)
   paperwork (code already landed) is an implement precondition, folded into this landing if still
   open.

## Out of scope / follow-ups

- Nearest-neighbor read-back, on-grid identity, default step →
  [0117](../../tickets/01-0117-off-grid-homogenization.md) (the **`TODO (temporary)`** marker
  identifies its code seam).
- Cross-vantage root-unit reuse → [#25](../../concerns.md#25-root-store-holding-reuse-across-vantage-windows).
- Per-axis winner-agreement relaxation under open members → #30/#9.
- Store hit/refill observability → [0195](../../tickets/01-0195-minimal-resolution-logging.md).
