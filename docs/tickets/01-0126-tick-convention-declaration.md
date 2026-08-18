# Tick-convention declaration

- **Status:** Planned (own align precedes)
- **Depends on:** [011 — TWC provider](./done/01-0120-twc-provider.md), which supplies the second real
  convention and prevents an Open-Meteo-specific default.
- **Outcome:** A tap declares where its value sits relative to the tick, and Open-Meteo's
  precipitation stops being labelled an hour late.

## The defect this repairs

`TimelineProvider` assigns every field the following cell `[T, T+step]`. Open-Meteo precipitation is
the preceding-hour total, so its values are labelled one hour late; TWC's forward-looking `qpf`
demonstrates the second convention. The declaration gap and parity blind spot are owned by
[#48](../concerns.md#48-a-tap-cannot-declare-where-its-value-sits-relative-to-the-tick).

## What to build

Add per-field declarations for **which temporal cell** owns a value and **which statistic** the vendor
already computed. Records split by temporal convention as they already split by Z level. The align
must settle whether cell side belongs on the tap, `ParameterDef`, or the axis, and whether
instantaneous parameters remain cellular. Open-Meteo and TWC precipitation must each retain their
native window semantics.

## Acceptance criteria

- [ ] A tap can declare where its value sits relative to the tick; Open-Meteo's precipitation declares
      the preceding hour and TWC's `qpf` the following one, each from its own vendor documentation.
- [ ] The published meaning in [parameters.md](../parameters.md) is true of every shipped provider,
      and its temporary caveat is removed.
- [ ] A deterministic test pins the window each provider's precipitation carries — the guard parity
      structurally cannot supply.
- [ ] Records split by T-convention where the shape requires it, without disturbing the Z-level split.
- [ ] No change to what any *intensive* parameter reports.
