# 0026 · 2026-08-09 · Slice 4 reviewed, four review rounds, and the Holding rename

**Scope:** the slice-4 `Reservoir` retention pipeline landed and was reviewed four times (each round
by a different lens, two of them adversarial); a latent admission bug and two vacuous tests were
fixed; `compose`'s clock invariant became structural; the failure-class inventory was minted; and
the store's grain was renamed **unit → Holding** across the maintained corpus. Closed with a
`/sync-arch` pass over architecture, ADRs, glossary, and the three Edge records.

## Work done

- **Reviewed the slice-4 landing** ([RFC 0014](../../../rfc/done/0014-20260808-reservoir-retention-pipeline.md),
  [ticket 0115.0040](../../../tickets/done/01-0115.0040-reservoir-retention-pipeline.md)): faithful to the
  plan, including both e2e ripples it predicted in advance. The gate, however, was **red on three of
  four checks** while the ticket read Done — lint, format, and pyright all failed on the new test
  module. Fixed, and the whole of 006 is now green at 303 tests.
- **Four review rounds, each finding what the last could not**: (1) conformance + gate;
  (2) a user challenge on `_missing`'s `servable` — which turned out to be a *naming* defect, not a
  behavioural one, since the code already narrowed to the request; (3) placement questions
  (`_grid_axes`, `_t_extent`, `_relabel_onto`); (4) an external reviewer's five findings, all valid.
- **Two vacuous tests found and repaired** — a carrier test asserting `pytest.raises(Exception)` that
  passed for the wrong reason, and a target-fold test made vacuous *by my own fix* earlier the same
  session (an empty carrier short-circuited before the fold it meant to exercise). Both now assert
  the specific sentence, and each was verified to fail against the old behaviour before being kept.
- **Landed the failure-class inventory** and tagged its sites in code — see *Settled*.
- **Renamed the store's grain** (see *Settled*), including the private types, the privacy guard's
  pinned set, and every maintained doc.

## Settled this session

- **Admission gates serving, not only refilling** — a parameter whose reach no longer covers the
  request is omitted rather than answered from Holdings nothing would refresh →
  [architecture §Reservoir](../../../architecture.md#reservoir), corrected in
  [RFC 0014 d.1](../../../rfc/done/0014-20260808-reservoir-retention-pipeline.md) (whose pseudocode had
  specified the hole), pinned by `test_parameter_whose_reach_left_the_window_is_not_served_from_holdings`.
- **One clock, structurally** — `compose` takes the clock and builds the `StoreFactory` from it, so
  eviction and freshness cannot diverge → [ADR-0005](../../../adr/0005-build-time-composition.md),
  [architecture](../../../architecture.md), [module-layout](../../../module-layout.md),
  [edge/embedding](../../../edge/embedding.md).
- **Four failure classes share two wire categories** (capability / composition / **unbuilt** /
  **invariant break**), and an engine invariant break must not reach a product surface wearing a
  producer's fault → [#39](../../../concerns.md#39-python-embedding-surface-and-public-failures)'s
  inventory, `TODO(#39)` at the five leak sites, agenda item on
  [0125](../../../tickets/01-0125-supported-python-embedding.md).
- **The divergence guard is re-homed to the fold that owns it** —
  `test_winner_domains_that_differ_fail_the_whole_request` (no network, no store) →
  [#43](../../../concerns.md#43-narrow-answering-providers-re-open-mixed-request-run-divergence),
  [edge/provider](../../../edge/provider.md), RFC 0014 fact 3.
- **`unit` → `Holding`** for the store's atomically replaceable grain; the word `unit` stays with
  physical units → [glossary](../../../glossary.md) (`Holding / Holdings`, one entry), swept through
  ADR-0001/0002/0006, architecture, edge/provider, concerns, `store.py`, `reservoir.py`, and the
  store tests. Dated records keep "unit", per the ticket-renumbering precedent.
- **Geometry checks belong to geometry** — `as_enumerable_axes` moved from the `Reservoir` into
  `domain.py` beside `as_separable`, returning rather than raising →
  [ADR-0002](../../../adr/0002-data-model.md)'s Separable clause.
- **The relabel stays the Reservoir's, and its 007 split is pre-decided** — kernel to `sampling.py`,
  claim stays → `TODO(0117)` in [reservoir.py](../../../../src/meteoscape/nodes/reservoir.py).
- **Retention's caller-visible promise is on the record** — a repeat inside the freshness window
  returns the same values with no upstream trip and never stale ones, so `exp` is a usable staleness
  bound → [edge/mcp.md](../../../edge/mcp.md) Invariants; Roadmap 2 struck.

## Open questions

All owned elsewhere; none live only here:

- **Typed T-extent reads are duplicated three ways** — carve a `domain.py` narrowing helper or keep
  local copies → [#22](../../../concerns.md#22-lattice-helpers-vs-domain--sampling-module-split),
  `TODO(#22)` on `_request_t_bounds`.
- **The public failure hierarchy** (one class or two for unbuilt vs invariant break; which failures
  stay uncaught) → [#39](../../../concerns.md#39-python-embedding-surface-and-public-failures), decided at
  [0125](../../../tickets/01-0125-supported-python-embedding.md)'s align.
- **Bare `assert`s as the invariant-break mechanism** — counted in #39's table, deliberately
  untagged until the align decides whether asserts are intended there.
- **`Natural fetch unit` keeps the word `unit`** — it names the *provider's* answer granularity, not
  the store's grain; rename only if the collision proves confusing → [glossary](../../../glossary.md).

## Advice notes

- **What went well:** the review rounds compounded — each lens caught a class the previous one was
  structurally blind to, and the two most valuable findings (the vacuous tests) came from *doubting
  passing tests*, not from reading new code.
- **What to watch:** twice this session a green suite hid a defect because a test asserted *that*
  something failed without asserting *which* failure. Worth a rule in `/tdd` or `/review-impl`:
  assert the sentence, not the exception class.
- **Process observation:** three defects this session originated in a doc (RFC 0014's pseudocode
  specified the admission hole; the RFC named `servable`; the ticket claimed transport-level evidence
  it did not have). The `/plan-impl` unambiguity rules are working as intended — the plans were
  followed faithfully — which puts the remaining leverage on reviewing *plans* adversarially, not
  just implementations.

## Continuation

- **Commit the tree** — the slice-4 landing plus this session's fixes across code, tests, and ~15
  docs are uncommitted; the `Holding` rename touches both code and docs, so it wants its own commit.
- **Next in the queue is [0125 — supported Python embedding surface](../../../tickets/01-0125-supported-python-embedding.md)**
  (own align precedes), which now opens with #39's failure-class inventory in hand;
  [007 — off-grid homogenization](../../../tickets/done/01-0117-off-grid-homogenization.md) carries the
  `TODO(0117)` relabel split.
- **`Reservoir.held`** is dead instance state (never read or written) — flagged, left in place.
