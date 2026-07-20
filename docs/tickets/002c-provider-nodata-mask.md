# 002c — Provider nodata mask

- **Status:** Done
- **Depends on:** [002 — Core canonical parameters](./done/002-core-5-parameters.md)
- **Outcome:** A vendor null becomes `present[i] = False` and serializes as JSON `null`, replacing the
  undeclared NaN substitution that violates the Coverage contract — with presence read through
  `ParameterData` behaviour rather than off its representation.

## Parent PRD

`docs/v1-requirements.md`

## What to build

**The gap.** [ADR-0002](../adr/0002-data-model.md) fixes nodata as an explicit boolean mask and
**rejects a NaN sentinel by name** ("dtype-agnostic… keeps 'no data' distinct from a legitimate
not-a-number value"). Session 0011 specified the Provider side to match. The 002 build shipped
`Decode = Callable[..., list[float]]` instead, with
[`cell()`](../../src/meteoscape/nodes/providers/timeline.py) mapping vendor null → `nan` and
[`open_meteo.project`](../../src/meteoscape/nodes/providers/open_meteo.py) hardcoding `present=None`.
The deviation is currently *blessed* by a docstring ("None cells stay None → nan"), so it does not
read as a defect.

**Why it matters now.** The serializer only emits `null` when `present is not None`, which provider
data never is — so that branch is **dead for every real response**, and a vendor null reaches the wire
as `NaN`, which is **not valid JSON** (RFC 8259). The existing nodata test hand-builds
`present=[True, False]` on a fabricated Coverage, so it exercises a path no live response can reach:
green tests over a dead branch. This is the ticket's one live defect; everything below serves it.
(That hand-built test **stays** — it is a legitimate unit test of the serializer. What it may no longer
do is stand in for provider coverage, which is why the criteria below demand the same assertion made
end-to-end.)

### Provider side — one rule, one home

- **`Decode` returns `ParameterData`.** The pair `(values, present)` *is* `ParameterData`; an
  anonymous tuple would be that type with its identity filed off. No layering cost —
  `timeline.py` already imports from `manifold.domain`.
- **A `pointwise(*vars, fn)` combinator** in `timeline.py` owns the nodata rule: *a tick is present iff
  every input vendor var is present at it*, and `fn` is called **only on present ticks**. `passthrough`
  and the wind component decoders are both expressed through it. This makes "a null in either wind
  variable marks both components absent" true **by construction** rather than by two decoders agreeing.
- **Kernels become pure physics.** `_wind_component`'s `math.isnan(...)` guard deletes — it can no
  longer be handed a null or a `nan`.
- **`open_meteo.project`** builds its `ParameterData` from the decode result. Its existing explicit
  length checks **stay**: they guard a *vendor* payload and correctly raise `RuntimeFailure`.
- **`cell()` is deleted** — `pointwise` subsumes it, and it is the function that encoded the defect.
  `passthrough(var)` survives as a thin `pointwise` wrapper; the tap table reads better for it.
- Retire the docstring that documents the NaN behaviour as intended.

An **all-absent** parameter (every tick null) is a legal outcome here and serializes as an array of
`null`s. Whether it should instead be *omitted with a reason* is [009](./009-error-taxonomy-partial-success.md)'s
question, not this ticket's.

### The masked-cell value is unspecified

`values` stays `Sequence[float]`, so an absent cell still holds a number. **v1 fills `nan`, as filler
carrying no meaning** — the mask is the sole presence authority, and a reader that consulted
`values[i]` instead of `present[i]` would be reading the very sentinel ADR-0002 rejects. Consequence
to state plainly: kernels compute garbage at masked cells by design (`wind_from_uv` will evaluate
`atan2` over filler), and that is correct — the mask discards it. Do not "fix" a kernel to skip masked
cells. → [ADR-0002](../adr/0002-data-model.md) (Nodata).

### Presence becomes behaviour, not a field read

`present`'s `None`-means-all-present is a **representation** — an elision that keeps the common case
free. The harm when it leaks is a consumer having to **understand** the convention, so the test is
*does this site branch on `None`*, not *does it touch the field*. Two sites do:

| Site | Today | After |
|---|---|---|
| [`mcp_app.py`](../../src/meteoscape/api/mcp_app.py) | `data.present is not None and not data.present[i]` | `data.is_present(i)` |
| [`sampling.py`](../../src/meteoscape/manifold/sampling.py) | `None if data.present is None else [...]`, beside a parallel `values` comprehension | `data.take(source_indices)` |

**`and_present` and [`wind.py`](../../src/meteoscape/nodes/calculators/wind.py) are deliberately left
alone.** `wind.py` passes both masks to a function that handles `None` internally — it never branches,
so it never learns the convention, and moving the function onto the class would be aesthetics. It would
also *cost* something real: `and_present`'s `n=len(cov.domain)` means its `zip(strict=True)`
incidentally cross-checks each mask against the **domain** length, which a method reading
`len(self.values)` would lose — the very check deferred by
[#31](../concerns.md#31-positional-alignment-is-asserted-never-checked). `and_present` already sits in
`data.py` beside `ParameterData`; it is at home.

`ParameterData` gains:

- **`of(values, present)`** — the construction path used by `pointwise` and `take`, eliding an
  all-`True` mask to `None` (a memory optimization for the common case: a ~400-element all-`True` list
  per parameter per request). Direct construction stays legal and non-eliding; nothing reads the
  representation, so an un-elided mask is merely larger, never wrong.
- **`__post_init__`** — validates `len(present) == len(values)` when `present` is not `None`. The
  pair's *internal* consistency, which is all this type can see.

After this, no consumer branches on the representation, so switching to an array-backed mask stays
open — as `data.py`'s docstring reserves.

### Test migration (not optional — one of these is a hard break)

Two tests assert on the representation:

| Test | Issue |
|---|---|
| [`test_sampling.py:130-132`](../../tests/manifold/test_sampling.py) | Asserts `list(present) == [True, False, True]` — a raw representation read, and the closest existing cousin of the new `take` criterion. Rewrite through `is_present`; it becomes that criterion's test rather than a second one beside it. |
| [`test_open_meteo.py:131`](../../tests/nodes/providers/test_open_meteo.py) | Asserts `.present is None` — this is the *one* place the elision may still be asserted directly (criterion 3's "verified once"), so it stays, but should say in a comment that it pins an optimization, not a contract. |
| [`test_mcp_app.py:229`](../../tests/api/test_mcp_app.py) | The hand-built `present=[True, False]` serializer test. Stays as-is (see above). |

Every other `ParameterData(values=…, present=None)` in the suite keeps working — direct construction
stays legal, which is why `of` was chosen over normalizing in `__post_init__`. That the migration is
this small is a consequence of that decision, not a coincidence.

### Not in this ticket

- **Per-parameter absence reasons and partial-failure semantics** — [009](./009-error-taxonomy-partial-success.md),
  which distinguishes nodata from failure at the edge and **assumes this mask exists**. 009's claim
  that "nodata → `null` serialization" already landed is only true once this ships.
- **Positional-alignment validation on `CoverageRecord`.** Folded in at session 0013, **reversed at
  session 0014**: no construction site can misalign today — `sampling` maps over an index list sized to
  the target domain, `arbiter` moves whole `ParameterData` objects between domain-compared Coverages,
  `open_meteo` checks explicitly at both sites, and `Calculator`'s only kernel returns its input domain
  unchanged with element-count-preserving ranges. With `ParameterData` now owning `present`'s length, this ticket gives
  `CoverageRecord` no new reason to be touched. Filed as
  [#31](../concerns.md#31-positional-alignment-is-asserted-never-checked) with the two events that
  would open the hole (a windowing kernel; Store read-back in [006](./006-retentive-store-freshness.md)).
- **Wire-level NaN verification.** The serializer trusts the mask. Presence and values travel as one
  frozen object through every transform, so the mask cannot desync — a second enforcement point would
  guard an invariant already held by construction.

v1 expects Open-Meteo's hourly series to be complete, so all-present stays the ordinary shape; this
ticket makes the *exception* honest rather than substituted. See `docs/v1-requirements.md`
(parameter encoding).

## Acceptance criteria

- [ ] `Decode` returns `ParameterData`; no code path treats `nan` as the absence **signal** (it remains
      only as unspecified filler, written at the single site named above), and no decoder implements the
      presence rule itself — `pointwise` owns it.
- [ ] A mocked Open-Meteo response containing a `null` hourly sample yields a non-present cell for that
      tick, and the MCP response serializes it as JSON `null` — asserted **through the provider**, not
      on a hand-built Coverage.
- [ ] A fully-present response reports **every cell present** (asserted through `is_present`, not on
      the representation). Elision to `present is None` is verified **once**, as the optimization it is.
- [ ] A null in **either** wind vendor variable marks both `wind_u` and `wind_v` absent at that tick.
- [ ] A response containing an absent cell round-trips through a **strict** JSON parser
      (`json.loads(..., parse_constant=…)` raises on any `NaN` / `Infinity` token).
- [ ] `take` preserves presence through a crop: a `resample` that keeps an absent tick keeps it absent,
      and one that crops it away yields an all-present result.
- [ ] No site in `src/` **branches on the `None` convention** outside `ParameterData` itself
      (`wind.py`'s pass-through to `and_present` is not such a site and stays unchanged).
- [ ] `ParameterData` rejects a `present` whose length differs from `values` at construction.

## User stories addressed

- User story 8 (producible subset — the nodata half; the reason half is 009)
- Supports acceptance §1 (normalized Timeline) by making absent samples representable
