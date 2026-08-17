# Sample-level allowance

- **Status:** Done — 2026-08-17
- **Type:** AFK
- **Plan:** [Sample-level allowance RFC](../../rfc/done/01-0118-sample-level-allowance.md) — band on
  `ParameterDef` as plain floats (layering), the Z rule scoped to the reconciler's fold via an
  optional argument, `compose_domains` takes the def; calculator fold and admission untouched.
- **Blocks:** [TWC provider](../01-0120-twc-provider.md) — its native 1.5 m screen height against
  Open-Meteo's 2 m makes key-present composition fail at boot until this lands.
- **Outcome:** Two producers declaring the same parameter at nearby sample levels compose into one
  profile — the fold treats sample levels inside the Parameter's declared allowance as
  interchangeable instead of demanding point containment; a level outside the band still fails the
  build by name.

## Parent

[ADR-0007 § Composition rules](../../adr/0007-capability-carries-its-domain.md) (the 2026-08-17
amendment: *sample levels compose by Allowance, not containment*) and
[parameters.md § Sample-level allowance](../../parameters.md#sample-level-allowance), which carries the
v1 bands. Both landed at the 2026-08-17 align; this ticket is their runtime realization.

## What goes wrong today

Reach composition is dominance-or-raise by per-axis extent containment, uniformly over all four
axes. On a **sample**-level Z pair, containment degenerates to point equality:

```
                Z declaration          [2,2] ⊇ [1.5,1.5]?   [1.5,1.5] ⊇ [2,2]?
Open-Meteo      sample @ 2 m                 no                    —
TWC             sample @ 1.5 m               —                    no
                                     ⇒ incomparable ⇒ CompositionError at boot
```

Both are ordinary screen heights — the producers do not disagree about coverage; the fold is asking
a coverage question of a fact that is not coverage. Verified live: composing the two footprints
raises `incomparable reach footprints for air_temperature … on z`, so the first key-present TWC
boot fails. The distinction the fold is missing is one
[parameters.md § Vertical carriage](../../parameters.md) already draws: a **sample** level (count-1
point cell) versus a **statistic span** (cloud cover's `[0, TOA]` column), where containment is
genuinely the right question — the maximal-served-cell rule.

## What to build

The composing fold learns the sample-vs-span distinction. Where both candidates declare a
**sample** cell on an axis, the pair composes iff both levels lie inside the **Parameter's declared
allowance** ([parameters.md § Sample-level allowance](../../parameters.md#sample-level-allowance));
dominance is then decided on the remaining axes, and the winner's own `Domain` is returned
unchanged — its level stays its native one, honest within the band. Statistic **span** cells keep
containment, and **equal levels always compose** — a tie states one promise, so the band is a
licence that extends composability, never a constraint that narrows it *(sharpened 2026-08-17,
second RFC pass)*. An **unequal** pair not both inside the band, or a sample-vs-span pair under a
**banded** parameter, is a genuine incomparability and fails the build with the existing named
error.

Constraints, each with its reason:

- **The allowance is the Parameter's declaration, never a producer's** — a leaf widening its own
  acceptability would be policy smuggled into a declaration, and the shared fold stays
  provider-blind (the align's boundary rule: shared shapes host no provider-specific logic).
- **Leaves still declare native facts, never widened** — the band bounds the *comparison*, not the
  declaration ([parameters.md](../../parameters.md)).
- **Composition still returns an existing `Domain`, never a synthesized one** — tightness by
  construction, liveness of `RollingAxis`, representation survival
  ([ADR-0007](../../adr/0007-capability-carries-its-domain.md)).
- **An absent allowance means exact** — wind at 10 m and surface precipitation keep today's
  behavior until a differing vendor forces a band.

## Acceptance criteria

- [x] Two producers declaring `air_temperature` at `1.5 m` and `2 m` (synthetic candidates — TWC
      itself lands at [0120](../01-0120-twc-provider.md)) compose; the composed reach is the
      axes-dominant candidate's own `Domain`, its Z that candidate's native level.
- [x] An **unequal** sample-level pair not both inside the band still fails the build with the
      error naming the parameter, both producers, and the axis — pinned so the allowance cannot
      silently become "any two points compose" — while an **equal** pair composes even outside the
      band *(sharpened 2026-08-17: a tie states one promise; the band licenses, never narrows)*,
      pinned so the band cannot silently become a validity constraint on declarations.
- [x] A parameter with no declared allowance composes only on equal sample levels — today's
      behavior, pinned.
- [x] Statistic-span composition is untouched: cloud cover's column still composes by containment.
- [x] The full deterministic suite stays green — identical-level pairs (wind at 10 m twice) see no
      behavior change.
- [x] The **⚠ unimplemented** marker in
      [parameters.md § Sample-level allowance](../../parameters.md#sample-level-allowance) is
      discharged.

## Out of scope

- **The TWC leaf and the live pairing** — [0120](../01-0120-twc-provider.md), which depends on this.
- **Request-side Z admission** — untouched; the `VantageAxis` already admits both levels against
  each member's own footprint ([ADR-0002](../../adr/0002-data-model.md),
  [ADR-0004](../../adr/0004-producer-resolution-and-capability.md)).
- **Value-side homogenization between levels** — serving a 2 m value at a 1.5 m ask is the identity
  Resampler's relabel today; parameter-specific fidelity stays at
  [#5](../../concerns.md#5-read-time-homogenization-fidelity).
- **Band content beyond v1** — the conversion-edge and convention questions stay at
  [#10](../../concerns.md#10-parameter-conventions).
