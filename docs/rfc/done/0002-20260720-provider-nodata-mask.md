# RFC 0002 — Provider nodata mask (ticket 002c)

- **Date:** 2026-07-20
- **Ticket:** [002c — Provider nodata mask](../../tickets/done/002c-provider-nodata-mask.md)
- **Depends on:** 002 (done) — the tap table, `Decode`, and the `present=None` shape it shipped
- **Status:** Accepted (implemented — 113 tests green, ruff + pyright clean; stages S1–S5 shipped as planned)
- **Owning docs:** [ADR-0002](../../adr/0002-data-model.md) (nodata encoding, `ParameterData`),
  [ADR-0004](../../adr/0004-producer-resolution-and-capability.md) (node well-formedness),
  [architecture.md §Failure, nodata, and availability](../../architecture.md#failure-nodata-and-availability)
- **Planning source:** session 0014 — the 002c align pass that cut the ticket to its live defect and
  moved presence behind `ParameterData` behaviour (committed as `c5dd2b9`; not yet written up)
- **Blocks:** [009](../../tickets/009-error-taxonomy-partial-success.md)

---

## 1. Summary

One live defect: a vendor `null` reaches the MCP wire as the token `NaN`, which is **not valid JSON**
(RFC 8259). [`cell()`](../../../src/meteoscape/nodes/providers/timeline.py) substitutes `nan` for a null
sample and [`open_meteo.normalize`](../../../src/meteoscape/nodes/providers/open_meteo.py) hardcodes
`present=None`, so the serializer's `null` branch is **dead for every real response**.

The fix is Provider-side and small. Three things follow from it:

1. **`Decode` returns `ParameterData`**, and a `pointwise(*vars, fn)` combinator owns the presence rule
   — *a tick is present iff every input vendor var is present at it* — so no decoder implements it and
   `fn` never sees a null.
2. **The masked-cell value is unspecified.** `nan` survives only as filler with a **single writer**
   (`pointwise`), never as the absence signal.
3. **`ParameterData` gains `of` / `is_present` / `take`**, retiring the two sites that branch on the
   `None`-means-all-present convention.

**Deliberately not in scope** (each cut during align, with the reasoning recorded): alignment
validation on `CoverageRecord` (→ [#31](../../concerns.md#31-positional-alignment-is-asserted-never-checked)),
wire-level NaN verification, per-parameter absence *reasons* (→ 009), and any change to
[`wind.py`](../../../src/meteoscape/nodes/calculators/wind.py) or `and_present`.

## 2. Decisions resolved during planning

**D1 — `of` elides only a *validated* mask; the length rule has exactly one home.**
The ticket gives `ParameterData` both an eliding constructor (`of` collapses an all-`True` mask to
`None`) and a validating one (`__post_init__` rejects `len(present) != len(values)`). If `of` computes
the elision itself and hands the *result* to the constructor, they compose with a gap:

```python
ParameterData.of(values=[1.0, 2.0], present=[True])   # mask too short
# all(present) is True  -> elided to None
# __post_init__ sees present=None -> nothing to check
# result: a malformed mask is silently accepted
```

A **short but all-`True`** mask evades both checks — elision destroys the evidence before validation
sees it. Every other malformed mask is caught, which makes it the worst kind of gap: the type looks
enforced.

**Resolution:** `of` constructs with the mask **first** (so `__post_init__` validates it), and only
then elides. The rule is written once, in `__post_init__`; `of` is a convenience layered on top of the
constructor rather than a parallel path around it, so the ordering cannot be got wrong later. Cost is
a second construction of a frozen two-field pair in the all-present case.

*(Rejected: duplicating the length check inside `of`. It works, but two copies of an invariant is how
they drift — and it leaves the gap one edit away from reopening. Also rejected, at align: eliding
inside `__post_init__`, which silently rewrites a caller's argument.)*

**D2 — `fn` receives present values positionally, in `vendor_vars` order.**
`pointwise("wind_speed_10m", "wind_direction_10m", fn=_u_component)` calls `fn(speed, direction)`. The
alternative (a `Mapping` per tick) was rejected: it re-introduces the vendor-name vocabulary into the
kernel, which is exactly what taps exist to hold. Consequence: `_wind_component(speed, direction, *,
u: bool)` splits into two thin binders, `_u_component` / `_v_component`, since `fn` takes no keywords.

**D3 — The serializer needs no change for the defect to die.**
[`serialize_coverage`](../../../src/meteoscape/api/mcp_app.py) already emits `null` when
`present[i]` is `False`; it was only ever unreachable because provider data never carried a mask. So
**stages S1–S3 fix the live defect end-to-end**, and the `mcp_app` / `sampling` work (S4–S5) is pure
refactor that must keep it green. This orders the build and is why the tracer test can be written
first.

## 3. Scope, boundaries, ownership

**In scope (code):** `manifold/data.py`, `nodes/providers/timeline.py`,
`nodes/providers/open_meteo.py`, `manifold/sampling.py`, `api/mcp_app.py`.

**Explicitly untouched:** `manifold/coverage.py` (no `CoverageRecord.__post_init__` — see #31),
`nodes/calculator.py`, `nodes/calculators/wind.py`, `nodes/arbiter.py`, `and_present`.

**Contracts touched:**

| Contract | Current | Target |
|---|---|---|
| `Decode` | `Callable[[Mapping[str, Sequence[float \| None]]], list[float]]` | `Callable[[Mapping[str, Sequence[float \| None]]], ParameterData]` |
| `cell(value)` | `float \| None -> float` (null → `nan`) | **deleted** |
| `passthrough(var)` | builds `[cell(v) …]` | thin `pointwise(var, fn=…)` wrapper |
| — | — | `pointwise(*vars: str, fn: Callable[..., float]) -> Decode` |
| `ParameterData` | frozen pair, no behaviour | `+ of` (classmethod), `+ is_present(i)`, `+ take(indices)`, `+ __post_init__` |
| `and_present` | module function in `data.py` | **unchanged** |

**Ownership invariants preserved.** Units are converted *before* decode
(`_converted_vendor_arrays`) and geometry is decided *outside* it, so decode still touches values only
— the Normalizer boundary in [architecture.md §Normalization vs. homogenization](../../architecture.md#normalization-vs-homogenization)
is unmoved. `open_meteo`'s explicit length checks stay: they attribute cause to the **vendor** and
correctly raise `RuntimeFailure`, which a type-level check could not do (#31).

## 4. Target code shapes

### 4.1 `manifold/data.py`

```python
@dataclass(frozen=True)
class ParameterData:
    values: Sequence[float]
    present: Sequence[bool] | None

    def __post_init__(self) -> None:
        if self.present is not None and len(self.present) != len(self.values):
            raise ValueError(
                f"present length {len(self.present)} != values length {len(self.values)}"
            )

    @classmethod
    def of(cls, values: Sequence[float], present: Sequence[bool]) -> ParameterData:
        """Construct, eliding an all-present mask. Elides only a *validated* mask (D1)."""
        validated = cls(values=values, present=present)   # __post_init__ checks length
        return cls(values=values, present=None) if all(present) else validated

    def is_present(self, i: int) -> bool:
        return self.present is None or self.present[i]

    def take(self, indices: Sequence[int]) -> ParameterData:
        """Gather the slice at `indices` — values and presence stay in step by construction."""
        values = [self.values[i] for i in indices]
        if self.present is None:
            return ParameterData(values=values, present=None)
        return ParameterData.of(values, [self.present[i] for i in indices])
```

**One rule, stated once: every construction path holding a mask goes through `of`.** So a crop that
happens to remove every absent cell *does* re-elide. The alternative (let `take` keep a redundant
all-`True` mask) is unobservable today and costs nothing measurable either way — but it leaves two
construction paths normalizing differently, which is the kind of divergence that is invisible until
something starts depending on it.

`and_present` stays exactly as it is, directly below.

### 4.2 `nodes/providers/timeline.py`

```python
Decode = Callable[[Mapping[str, Sequence[float | None]]], ParameterData]
"""Quantity transform over already unit-converted vendor series → one parameter's slice."""

def pointwise(*vars: str, fn: Callable[..., float]) -> Decode:
    """A tick is present iff every input var is; `fn` sees only present ticks.

    The value at an absent tick is unspecified filler (`nan`) — the mask is the sole
    presence authority. This is the only site that *writes* filler; downstream kernels
    then compute over it (`hypot(nan, nan)`), which the mask discards.
    """
    def decode(arrays: Mapping[str, Sequence[float | None]]) -> ParameterData:
        series = [arrays[v] for v in vars]
        values: list[float] = []
        present: list[bool] = []
        for cells in zip(*series, strict=True):
            if any(c is None for c in cells):
                values.append(float("nan"))
                present.append(False)
            else:
                values.append(fn(*cells))
                present.append(True)
        return ParameterData.of(values, present)
    return decode


def passthrough(var: str) -> Decode:
    """Decode that copies one already-converted vendor series into canonical values."""
    return pointwise(var, fn=lambda v: v)
```

`cell()` is deleted. `AxisSpec` / `PointSeriesTap` / `axis()` and the Z presets are untouched.

### 4.3 `nodes/providers/open_meteo.py`

```python
def _u_component(speed_ms: float, direction_deg: float) -> float:
    rad = math.radians(direction_deg)
    return -speed_ms * math.sin(rad)          # meteorological: degrees FROM

def _v_component(speed_ms: float, direction_deg: float) -> float:
    return -speed_ms * math.cos(math.radians(direction_deg))

_wind_u = pointwise("wind_speed_10m", "wind_direction_10m", fn=_u_component)
_wind_v = pointwise("wind_speed_10m", "wind_direction_10m", fn=_v_component)
```

The `math.isnan(...)` guard in `_wind_component` **deletes** — `fn` cannot be handed a null or a `nan`.
`math` stays imported for the trig. The `TAPS` table is unchanged in shape (`decode=_wind_u`, etc.).

In `normalize`, the loop body becomes:

```python
data = tap.decode({var.name: converted[var.name] for var in tap.vendor_vars})
if len(data.values) != n:
    raise RuntimeFailure(f"open-meteo decode length mismatch for {tap.produces}: …")
ranges[tap.produces] = data
```

### 4.4 `manifold/sampling.py` and `api/mcp_app.py`

```python
# sampling.resample
ranges[pid] = coverage.ranges[pid].take(source_indices)

# mcp_app.serialize_coverage
values = [
    None if not data.is_present(i) else float(value)
    for i, value in enumerate(data.values)
]
```

## 5. Flow walkthrough — one null hourly sample

1. Open-Meteo returns `hourly.temperature_2m = [18.5, null, 19.1]`.
2. `_converted_vendor_arrays` validates units and preserves the null (`_optional_float` → `None`;
   the km/h→m/s branch is `None`-safe already).
3. `passthrough("temperature_2m")` → `pointwise` marks tick 1 absent, writes filler, returns
   `ParameterData(values=[18.5, nan, 19.1], present=[True, False, True])` — `of` does not elide
   because not all present.
4. `normalize` length-checks and stores it in the native record; `_assemble` moves it through
   unchanged; the Arbiter moves the whole object.
5. `serialize_coverage` → `"values": [18.5, null, 19.1]`. Valid JSON.

**Wind, one null in either variable.** `pointwise` is built over *both* vendor vars for *both*
components, so a null in `wind_speed_10m` alone marks tick *i* absent in `wind_u` **and** `wind_v` —
by construction, not by two decoders agreeing.

**Through the wind Calculator.** `and_present` ANDs the two input masks (already `False` at *i*), and
the kernel computes `hypot(nan, nan)` / `atan2(-nan, -nan) % 360.0` at that tick — both `nan`, both
discarded by the mask. This is the "kernels compute garbage at masked cells by design" case; it is
correct and must not be "fixed".

**Fully-present response** (the ordinary v1 shape): `pointwise` builds an all-`True` mask, `of` elides
it to `None`, and everything downstream behaves exactly as today.

## 6. Implementation stages (TDD, red → green → refactor)

Vertical slices; write the failing test first **within each stage**, and finish each stage green.
**The live defect dies at S3**; S4–S5 are refactors that must keep S3's test green (D3).

*(No cross-stage tracer. An end-to-end test written at S1 would sit red through S2 and S3 — which is
the horizontal slicing the [tdd skill](../../../.claude/skills/tdd/SKILL.md) rules out, and it would
leave the suite red for three stages behind an `xfail` someone has to remember to flip. The
end-to-end assertion is still written test-first; it just belongs at the head of S3, the slice that
makes it pass.)*

- **S1 — `ParameterData` behaviour.** `__post_init__`, `of` (elides only a validated mask, D1),
  `is_present`.
  Tests: mismatched length rejected at direct construction; **`of([1.0, 2.0], [True])` rejected** (the
  D1 hole — this test is the reason D1 exists); all-`True` elides to `None`; mixed mask preserved;
  `is_present` agrees for both representations. No caller changes yet — everything stays green.
- **S2 — `pointwise` + `Decode`.** Add `pointwise`, re-express `passthrough`, delete `cell()`, retarget
  the `Decode` alias. Tests at the decoder level: a null yields a non-present tick; an all-present
  series elides; `fn` is never called with `None`; a two-var decoder marks absent when **either** is
  null. `open_meteo` still compiles because its decoders are next.
- **S3 — `open_meteo` wiring + the end-to-end assertion.** Write it first: an integration test through
  `OpenMeteoProvider` with a mocked transport whose `hourly` carries one `null`, asserting the
  serialized MCP payload parses under `json.loads(..., parse_constant=_reject)` and that the tick is
  `null` — the ticket's live defect, stated as a test. Then: `_wind_u` / `_wind_v` via `pointwise`;
  `_u_component` / `_v_component` replace `_wind_component` (guard deleted); `normalize` consumes the
  `ParameterData`. **The defect dies here.** Add: a null in `wind_speed_10m` marks both components absent at that tick;
  a fully-present response still yields `present is None` (the one sanctioned elision assertion —
  `test_open_meteo.py:131`, with a comment that it pins an optimization, not a contract).
- **S4 — `mcp_app` refactor.** Serializer reads `is_present`. Behaviour-neutral; S0 and the existing
  hand-built serializer test (`test_mcp_app.py:229`) both stay green. That test **stays** — it is a
  legitimate serializer unit test; what it may no longer do is stand in for provider coverage.
- **S5 — `sampling` refactor.** `resample` uses `take`. Rewrite `test_sampling.py:130-132`
  (`list(present) == [True, False, True]`) through `is_present`, and add the crop-away case: a crop
  that removes every absent tick yields an all-present result.

## 7. Migration / compatibility / rollout

- **No wire-schema change**, but a real behaviour change for one class of client. The response shape is
  unchanged; a `null` becomes *reachable* where `NaN` previously appeared. A client on a **strict**
  parser was getting a hard parse error and starts working. A client on a **lenient** parser — which
  includes Python's own `json.loads`, non-strict unless given `parse_constant` — was silently
  receiving `float('nan')` and now receives `None`. That is the correction we want, but it is a change
  in delivered values, not merely a fix to something already broken, and downstream arithmetic that
  happened to tolerate `NaN` may now hit `None`.
- **No persisted state.** Nothing in a `Store` yet (006), so no data migration.
- **No config or rollout gate.** The change is unconditional and self-contained in the provider path.
- **Test churn is minimal by design** — two tests touched (`test_sampling.py`, and a comment on
  `test_open_meteo.py:131`). The dozen `ParameterData(values=…, present=None)` constructions across
  the suite keep working because direct construction stays legal. That is the payoff of choosing `of`
  over normalizing inside `__post_init__`.

## 8. Failure handling & observability

- **Nodata is not a failure.** An absent cell is a *successful gap* and never raises, never omits the
  parameter, never reaches the error taxonomy → [architecture §Failure, nodata, and availability](../../architecture.md#failure-nodata-and-availability).
- **An all-absent parameter is legal here** and serializes as an array of `null`s. Whether it should
  instead be *omitted with a reason* is 009's question.
- **Vendor-attributable malformity stays `RuntimeFailure`** — unit mismatch, wrong array length,
  non-numeric cell, non-hourly time axis: all unchanged, all raised by `open_meteo` where the cause is
  known.
- **Caller-attributable malformity is non-taxonomy** — `ParameterData`'s length checks raise
  `ValueError`, matching the precedent at [sampling.py:67](../../../src/meteoscape/manifold/sampling.py)
  and architecture's "bug → non-taxonomy error".
- **No new observability surface.** Counting nodata cells per response is plausible telemetry and
  belongs with 009's reason channel, not here (concern #14 still unassigned).

## 9. Limitations & out-of-scope (by design)

- **No absence *reason*.** `present[i] = False` says *no value*, never *why* — 009 owns the
  distinction between nodata and a suppressed fault, and assumes this mask exists.
- **No alignment enforcement.** `CoverageRecord` is untouched; positional alignment stays asserted and
  unchecked → [#31](../../concerns.md#31-positional-alignment-is-asserted-never-checked), which names the
  two events that would open the hole and records that a length check is only a proxy (it cannot catch
  transposed axis order).
- **`values` stays `Sequence[float]`.** A nullable value array was rejected at align: it contradicts
  ADR-0002's dtype-agnostic rationale and forecloses the array-backed mask `data.py` reserves.
- **Filler is `nan`, and that is a deliberate re-use of a rejected token.** ADR-0002 rejects NaN as a
  *sentinel*; here it is unspecified filler with one writer and no reader. The chosen tradeoff: a mask
  bug produces invalid JSON (loud) rather than a plausible zero (silent-wrong).
- **`present` is not exposed at the MCP surface** as a parallel array; absence is carried by `null` in
  `values`. Nothing in v1 needs to distinguish "absent" from "absent for reason X" on the wire.

## 10. Follow-ups

**Doc alignment — none outstanding.** ADR-0002, ADR-0004, `v1-requirements`, `architecture.md`
(concerns index + the "padded with nodata" qualifier), `concerns.md` #31, `tickets/README`, and the
session 0013 supersession note all landed with the align pass in `c5dd2b9`. This RFC introduces **no**
new contract that the accepted docs do not already state.

**One correction this RFC makes to a prior RFC:** [RFC 0001 §10](./0001-20260716-derived-wind-calculator.md)
says nodata masks are "ticket 009, not 002b" and predicts the wind kernel will "inherit them through
the AND with **zero rework**". The ownership moved to 002c, but the prediction holds exactly —
`wind.py` and `and_present` are untouched by this RFC, and the kernel inherits real masks through the
existing AND. Worth recording because it is a rare case of a forward-compatibility claim being tested
and surviving.

**Product/tech:**

- **009** unblocks on this: per-parameter absence reasons, partial-failure omission, and the
  nodata-vs-failure distinction at the edge.
- **#31** stays open, owned by whichever of a non-pointwise Calculator kernel or 006's Store read-back
  arrives first.
- **Nodata telemetry** (how often does a vendor actually null a cell?) is unmeasured and unassigned;
  it would tell us whether the all-absent-parameter case in §8 ever needs 009's treatment.
