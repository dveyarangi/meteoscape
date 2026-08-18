# Unit-conversion catalogue

**Legacy id:** 010

- **Status:** Planned
- **Depends on:** [002 — Core canonical parameters](./done/01-0030-core-5-parameters.md)
- **Trigger:** The first vendor whose unit spread outgrows one hardcoded factor. TWC serves metric
  and reuses the same inline `km/h → m/s` edge as Open-Meteo, so the trigger stayed unmet there —
  falsifying the beeline prediction that placed this at 0122. The next plausible pull is the
  [Mongo obs source](./01-0130-mongo-obs-source.md)'s align, whose pinned collector fixtures
  ([#45](../concerns.md#45-the-collector-schema-is-a-contract-meteoscape-depends-on-but-does-not-own))
  reveal the native units of the per-provider forecast fields and station payloads. If those prove
  already canonical, this ticket slides again behind the next producer with a differing native unit.
- **Outcome:** Shared verified native-to-canonical conversion edges.
- **Position note:** renumbered 0122 → 0129 (2026-08-19) to sit just ahead of its first plausible
  customer; 0127/0128 were consumed by the docs gate and mover.

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
