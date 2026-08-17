# Sample-level allowance — implementation plan

**Authored:** 2026-08-17
**Last amended:** 2026-08-17 (closing note, post-implementation)

Implementation plan for [sample-level allowance](../../tickets/done/01-0118-sample-level-allowance.md).

**As landed:** `compose_domains(definition, candidates)` — the `ParameterDef` **replaced** the
`ParameterId` first argument rather than riding beside it as sketched below; `definition.id` serves
the error messages. A deliberate improvement (the pid would have been redundant), recorded here so
the deviation is a decision, not drift.

**Scope in one line:** the reach-composition fold learns the sample-vs-span distinction on Z and
reads the Parameter's declared band; `ParameterDef` gains the optional `z_allowance`; the calculator
fold and every admission path are untouched. Unblocks [0120](../../tickets/01-0120-twc-provider.md).

## Boundaries involved

| Boundary | Owner | What this does to it |
|---|---|---|
| Reach composition (dominance fold) | [ADR-0007](../../adr/0007-capability-carries-its-domain.md) (2026-08-17 amendment) | Implements the amendment: two sample-Z levels compose iff equal (a tie) or both in the Parameter's band; a sample-vs-span pair under a banded parameter fails; span cells keep containment. |
| `contains_extents` / `first_incomparable` / `split_extents` | [domain.py](../../../src/meteoscape/manifold/domain.py) | Gain an **optional** band argument, default `None` = today's behavior exactly. Geometry stays parameter-blind — it receives a plain band, never a `ParameterDef`. |
| `Reconciler.compose_domains` | [ADR-0004](../../adr/0004-producer-resolution-and-capability.md) / [arbiter.py](../../../src/meteoscape/nodes/arbiter.py) | Signature is `compose_domains(definition, candidates)` — the def *is* the parameter (`id` names the error, `z_allowance` is the band). `select` still takes the id. |
| `ParameterDef` | [ADR-0002](../../adr/0002-data-model.md) (amended this pass) | New optional field `z_allowance: tuple[float, float] \| None` — named for its axis, matching the domain-seam argument. Plain floats, **not** `Interval`: `parameters.py` imports nothing from `manifold` (verified), and this ticket does not invert that layering. |
| v1 band content | [parameters.md § Sample-level allowance](../../parameters.md#sample-level-allowance) | `StaticParameterTable.core()` realizes the table: `(1.25, 2.0)` for `air_temperature` and `relative_humidity`, `None` elsewhere. |
| Calculator reach fold (`_contained_in_all`) | [calculator.py](../../../src/meteoscape/nodes/calculator.py) | **Untouched.** It folds across *different parameters* (an input set), where no single parameter owns the band; its default-`None` call keeps pure containment. See Limitations. |
| Admission (`serves`, `matches`, `VantageAxis`) | [ADR-0002](../../adr/0002-data-model.md), [ADR-0004](../../adr/0004-producer-resolution-and-capability.md) | **Untouched.** The request-side vantage already admits both levels against each member's own footprint; `UnionCapability.serves` delegates to members and never reads the composed domain. |
| MCP edge | [edge/mcp.md](../../edge/mcp.md) | **Unchanged.** Reach readers consume only the T extent ([mcp_app.py:159](../../../src/meteoscape/api/mcp_app.py), [:219](../../../src/meteoscape/api/mcp_app.py)). |

## Facts about the tree (verified 2026-08-17)

1. **The fold is dominance-or-raise over `AXIS_ORDER`, which includes Z**
   ([arbiter.py:105-117](../../../src/meteoscape/nodes/arbiter.py),
   [domain.py:428-431](../../../src/meteoscape/manifold/domain.py)). Two degenerate Z extents at
   different levels fail containment both ways — **verified live**: composing a 1.5 m footprint
   against Open-Meteo's 2 m raises `incomparable reach footprints … on z` (the control with both at
   2 m composes, T dominance working as documented).
2. **`contains_extents` has exactly two callers**: the reconciler's fold and the calculator's
   inverted fold — plus `first_incomparable`, which both use for the witness. An optional
   default-`None` argument therefore changes nothing it does not explicitly opt into. There is
   still **one `Reconciler` implementor** (`PriorityReconciler`); no test double implements the
   protocol.
3. **`compose_domains` is called from one production site**, `Arbiter.__init__`
   ([arbiter.py:151](../../../src/meteoscape/nodes/arbiter.py)); stage 3's headline test constructs
   an `Arbiter` so that threading is proven, not only the reconciler method. Direct constructions
   in [test_arbiter.py](../../../tests/deterministic/nodes/test_arbiter.py) (~8 call sites) pass the
   def in the same stage.
4. **The `ParameterDef` is already at the call site.** Every candidate indexed under a parameter
   publishes it: `candidate.node.capability.parameters[parameter]`
   ([capability.py](../../../src/meteoscape/manifold/capability.py)) — no new plumbing, no second
   defs map. All members resolve defs from the one `ParameterTable` at build, so any candidate's
   copy is the def. `UnionCapability.serves` still delegates to members and never reads the
   composed domain ([capability.py:129-132](../../../src/meteoscape/manifold/capability.py)).
