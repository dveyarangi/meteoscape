# Manifold geometry carved for navigation

- **Status:** Planned
- **Type:** AFK
- **Kind:** Maintenance
- **Depends on:** [scatter substrate](./done/01-0124.0010-scatter-substrate.md) (lands first so the
  carve is not entangled with a reviewed feature diff)
- **Outcome:** `manifold/domain.py` (858 lines, four distinct layers) becomes three navigable
  modules — the axis vocabulary, the lattice index arithmetic, and the Domain forms — with no
  contract or behavior change, the one-way import direction machine-enforced, and
  [#22](../concerns.md#22-lattice-helpers-vs-domain--sampling-module-split) closed into
  [module-layout](../module-layout.md).

## Parent

[#22](../concerns.md#22-lattice-helpers-vs-domain--sampling-module-split), whose named trigger —
a third consumer of the index arithmetic — has fired: `store.py:39,221,237` imports and uses
`sub_lattice_offset` (measured 2026-08-21; the concern's "two index-arithmetic sites" sentence
predates the retentive store). The wider carve is a navigation decision taken at the
[scatter substrate](./done/01-0124.0010-scatter-substrate.md) review: the file now spans value
primitives, five axis kinds, lattice math, extent algebra, and five Domain forms — four layers in
one 858-line module that every validation pass re-reads.

## What to build

A pure refactor — no signature, behavior, or contract changes:

- **`lattice.py`** (#22's own prescription): `encode_flat_index`, `decode_flat_index`,
  `sub_lattice_offset`, `AXIS_ORDER`, `_validate_four_axes` — imported one-way by `domain`,
  `sampling`, and `store`.
- **`axes.py`**: `Cell`, `Point`, `Interval`, `Axis` and its five kinds (`Regular`, `Interval`,
  `Vantage`, `Continuous`, `Snapped`, plus `EnumerableAxis`) — the coordinate vocabulary below
  domains. (`RollingAxis` stays in `cadence.py` with its clock, as today.)
- **`domain.py`** keeps what is left: `Separable` and the extent algebra, the narrowing helpers,
  the `Domain` forms (`Grid`, `Footprint`, `Scatter`, `Selection`, the `Curvilinear` stub), and
  request resolution (`ground`, `open_axes`, `agreed_geometry`).
- Importers name the new homes directly — **no compatibility re-exports** (one home per name;
  measured surface: five files import axis kinds directly, three import the lattice math).
- [module-layout](../module-layout.md) records the three-module cut and the import direction
  `lattice ← axes ← domain`, with `sampling`/`store` reading `lattice` directly.

## Acceptance criteria

- [ ] Full deterministic suite, `ruff`, format, and `pyright` pass with no test edited beyond
      import lines — behavior pinned unchanged by the suite itself, not by inspection.
- [ ] The import direction is machine-enforced: a guard test fails if `lattice` imports from
      `axes` or `domain`, or `axes` from `domain`.
- [ ] No compatibility re-exports: the moved names resolve only at their new homes.
- [ ] [module-layout](../module-layout.md) records the cut;
      [#22](../concerns.md#22-lattice-helpers-vs-domain--sampling-module-split) is closed into it
      (contact surface moves, stable anchor left per the retirement rule).

## Out of scope

- Any change to `Domain`/`Axis` semantics, `matches` behavior, or the sampler → those stay where
  their tickets put them.
- Splitting the Domain forms into per-form files — one algebra, one module.
