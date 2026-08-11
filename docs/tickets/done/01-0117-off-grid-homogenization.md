# Off-grid homogenization

**Legacy id:** 007

- **Status:** Done — behaviour landed with 006; this ticket guarded it with tests and stated it on
  the Coverage contract and the MCP edge record (2026-08-10).
- **Depends on:** [006 — Retentive store](./01-0115-retentive-store-freshness.md)
- **Plan:** [RFC 0016](../../rfc/done/0016-20260810-off-grid-homogenization.md) — align 2026-08-10; guard
  ticket, no `src` logic changes.
- **Outcome:** Enclosing-cell read-back onto the requested point — guarded by Reservoir and e2e
  tests; Coverage-contract invariant on the architecture record; MCP fidelity-floor invariant
  validated by `test_points_within_one_store_cell_share_one_vendor_call`.

> **Noted at the 2026-08-10 beeline align.** A weather station is an off-grid point, so pairing a
> station observation with the forecast *at that station's coordinates* rides this read-back. The
> station/correction workstream ([02-0130](../02-0130-mongo-obs-source.md) →
> [02-0140](../02-0140-correction-calculator.md)) therefore reads through it — but it is **not blocked
> on it**: the point-exact half already landed (below). 007 stayed at the head of the queue because it
> closed the retention path, not because the correction work waits on it.
>
> **What 006 already delivered** (verify, do not rebuild):
>
> - *Point-exact reporting* — pinned X/Y pass through `ground` by identity, and `_relabel_onto`
>   writes the Holding's values onto the request's own coordinates. An off-grid lat/lon already
>   returns values **at the requested point**; [`test_e2e_forecast.py`](../../../tests/deterministic/test_e2e_forecast.py)
>   exercises one.
> - *A configurable, validated step* — `StoreSpec.spatial_step`, `Settings.store_spatial_step`
>   defaulting to 0.0001°, and the Open-Meteo catalogue shipping `StoreSpec(spatial_step=0.0001, …)`.
>
> **What actually remained was evidence, not code.** An earlier draft of this note said the ticket would
> *give the identity Resampler its own home* — that was written before the split was checked, and is
> **superseded**: it already has one. `Reservoir._relabel_onto` is the **claim** (which cell may
> answer) and `sampling.resample`, reached through `CoverageSet.project`
> ([coverage.py:115](../../../src/meteoscape/manifold/coverage.py)), is the **transfer**. Nothing
> relocated, and no Resampler registry was built here (see *Not in scope*).

## Parent PRD

`docs/v1-requirements.md`

## What to build

Answer an **off-grid** lat/lon **at the requested point** via read-time homogenization (S). Each
`Reservoir` quantizes the request onto its `Store`'s declared spatial grid for retention and
**homogenizes back onto the request at read**: when the request rides the grid it is a lossless crop
(identity); when it is off-grid the value is read from the **enclosing**
store cell (cached-fresh or refilled) and reported at `sel.domain`. The v1 read-back
**Resampler is identity** — no interpolation, one
rule for every Parameter; `valid_time` stays hourly-aligned (identity). The store's spatial step is
**configurable** (coarser = more cache sharing + more approximation error: with an identity Resampler,
a coarser cell means the unchanged value reported at the requested point was fetched from farther away).

> **Resolved in the 2026-08-10 align — *enclosing*, not *nearest*.** "Nearest enclosing" named no
> cell: there is exactly one enclosing cell, and *nearest* is only a question when several candidates
> exist. Under v1's shape none ever do — provider records are point-shaped (`_relabel_onto` asserts
> count-1 on X/Y) and the store is a **sparse cache** holding only cells already asked for, so the one
> cell guaranteed to hold data is the one the request quantized to. *Enclosing* is therefore both the
> accurate word and the one already decided:
> [ADR-0006](../../adr/0006-materialization-granularity-and-store-shape.md) fixes `quantize` as the
> containing cell's tick, and the glossary reserves *round* against it.
>
> **Consequence for this ticket:** there was no cell-selection change to make. Choosing *nearest*
> instead would have meant amending ADR-0006 and the glossary to let `quantize` round — buying a
> ≤½-step error bound that only matters if the store step coarsens, which is the
> [ledger](../02-0124-vendor-call-ledger.md)'s question, not this one.
> [v1-requirements §4](../../v1-requirements.md) corrected to match.