5. **A sample level is a degenerate Z extent** (`lower == upper`): footprint and record Z for POINT
   mode is `RegularAxis(name, level, 1.0, 1, cellular=False)`
   ([timeline.py:517-521](../../../src/meteoscape/nodes/providers/timeline.py)); SPAN mode is an
   `IntervalAxis` with `lower < upper`. No shipped Z is a degenerate span, so extent degeneracy is
   the discriminator — representation-blind and enumeration-free. It is also **cellular-blind**:
   `RegularAxis.extent` spans ticks, never cell bounds ("cellular only affects `Cell.bounds`, never
   axis geometry", [domain.py:185](../../../src/meteoscape/manifold/domain.py)), so a count-1 Z reads
   degenerate under either cellular flag — a future materialized source cannot dodge the rule by
   representation.
6. **Composed-reach consumers**: the MCP edge and the Reservoir read T only
   ([mcp_app.py:159](../../../src/meteoscape/api/mcp_app.py),
   [:220](../../../src/meteoscape/api/mcp_app.py)); the calculator fold reads all axes but over inputs
   that share `Z_10M`. Nothing shipped reads the composed Z — the change is still contract-honest
   because Reach is published ([ADR-0007](../../adr/0007-capability-carries-its-domain.md)).
7. **`ParameterDef` reaches no wire**: no `asdict` exists anywhere in `src`, and the MCP edge
   builds its payload field-by-field without touching defs — so the new field is invisible to every
   serialized surface; adding it is compatible by construction, not by luck. No test constructs a
   `ParameterDef` by hand, so the optional field with a default cannot break existing equality.
8. **`Interval.contains` is inclusive on both ends**
   (`lower <= other.lower and other.upper <= self.upper`,
   [domain.py:56-57](../../../src/meteoscape/manifold/domain.py)). Converting the WMO pair
   `(1.25, 2.0)` to an `Interval` therefore admits Open-Meteo's native 2 m — the upper bound is not
   a fence-post.
9. **The rule and the witness math were simulated over real footprints**: all eight scenarios —
   headline 1.5 v 2 (winner is Open-Meteo's own object), outside-band, equal-outside tie, no-band
   refusal, mixed-under-band, span containment, and both three-candidate coherence sets — behave as
   specified, and **no case reaches the fold's no-winner-no-witness `assert`**: the Z arm
   (equal-or-both-in-band) is a preorder, so a finite set with no maximum has an incomparable pair.
   The stage-3 tests re-prove this in-tree.

## Code shape

**`parameters.py`** — the leaf stays manifold-free:

```python
@dataclass(frozen=True)
class ParameterDef:
    id: ParameterId
    quantity: Quantity
    canonical_unit: Unit
    statistic: CellStatistic
    z_allowance: tuple[float, float] | None = None
    """The Allowance: metres above ground, inclusive band of sample levels this parameter's
    consumers accept as interchangeable (ADR-0007, parameters.md § Sample-level allowance).
    `None` = exact level match required. A fact of the parameter, never of a producer. Named for
    its axis, matching the `z_allowance` argument on the domain comparison seam."""
```

**`paramtable.py`** — `core()` sets `z_allowance=(1.25, 2.0)` on `air_temperature` and
`relative_humidity`; every other def is untouched (field defaults to `None`).

**`domain.py`** — the three comparison helpers gain `z_allowance: Interval | None = None`
(an `Interval` here — this module owns the type; the caller converts the def's plain pair). The
rule, applied **only to `AxisName.Z`** and only when `z_allowance` is given:

```
both extents degenerate      → True iff levels EQUAL or both lie in the band (either direction)
exactly one degenerate       → False (a banded parameter's Z is a sample level; a span candidate
                               under that id is a modeling violation to surface, not absorb)
neither degenerate           → containment, as today
z_allowance is None          → containment, as today (degenerate pairs then require equality,
                               which containment already is at a point)
```

The equal-levels arm is load-bearing, not redundant *(added on the second pass)*: without it, two
producers agreeing on a level **outside** the band would refuse — but equal extents are a **tie**,
and [ADR-0007](../../adr/0007-capability-carries-its-domain.md) resolves ties ("tied candidates state
the same promise"). The band is a **licence that extends composability, never a constraint that
narrows it** — which is also what makes no-band behavior a strict subset and stage 1's
byte-for-byte pin true. (Equality falls out of containment anyway; the rule states it so nobody
"simplifies" the band arm into the only arm.) Two boundary notes:

- **A lone candidate stays unchecked, banded or not** — ADR-0007's lone-candidate rule; the band
  constrains comparison, and one candidate compares against nothing.
- **Mixed sample/span with no band keeps today's containment** (span ⊇ point → composes) —
  unreachable in v1, since no parameter is served both ways; the mixed-pair refusal is scoped to
  banded parameters ([ADR-0007](../../adr/0007-capability-carries-its-domain.md)).

`split_extents` under the same argument names the refusal honestly: a level outside the band reports
`z level {v} outside allowance [{lo}, {hi}]` instead of the mutual "extends beyond" pair, so the
reconciler's error — which already names the parameter and producers — carries the actionable fact.

**`arbiter.py`** — the protocol and its one implementor:

```python
class Reconciler(Protocol):
    def compose_domains(
        self, definition: ParameterDef, candidates: ...
    ) -> Domain: ...
```

`Arbiter.__init__` passes `candidates[0].node.capability.parameters[parameter]` (fact 4).
`PriorityReconciler` converts once — `band = None if definition.z_allowance is None else
Interval(*definition.z_allowance)` — and threads it to `contains_extents`, `first_incomparable`, and
`split_extents`. Errors name `definition.id`. Dominance is then decided on the remaining axes exactly as today, and **the
winner's own `Domain` is returned unchanged** — its Z stays its native level, which is what keeps
ADR-0007's tightness/liveness/representation triple intact. When remaining axes also tie, the
existing first-containing-all loop returns the first candidate (bind order); the composed Z is that
candidate's native level and may differ from the other's, unread until
[#29](../../concerns.md#29-narrated-reach-what-a-profile-promises).

What does **not** change: `select`, admission, `UnionCapability`, the Calculator fold, every
Reservoir and edge path, and `_contained_in_all`'s call (default `None`).

## Stages

### Stage 1 — the predicate *(red → green)*

`domain.py`: the `z_allowance` argument on the three helpers. Tests in
`tests/deterministic/manifold/test_domain.py` prove the matrix, each case asserting the *reason*:

- band + both degenerate, both inside (1.5 vs 2.0 in `[1.25, 2.0]`) → contains both directions
  (the tie that lets other axes decide);
- band + one outside (30.0) → `False` both directions, and `split_extents` names the level and the
  band — not the mutual extends-beyond pair;
- band + mixed sample/span → `False` both directions;
- band + neither degenerate → containment (band ignored);
- **no band → byte-for-byte today's behavior**, pinned by the existing suite passing untouched.

### Stage 2 — the declaration *(green)*

`ParameterDef.z_allowance` + the two `core()` bands. One test asserts the banded set is exactly
`{air_temperature, relative_humidity}` with `(1.25, 2.0)` — pinning code-vs-[parameters.md](../../parameters.md)
agreement, the file's own normative claim.

### Stage 3 — the fold *(green)*

Protocol + `PriorityReconciler` + `Arbiter` threading; test_arbiter's direct `compose_domains`
calls pass the def (a plain helper def suffices). New tests:

- **the ticket's headline, through `Arbiter` construction**: two synthetic producers declaring
  `air_temperature` at 1.5 m / 2 m (TWC-shaped and Open-Meteo-shaped cadences) compose; the
  published reach `is` the T-dominant candidate's own `Domain` object — identity, not equality,
  pinning "an existing Domain, never synthesized" *and* that `__init__` threads the def. Direct
  `compose_domains` calls cover the other cases;
- 1.5 m vs 30 m raises `CompositionError` naming the parameter, both producers, the axis, and the
  band — asserted on the message;
- **two producers at the same level outside the band compose** (30 m vs 30 m under `[1.25, 2.0]`)
  — pinning the licence-not-constraint semantics and the ADR-0007 tie law against a future
  "simplification" of the equal-levels arm;
- no-band parameter (wind at 10 m vs 9 m) still raises — the allowance cannot silently become
  "any two points compose";
- cloud cover's span composition unchanged;
- full suite green.

### Stage 4 — records *(green)*

Tick the ticket into `done/`; discharge the **⚠ unimplemented** in
[parameters.md § Sample-level allowance](../../parameters.md#sample-level-allowance); flip
[0120](../../tickets/01-0120-twc-provider.md) to **Ready** and update the queue's current stage.

## Limitations and follow-ups

- **The calculator fold keeps pure containment.** `_contained_in_all` compares reaches of
  *different* parameters, where no single def owns the band; v1's only calculator reads two inputs
  at one level. A future cross-level calculator (e.g. heat index over 1.5 m temperature and 2 m
  humidity through mixed winners) re-opens this — at that point the question is which parameter's
  band licenses a cross-parameter comparison, and it lands beside
  [#38](../../concerns.md#38-calculator-admittance-is-fixed-pointwise-total)'s admittance work, not here.
- **The composed reach's Z publishes the winner's level** while a non-winning member may answer at
  its own — within the band by construction, and unread by any shipped consumer (fact 6). The
  narrated-reach surface that would expose Z is [#29](../../concerns.md#29-narrated-reach-what-a-profile-promises)'s.
- **Band content beyond v1** (further parameters, non-vertical sample axes if one ever exists) →
  [#10](../../concerns.md#10-parameter-conventions).
- **Witness/attribution duplication in geometry** is unchanged in shape and stays at
  [#46](../../concerns.md#46-composition-failure-attribution-is-paid-inside-geometry) — this adds one
  argument, not a second reporting path.
