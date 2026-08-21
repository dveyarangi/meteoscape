# Observation and forecast reaches compose

- **Status:** Planned (own align precedes)
- **Type:** HITL
- **Depends on:** [Mongo obs source station serving](./01-0124.0020-mongo-obs-serving.md) (a real
  scatter reach to compose beside the in-tree forecast reaches)
- **Blocks:** [correction calculator](./01-0140-correction-calculator.md) — its scoped input fold
  meets the same incomparability, so it cannot build until this lands.
- **Outcome:** A profile composing station observations and forecast producers over shared
  parameters builds and serves: a shared parameter's reach composes across a past-facing scatter
  and a forward-facing footprint instead of refusing the whole composition as incomparable.

## Parent

Carved at the [Mongo obs source](./01-0124-mongo-obs-source.md) align's impact trace (2026-08-21),
which found the cliff before implementation did. Durable context:
[#13](../concerns.md#13-candidate-admission-containment-vs-intersection),
[#28](../concerns.md#28-reconciler-interface-selection-ordering-vs-per-cell-fold),
[#29](../concerns.md#29-narrated-reach-what-a-profile-promises) (backward reach), and
[architecture § Extension points](../architecture.md#extension-points) — "obs + forecast along
`valid_time` are this one shape".

## What goes wrong today

`compose_domains` is dominance-or-raise (`arbiter.py`): every parameter with two or more candidates
requires all reaches separable and one reach to contain the rest per axis. An observation source
sharing `air_temperature` with any forecast producer shears on T — obs `[archive floor, now]`
against forecast `[now-ish, horizon]`, neither containing the other — so the *whole profile refuses
to build* on the first shared parameter. The calculator input fold (`_contained_in_all`,
`calculator.py`) applies the same rule to the correction calculator's paired inputs. ADR-0007's
fold deliberately returns an existing candidate `Domain`, never a synthesized one; obs+forecast is
the first pair for which no candidate can stand for both.

## Decisions this ticket's align owns

- Whether the composed reach becomes a richer structure than one candidate's `Domain` (the
  [#13](../concerns.md#13-candidate-admission-containment-vs-intersection) containment-vs-intersection
  fork, and [#29](../concerns.md#29-narrated-reach-what-a-profile-promises)'s claim that backward
  reach "should absorb without a contract change" — verified false at the fold by the 0124 impact
  trace) — cannot be answered before a real scatter reach exists to measure against.
- How serving policy relates: whether the T-split ("obs for the past, forecast for the future") is
  the reconciler's selection, a fold-level composition, or
  [#28](../concerns.md#28-reconciler-interface-selection-ordering-vs-per-cell-fold)'s first
  per-cell-fold slice — the deferred interface widening this pair was always going to trigger.
- Whether `Separable` is the right precondition once one legitimate candidate is jointly-matched —
  or the fold needs a weaker per-axis *extent* view (the same question the MCP `_t_extent` raise
  poses at the edge).

## Acceptance criteria (provisional — firmed at the align)

- [ ] A profile declaring the obs source and a forecast producer over shared parameters composes
      without `CompositionError`.
- [ ] A past window at a station serves observations; a future window at the same point serves the
      forecast — pinned end to end through `Gateway`, not by unit-testing the fold alone.
- [ ] The correction calculator's paired-input fold builds over the same pair
      ([correction calculator](./01-0140-correction-calculator.md) unblocked).

## Out of scope

- Per-cell blending (consensus/feather) beyond what the align selects →
  [#28](../concerns.md#28-reconciler-interface-selection-ordering-vs-per-cell-fold).
- Spatial widening of observation reach (inter/extrapolation) →
  [#37](../concerns.md#37-storeless-materialized-producers-and-read-back-homogenization) and
  [#5](../concerns.md#5-read-time-homogenization-fidelity).
