# Unit-conversion catalogue

**Legacy id:** 010

- **Status:** Planned
- **Depends on:** [002 — Core canonical parameters](./done/01-0030-core-5-parameters.md)
- **Trigger:** The first vendor whose unit spread outgrows one hardcoded factor. TWC uses the same
  inline `km/h → m/s` edge as Open-Meteo, so the trigger remains unmet.
- **Outcome:** Shared verified native-to-canonical conversion edges.

## Parent PRD

`docs/v1-requirements.md`

## What to build

The **general unit-conversion catalogue** — a shared factor/offset library keyed by
`(from_unit, to_unit)`, lifting the
ad-hoc per-`Tap` factors ticket 002 ships into one place and recording each edge's **lossless vs
degrading** quality ([concern #10](../concerns.md#10-parameter-conventions); degrading edges are a
quality signal, not silent).

**Not this ticket — the v1 per-`Tap` convert-on-ingest position** (verify-always, no request knob,
wind `km/h→m/s` inline) lands at 002 → [ticket 002 §Units](./done/01-0030-core-5-parameters.md). This ticket
is only the shared catalogue those inline factors graduate into.

## Acceptance criteria

- [ ] Per-`Tap` native→canonical conversions (002) are re-expressed through the shared library — no
      conversion factors inline in provider leaves.
- [ ] Conversions are looked up by unit pair; a pair with no registered edge is `runtime-failure`
      (never a silent guess), preserving 002's verify-always guard.
- [ ] Lossless vs degrading is recorded per edge (concern #10); v1 edges are all lossless
      factor/offset.
- [ ] Unit tests cover a multi-vendor unit spread (the same canonical parameter served in different
      native units by two providers) converging to one canonical unit.

## User stories addressed

- User story 4