Parameter-specific Resamplers and a provider `exact` capability stay deferred. See
`docs/v1-requirements.md` (Request / tool contract, acceptance §4) and `docs/architecture.md`
(Normalization vs. homogenization, Reservoir).

## Not in scope

- **[#21](../../concerns.md#21-serves-extent-vs-project-crop-ability) is not closed here.** That concern
  used to name this ticket ("registry at 007"); it was repointed on 2026-08-10. The identity Resampler
  lives in the `Reservoir`'s read-back and adds no Resampler *registry*, so `serves` still admits
  off-phase / different-step selections that `resample` then refuses. Its trigger is now the first
  request that is genuinely off-phase or on a different step.
- **The store step is not revisited.** Whether the lattice stays a per-point cache (0.0001°, no
  spatial sharing) or coarsens into a sharing lattice is a vendor-spend question, and belongs where
  the spend is visible — the [vendor-call ledger](../02-0124-vendor-call-ledger.md).
- **No Resampler registry or `ParameterDef` selector.** The claim/transfer split the "What to build"
  section describes is **already the shipped shape** — `Reservoir._relabel_onto` is the claim,
  `sampling.resample` (via `CoverageSet.project`) is the transfer — so nothing relocates. Building a
  registry against its single identity implementation would guess a shape
  [ADR-0004](../../adr/0004-producer-resolution-and-capability.md) defers to
  [#5](../../concerns.md#5-read-time-homogenization-fidelity) along with the Resampler choice.
- **No coordinate echo on the MCP wire.** `serialize_coverage` drops the answered X/Y; that is a
  per-surface serialization gap filed on the [MCP edge record](../../edge/mcp.md#roadmap), additive and
  compatible when wanted. Which cell *sourced* a value is
  [#14](../../concerns.md#14-resolution-trace-and-observability)'s, and is not provenance
  ([ADR-0003](../../adr/0003-provenance-and-origin.md)).

## Acceptance criteria

- [x] A request for an off-grid lat/lon returns values **at the requested point**, sourced from the
      enclosing store cell (cached-fresh or refilled). *Landed with 006 — guarded by
      `test_off_grid_request_is_answered_at_the_requested_point`.*
- [x] An on-grid request degenerates to a lossless crop (the identity Resampler's on-lattice case).
      *Guarded by `test_on_grid_request_is_the_identity_crop`.*
- [x] `valid_time` remains hourly-aligned (identity on the time axis). *Already guarded — MCP edge
      record cites `test_mcp_app.py` serializer tests.*
- [x] The store spatial step is configurable (not hardcoded); native/store fidelity is recoverable
      server-side via the provenance `SourceKey` — **not** a dedicated provenance field
      ([ADR-0003](../../adr/0003-provenance-and-origin.md)). *Step validation at `store.py`; per-offering
      override at `test_composition.py`.*
- [x] `store_spatial_step` defaults to **0.0001° (~11 m)** — a per-point cache: near-exact values
      under the identity Resampler, spatial sharing only for repeat coordinates (the agent case).
      *Default at `test_config.py`; Open-Meteo catalogue ships `spatial_step=0.0001°`.*
- [x] Unit + mocked-transport integration tests cover on-grid crop and off-grid enclosing-cell
      read-back. *`test_reservoir.py` (1a–1d) and
      `test_points_within_one_store_cell_share_one_vendor_call`.*
- [x] The Coverage-contract invariant is stated and guarded: an off-grid request returns a Coverage
      whose X/Y are the **requested** coordinates, carrying the enclosing store cell's values.
      *Stated on [architecture §Reservoir](../../architecture.md#reservoir); guarded by the Reservoir
      tests above.*
- [x] The [MCP edge record](../../edge/mcp.md) gains the caller-observable consequence — under a coarse
      store step, two distinct points inside one cell return identical values — with its
      *validated by:* citation.

## User stories addressed

- User story 7
- User story 15
