# RFC 0014 · 2026-08-08 · The Reservoir retention pipeline — implementation plan

Implementation plan for [the Reservoir retention pipeline](../tickets/01-0115.0040-reservoir-retention-pipeline.md)
(slice 4 of the [retentive store](../tickets/01-0115-retentive-store-freshness.md)). Retention goes
live; the only slice that changes observable behavior.

**Scope in one line:** `Reservoir.project` becomes the load → gate → refill (store-authored
fetch-order) → assimilate → reload → read-back pipeline, with the `Reservoir` gaining its
injected `Clock`; the stores are already wired (slice 3, inert) — this slice makes them serve;
the e2e re-fetch assertion flips.

## Boundaries involved

| Boundary | Owner | What this does to it |
|---|---|---|
| `Reservoir` (`nodes/reservoir.py`) | [ADR-0001](../adr/0001-manifold-algebra-and-composition.md), [ADR-0006](../adr/0006-materialization-granularity-and-store-shape.md) | The pipeline (decision 1). `capability` keeps forwarding the child's unchanged. |
| Unit definitions per position | [ADR-0006 §fact→product boundary](../adr/0006-materialization-granularity-and-store-shape.md), [ADR-0002](../adr/0002-data-model.md), [#25](../concerns.md#25-root-store-unit-reuse-across-vantage-windows) | **Source store defers `{T, Z}`** — the timeline **shape's** fact, not the position's (a volumetric shape would snap Z; ADR-0006 as amended 2026-08-09: deferral is position-*bounded*, producer-*decided*); **root store — and a stored Calculator's — defers `{T}`, Z passes identity** into the unit key, which *is* position-forced (product units — #25's recorded residue). Decision 2; mechanized as the factory's `deferred` argument (wired at slice 3). |
| `Weaver` (`nodes/weaver.py`) | [ADR-0005](../adr/0005-build-time-composition.md) | **Already done at slice 3** (2026-08-09 pass 2): the call sites pass `deferred` and the graph carries inert `MemoryStore`s. This slice adds only the `Reservoir`'s injected `Clock`. |
| Arbiter winner agreement (`nodes/arbiter.py`) | [ADR-0004](../adr/0004-producer-resolution-and-capability.md), [edge/provider.md](../edge/provider.md) | **Untouched** — priority assembly's whole-request equality check stays its own (decision 3). |
| MCP / e2e behavior | [edge/mcp.md](../edge/mcp.md) | Repeat requests stop re-fetching; the wire shape is unchanged (serve crops). The e2e `route.call_count` assertions flip from 4 to 2-then-cached. |
| Landing docs | edge/provider.md, ADR-0006 | The pending-006 block flips to current state; ADR-0001's sentence landed at [RFC 0012](./done/0012-20260808-multidomain-carrier-timeline.md) — only the remaining syncs here. |

## Facts that shape the implementation (verified 2026-08-08)

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
   `RuntimeFailure` (`test_snapped_winner_domains_that_diverge_fail_the_whole_request` semantics,
   unchanged).
4. [007](../tickets/01-0117-off-grid-homogenization.md) owns the *nearest*-cell kernel, the
   on-grid identity crop, and the `0.0001°` default step. This slice's X/Y read-back is the
   **containing-cell relabel** — same containment math as `quantize`, no new arithmetic — and is
   temporary by design.
5. **At a boundless-asked position the covers check runs against the child's *current* live
   window** (`reach`'s `RollingAxis` reads the clock), so a held unit stops covering when the
   window rolls past its stored end — a correct whole-unit refetch, not a defect.
   [0112](../tickets/done/01-0112-day-anchored-availability-window.md)'s day-anchoring is what
   keeps the window identical across a day, so same-day repeats serve tripless (the parent
   ticket's load-bearing-anchor note, mechanized here).
6. **Concurrency posture, named rather than lucky**: two concurrent requests can both miss and
   both refill — an accepted double fetch, not corruption, because `assimilate` replaces whole
   units atomically (last writer wins, single-origin preserved) and serving reads post-warm
   holdings. No locking or request coalescing in v1; a coalescing seam, if throughput ever wants
   one, is `Metronome`'s within-tick note ([clock.py](../../src/meteoscape/clock.py)), not the
   store's.

## The seam with RFC 0013 — what this pipeline assumes of the store

Each row is a promise the pipeline leans on; if [RFC 0013](./0013-20260808-timeline-store.md)
moves, this table says what breaks here.

| The pipeline assumes | Promised at |
|---|---|
| `project` is total over raw asks — translation internal, unheld omitted, empty `CoverageSet` normal, stale included | 0013 d.5 |
| A tick is a **fixed point** of `quantize`, so the fetch-order a parent hands down re-quantizes cleanly at the child position | 0013 d.1, fact 6 |
| An identity-axis member matches units by **value equality** on `z_key` — vantage-keyed root units answer only their own vantage (#25's residue) | 0013 d.5 |
| `assimilate` replaces **whole units**; a spliced `valid_time` is unrepresentable | 0013 d.4 |
| The gate reads the **returned holdings'** capability (per-ask exact), never `store.capability` (narration only, [#47](../concerns.md#47-a-stores-capability-narrates-plural-holdings-truncate-to-one-reach)) | 0013 d.7 |
| `quantize` authors the fetch-order, and its `ANY` axes are what license the child's native multi-domain answer | 0013 d.9, [ADR-0006](../adr/0006-materialization-granularity-and-store-shape.md) |

## Design decisions

1. **The pipeline** (`Reservoir.project(selection)`) — *amended 2026-08-09: the store-side
   `report` verb dissolved; the store's `project` is the holdings query and the gate is this
   node's policy over what it returns
   ([ADR-0006](../adr/0006-materialization-granularity-and-store-shape.md))*:

   ```python
   held = await self.store.project(selection)                       # RAW ask — the store translates
                                                                    # onto its boxes internally;
                                                                    # stale included, unheld omitted,
                                                                    # empty normal (RFC 0013 d.5)
   over = {p: required_window(selection.domain, self.source.capability.reach(p))
           for p in selection.parameters}                           # required coverage — only this
                                                                    # node holds both halves.
                                                                    # bounded T   → bounds ∩ reach;
                                                                    # boundless T → the child's whole
                                                                    #   live window (an open member
                                                                    #   has no extent to intersect —
                                                                    #   the source position's case,
                                                                    #   its ask being a fetch-order)
   missing = frozenset(
       p for p in selection.parameters
       if p not in held.capability.parameters                       # absent
       or held.capability.reach(p) T-extent ⊉ over[p]               # not covering → refetch whole
       or record_of(held, p).provenance.summary(p)                  # owning record by iterating
              .expiration <= self._clock.now()                      #   held.records (public field);
   )                                                                # expired (Reservoir's clock)
   if missing:
       shape = self.store.quantize(selection.domain)                # the fetch-order — quantize's
                                                                    # ONLY public use; lattices
                                                                    # stay store-private
       answer = await self.source.project(Selection(domain=shape, parameters=missing))
       await self.store.assimilate(CoverageSet.of(answer))          # normalize: an Arbiter child
                                                                    # answers single-domain
       held = await self.store.project(selection)
   return self._read_back(held, selection)                          # serve everything post-warm
   ```

   Serving happens **after** assimilation from the store alone — one code path, which is what makes
   same-`issue_time` across a mixed request a structural property rather than a test hope.
   `CoverageSet.of(answer: CoverageRecord | CoverageSet) -> CoverageSet` — identity on a group,
   a one-record wrap on a record — is minted **here**, with this line its only caller. The narrow
   parameter type is deliberate and total: the root's child is an Arbiter and `Arbiter._assemble`
   returns `CoverageRecord` ([arbiter.py:174](../../src/meteoscape/nodes/arbiter.py)); a lazy
   non-record `Coverage` has no business being assimilated (sampling happens at the leaf, ADR-0001).
2. **Read-back = per-axis relabel + crop, from stored units onto `selection`:**
   - **T** — aligned crop of the whole-timeline unit onto the grounded request window (`resample`;
     index arithmetic that exists).
   - **X/Y** — the containing cell's values relabeled onto the requested point.
     `TODO(0117): nearest-neighbor kernel + on-grid identity crop replace this containing-cell
     relabel` — the comment is required, so nothing grows to rely on floor-containment semantics.
   - **Z** — the fact→product boundary: a *source* Reservoir selects per parameter the native
     record whose Z cell `matches` the handed vantage and relabels onto the vantage cell (fat cell
     absorbs offsets, ADR-0002); the *root* Reservoir's units are already vantage-shaped
     (identity).
3. **Priority assembly keeps demanding full agreement.** Open members widen *admission* (an open
   member `matches` everything — already true from RFC 0011) but not *assembly*: under the
   `priority` reconciler every winner independently grounds the same request, so winner domains
   must be **equal on every axis, open or not** — the existing whole-request equality check in
   `Arbiter._assemble`, unchanged. It deliberately does not borrow `agreed_geometry`: that fold
   derives its licence from the request, and this demand is the priority reconciler's assembly
   law, not the request's (a `splice` reconciler will own a different one, as it owns its
   `compose_domains`). Per-axis relaxation for genuinely divergent multi-source reaches stays
   future work ([#30](../concerns.md#30-response-membership-under-runtime-degraded-fallback) /
   [#9](../concerns.md#9-cross-run-combination)); nothing here forecloses it.
4. **Wiring**: landed at slice 3 (2026-08-09 pass 2) — `StoreFactory.create(spec, deferred)`
   position-parameterized, `StubStore` already deleted, the graph carrying inert `MemoryStore`s.
   This slice's only construction change: the **`Reservoir` gains an injected `Clock`**
   (construction-time, ADR-0005) for its freshness gate — the `Store` contract stays clockless
   (2026-08-09 align). A materialized source still wires storeless (ADR-0006, untouched); the
   stored-Calculator site's root-spec reuse stays
   [#27](../concerns.md#27-stored-calculator-store-binding)'s question.
5. **Behavioral flips are confined to call counts and reuse** — the wire schema, units, provenance
   fields, and error taxonomy are untouched. The e2e re-fetch test becomes the fresh-reuse test
   (two requests → one fetch), and a new e2e pins the cold mixed request: one fetch, calculator
   inputs served from the store, one `issue_time` across parameters.

## Stages (each green)

Stages are landing milestones, not single red→green cycles: within each, work proceeds one
observable behavior → minimal implementation at a time per `/tdd`.

1. **Source position** — red: source Reservoir serves fresh repeats without a vendor call; Z-reuse
   (a request whose Z differs reuses native units); whole-unit refetch end-to-end. Green: pipeline
   + read-back wired at each Source; e2e re-fetch assertion flips here.
2. **Root position** — red: the cold mixed request (one fetch, store-served calculator inputs,
   one `issue_time`); vantage-keyed root units (#25 residue pinned as a test). Green: the root
   pipeline live (its store, `deferred={T}`, is already wired since slice 3).
3. **Landing** — retention-interval e2e (never serves stale; bounds memory only); docs: the
   provider edge record's pending-006 block flips to current state, ADR-0006's flatten rejection
   marked live, delivery README rows. (The per-position unit-definition architecture landed in
   ADR-0006/0002 at the align follow-up, 2026-08-08 — nothing architectural waits on this stage.)

## Out of scope / follow-ups

- Nearest-neighbor read-back, on-grid identity, default step → [007](../tickets/01-0117-off-grid-homogenization.md)
  (the `TODO(0117)` marks the seam in code).
- Cross-vantage root-unit reuse → [#25](../concerns.md#25-root-store-unit-reuse-across-vantage-windows).
- Per-axis winner-agreement relaxation under open members → #30/#9.
- Store hit/refill observability → [0195](../tickets/01-0195-minimal-resolution-logging.md).
