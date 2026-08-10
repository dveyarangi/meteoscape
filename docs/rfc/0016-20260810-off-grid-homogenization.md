# RFC 0016 · 2026-08-10 · Off-grid homogenization — implementation plan

Implementation plan for [off-grid homogenization](../tickets/done/01-0117-off-grid-homogenization.md)
(legacy 007).

**Scope in one line:** the behaviour this ticket was written to build is **already in the tree**; what
is missing is the **evidence**. This RFC adds the tests that guard it, corrects three code comments
that describe a plan rather than the code, and states the promise on the Coverage contract and the MCP
edge record. **No `src` logic changes.**

## Why this is a guard ticket, not a build ticket

The ticket asks for read-time homogenization that answers an off-grid point at the requested point,
sourced from the enclosing store cell, with the value-transfer half living in `sampling.py` and the
"which cell may answer" claim in the `Reservoir`. Every clause of that is how the code already runs:

```
caller asks (52.52, 13.419998)         RegularAxis count-1, pinned  (mcp_app.py:164-167)
      │
root Reservoir.project
      ├─ store.quantize(request)       X/Y → grid.clip() → cellular ⇒ floor
      │                                ⇒ ENCLOSING cell, emitted as its tick   (store.py:200-204)
      ├─ source.project(tick)          vendor fetched AT the tick; OM drops the
      │                                echoed lat/lon — "the point is the one asked
      │                                for"                     (open_meteo.py:164)
      ├─ store.assimilate              keyed by containing-cell index          (store.py:157-166)
      └─ _read_back
           ├─ ground(request, holding) pinned X/Y pass through by IDENTITY     (domain.py:645-647)
           ├─ _relabel_onto            ← THE CLAIM: address rewritten to the
           │                             requested point; values and provenance
           │                             untouched                          (reservoir.py:181-211)
           └─ CoverageSet.project
                └─ resample()          ← THE TRANSFER: aligned crop, parameter
                                         restrict                  (coverage.py:115 → sampling.py:89)
```

So: the answer is already reported at the requested point; the enclosing cell is already the one that
answers; and the claim/transfer split the ticket describes is already the module boundary. What does
**not** exist is a single test that pins any of it, and an invariant on any record that states it.

## Decisions taken at the 2026-08-10 align

| # | Question | Decision | Where it landed |
|---|---|---|---|
| 1 | *nearest* or *enclosing* cell? | **Enclosing.** "Nearest enclosing" named no cell — there is exactly one enclosing cell, and *nearest* is a question only when several candidates exist. Under v1's shape none ever do: provider records are point-shaped (`_relabel_onto` asserts count-1 on X/Y) and the store is a **sparse cache** holding only cells already asked for. Already decided by ADR-0006 (`quantize` ⇒ containing cell's tick) and the glossary (*Quantize*, _Avoid_: round). | [v1-requirements §4](../v1-requirements.md) corrected; [ticket](../tickets/done/01-0117-off-grid-homogenization.md) records it |
| 2 | What is the read-back called? | **The identity Resampler.** `kernel` was already reserved against in the glossary (*Resampler*, _Avoid_: kernel) — because *kernel* is taken by the Calculator sense. The glossary entry now admits a degenerate member: identity is kind-agnostic precisely because it is one rule for every Parameter. | [glossary](../glossary.md); resampling-sense sweep across ADR-0001/2/3/4/6, architecture, concerns, parameters, product-roadmap |
| 3 | How far does the rename sweep? | **Across the source-of-truth docs, ADRs included** — the [doc map](../README.md) puts ADRs in the source-of-truth row. Calculator-kernel and "shared kernel" senses untouched. | 12 sites swept; `rfc/done` left as written (history) |
| 4 | What does 0117 build? | **Guard and name it.** No production logic. Tests + comments + records. Building a Resampler registry now would guess a shape ADR-0004 defers to #5 against its single implementation. | [ticket → Not in scope](../tickets/done/01-0117-off-grid-homogenization.md) |
| 5 | Where does the promise live? | **Coverage contract**, guarded at the Reservoir. `serialize_coverage` emits only the T axis, so the MCP wire cannot show the answered coordinate; that surface promises the observable consequence instead (coarse step ⇒ two points in one cell return identical values). Echoing the coordinate is an additive per-surface gap on the MCP edge roadmap; *which* cell sourced a value is #14's and explicitly **not** provenance (ADR-0003). | [edge/mcp.md](../edge/mcp.md); [#14](../concerns.md#14-resolution-trace-and-observability) |

## Boundaries involved

| Boundary | Owner | What this does to it |
|---|---|---|
| `quantize` ⇒ enclosing cell's tick | [ADR-0006](../adr/0006-materialization-granularity-and-store-shape.md) | **Untouched and now guarded.** Decision 1 confirmed it rather than amending it. |
| Claim (`_relabel_onto`) vs transfer (`resample`) | [ADR-0006](../adr/0006-materialization-granularity-and-store-shape.md), [architecture §Reservoir](../architecture.md#reservoir) | **Untouched.** Already the module boundary; the RFC documents it in place of a `TODO` that promised to create it. |
| *Resampler* (the term) | [glossary](../glossary.md) | Entry widened to admit the **identity** member. No new type, no code noun. |
| Resampler registry / `ParameterDef` selector | [ADR-0004](../adr/0004-producer-resolution-and-capability.md), [#5](../concerns.md#5-read-time-homogenization-fidelity) | **Untouched — deferred.** Not built here. |
| [#21](../concerns.md#21-serves-extent-vs-project-crop-ability) `serves` vs crop-ability | concerns | **Repointed, not closed.** Used to read "registry at 007"; its trigger is now the first genuinely off-phase or different-step request. |
| Store step (`StoreSpec.spatial_step`) | [config.py](../../src/meteoscape/config.py) | **Untouched.** Whether the lattice coarsens is the [ledger](../tickets/02-0124-vendor-call-ledger.md)'s question. |
| MCP response payload | [edge/mcp.md](../edge/mcp.md) | **Unchanged.** One invariant added (fidelity floor), one roadmap item added (coordinate echo). |

## Facts that shape the implementation (verified 2026-08-10)

1. **`_timeline_store` in the reservoir tests already runs a 0.5° lattice** anchored at `-180.0`
   ([test_reservoir.py:100-110](../../tests/deterministic/nodes/test_reservoir.py)) — coarse enough
   that enclosing-cell behaviour is observable. Ticks land on `-180 + k·0.5`, so `10.0` is on-tick and
   cell `[10.0, 10.5)` contains `10.3` and `10.4` but not `10.6`.
2. **`_Counting` returns a fixed answer regardless of the ask**
   ([test_reservoir.py:127-160](../../tests/deterministic/nodes/test_reservoir.py)). That is fine for
   same-cell tests, and insufficient for a different-cell test: the second refill would assimilate at
   the first record's index and the reload would find nothing, raising `RuntimeFailure("refill
   produced no holdings")`. A child that answers on the asked geometry is required for that case
   (stage 1c).
3. **`_live_ask` hard-codes `lon=10.0, lat=20.0`**
   ([test_reservoir.py:180-195](../../tests/deterministic/nodes/test_reservoir.py)) — it takes only
   `hours` and `z`. Every new test needs a different point, so stage 1 **widens its signature** with
   `lon: float = 10.0, lat: float = 20.0`; the defaults keep all six existing callers byte-identical.
   This is the only change to an existing test helper.
4. **`as_separable` is not imported in `test_reservoir.py`.** `SelectionDomain` and `RegularAxis` are,
   and `store.quantize` returns a `SelectionDomain`, so the stage-1c fake reads its ask through
   `SelectionDomain.axis(...)` — no new import, and `isinstance` narrowing keeps `pyright` clean
   ([0050](../tickets/done/01-0050-type-contract-hygiene.md) requires it across `tests` too).
5. **`_fmt_coord` is `format(value, ".15g")`**
   ([open_meteo.py:211](../../src/meteoscape/nodes/providers/open_meteo.py)). A store tick carries
   float noise — `-180.0 + 1930000*0.0001 == 13.000000000000028` — which `.15g` absorbs to `"13"`.
   The stage-2 assertion still uses `pytest.approx` rather than `==`, so it states "the tick, not the
   caller's point" without depending on that absorption.
6. **`test_project_refills_then_serves_from_store`**
   ([test_reservoir.py:304-314](../../tests/deterministic/nodes/test_reservoir.py)) is the precedent
   for the two-project pattern: `Reservoir(_timeline_store(), child, STOPPED)`, `STOPPED` at
   `2026-07-11T12:00`, `_record`'s default expiration `_FETCHED + 1h`, so a repeat inside the same
   test is fresh by construction. Stage 1b reuses it exactly and varies only the point.
7. **`Settings` is a `BaseSettings`** with `store_spatial_step: float = 0.0001`
   ([config.py:76-89](../../src/meteoscape/config.py)), so `Settings(store_spatial_step=0.5)`
   composes a coarse root store for the e2e stage. `StoreFactory.create` accepts it
   (`0 < step <= 90`, [store.py:289](../../src/meteoscape/nodes/store.py)).
8. **The Open-Meteo source store is `spatial_step=0.0001` from the catalogue**
   ([open_meteo.py:258](../../src/meteoscape/nodes/providers/open_meteo.py)), so with a coarse root
   the vendor is asked at the **root** cell's tick: the source's own quantize of an already-tick
   coordinate is identity.
9. **`respx` route calls expose the vendor query**, the idiom
   `test_out_of_range_bounds_fetch_exactly_the_clipped_window` already uses
   ([test_e2e_forecast.py](../../tests/deterministic/test_e2e_forecast.py)).
10. **`valid_time` hourly-alignment is already guarded** — the MCP edge record cites `test_mcp_app.py`
    serializer tests for it. Ticket criterion 3 is met by citation; this RFC adds nothing for it.
11. **The configurable-step criteria are already guarded** — step validation at
   [store.py:289](../../src/meteoscape/nodes/store.py), the default at
   [test_config.py:69](../../tests/deterministic/test_config.py), the per-offering override at
   [test_composition.py:127](../../tests/deterministic/nodes/test_composition.py).

## Stages

Every stage leaves the suite green. Because the behaviour already exists, stages 1–2 are
**characterization** tests, not red-green: they pass on first run. A test that passes on first run has
not been shown to be load-bearing, so each stage carries a **mutation check** — a temporary local edit
that must turn the new test red, then be reverted. The mutation is never committed.

### Stage 1 — Reservoir-level guards (`tests/deterministic/nodes/test_reservoir.py`)

**1·0 (prerequisite).** Widen `_live_ask` per fact 3:

```python
def _live_ask(
    *,
    lon: float = 10.0,
    lat: float = 20.0,
    hours: int = 3,
    z: Interval[float] | None = None,
) -> Selection:
```

passing `lon` / `lat` through to `_ask`. Defaults preserve every existing caller; no existing test
changes. Add the new tests to the `--- Pipeline / source-group ---` section, beside
`test_project_refills_then_serves_from_store` (they all drive `project`, not read-back in isolation).

**1a. `test_off_grid_request_is_answered_at_the_requested_point`**

- Child: `_Counting((_record(AIR_TEMPERATURE, _native(lon=10.0, lat=20.0), value=7.5),),
  frozenset({AIR_TEMPERATURE}))` — the record sits on the cell tick, as a real fetch at the quantized
  point would.
- Ask: `_live_ask(lon=10.3, lat=20.2)` (inside cell `[10.0, 10.5) × [20.0, 20.5)`).
- Assert: the answer's `domain.axis(AxisName.X)[0].coordinate == 10.3` and
  `domain.axis(AxisName.Y)[0].coordinate == 20.2` — **the requested point, not the tick**.
- Assert: values equal `[7.5, …]` — the enclosing cell's, unmodified.
- *Mutation check:* make `_relabel_onto` return `record` unchanged; 1a must fail.

**1b. `test_two_points_in_one_store_cell_share_one_fetch`**

- Same child and record; `Reservoir(_timeline_store(), child, STOPPED)` as in fact 6.
- Project twice, at `_live_ask(lon=10.3)` then `_live_ask(lon=10.4)` — both inside `[10.0, 10.5)`.
- Assert: `child.calls == 1` — the second is served from the store.
- Assert: each answer carries **its own** requested X (`10.3`, then `10.4`), with identical values.
- This is the test that states the fidelity floor: one cell, one value, two labels.
- *Mutation check:* narrow the store lattice to `0.0001`; 1b must fail with `calls == 2`.

**1c. `test_points_in_different_store_cells_fetch_separately`**

- Requires a child answering on the geometry it was asked (fact 2). Add beside `_Widening`:

```python
class _Echoing(_Counting):
    """Child that answers on the asked X/Y — what a real Provider does (open_meteo.py:164).

    Its inherited `_answer` is never returned; the placeholder record it is built with only keeps
    `_Counting.__init__` honest.
    """

    async def project(self, selection: Selection) -> Manifold:
        self.calls += 1
        self.asked.append(selection.parameters)
        # `quantize` hands the store's fetch-order, always a SelectionDomain (store.py:185-208).
        assert isinstance(selection.domain, SelectionDomain)
        lon = selection.domain.axis(AxisName.X).extent.lower
        lat = selection.domain.axis(AxisName.Y).extent.lower
        assert isinstance(lon, float) and isinstance(lat, float)
        return CoverageSet((_record(AIR_TEMPERATURE, _native(lon=lon, lat=lat), value=7.5),))
```

Construct it as `_Echoing((_record(AIR_TEMPERATURE, _native(lon=10.0, lat=20.0)),),
frozenset({AIR_TEMPERATURE}))`. No new imports: `SelectionDomain`, `AxisName`, `CoverageSet` and
`Manifold` are already imported.

- Project at `_live_ask(lon=10.3)`, then `_live_ask(lon=10.6)` (cell `[10.5, 11.0)`).
- Assert: `child.calls == 2`, and each answer carries its own requested X.
- *Mutation check:* widen the store lattice to `5.0`; 1c must fail with `calls == 1`.

**1d. `test_on_grid_request_is_the_identity_crop`**

- Same child and record at `lon=10.0, lat=20.0`.
- Ask at exactly `_live_ask()` — the defaults are the on-tick point.
- Assert: the answer's X/Y coordinates equal `10.0 / 20.0`, and values are unchanged — the
  degenerate case where the **coordinate** and the **values** are identity and `resample` is a
  lossless crop.
- **Relabel is *not* a no-op here** (corrected 2026-08-10 from the mutation run, which failed 1d as
  well as 1a). It harmonizes the whole axis object: the held record carries the provider's native
  `step` (1.0) where the ask carries the edge's (0.0001), so skipping it raises
  `NotImplementedError: non-identical step or off-phase selection` from `resample` — on-grid as much
  as off. The docstring must say so; "on-grid degenerates to a lossless crop" is a statement about
  the Resampler and the coordinate, never a licence to skip the rewrite.
- *Mutation check:* covered by 1a's — disabling relabel fails 1d too, which is the fact above.

### Stage 2 — edge-observable guard (`tests/deterministic/test_e2e_forecast.py`)

**2a. `test_points_within_one_store_cell_share_one_vendor_call`**

- Compose with `Settings(store_spatial_step=0.5)` — a local variant of `_compose_default`, taking the
  step as an argument. Do **not** change the default.
- One `respx` route returning `_canned_forecast()`.
- **Compose once, call twice inside one `async with Client(app)` block.** The shared root store is
  what makes the second call free; composing twice would build a second empty store and the test
  would fail for a reason that has nothing to do with the claim under test.
- Two tool calls: `(52.52, 13.41)` then `(52.52, 13.44)` — both inside the root cell
  `[13.0, 13.5) × [52.5, 53.0)` — each with `"parameters": ["air_temperature"]`, the
  one-winner-one-fetch idiom the existing e2e tests use, so the captured query is the whole vendor
  conversation and the compared values are a single series.
- Assert: `route.call_count == 1`.
- Assert: `float(asked["longitude"]) == pytest.approx(13.0, abs=1e-9)` and
  `float(asked["latitude"]) == pytest.approx(52.5, abs=1e-9)` — the vendor was asked at the **root
  store's cell tick**, not the caller's point. `approx` because a tick carries float noise (fact 5);
  the tolerance is nine orders of magnitude tighter than the 0.41° it must distinguish.
- Assert: the two responses' `air_temperature.values` are **identical** — the caller-observable
  consequence, and the exact promise the MCP edge record will carry.

### Stage 3 — comment corrections (`src`, comments only)

No logic changes. Three comments describe a plan the code has outgrown or use the reserved word:

1. **[reservoir.py:187-190](../../src/meteoscape/nodes/reservoir.py)** — delete the
   `TODO (temporary)` block. Replace with a statement of the split as it stands: this method is the
   **claim** (which cell may answer, honest only because admission gated it); the **transfer** is
   `resample`, reached through `CoverageSet.project`; v1's Resampler is **identity**, so no value
   moves here or there. Reference [#5](../concerns.md#5-read-time-homogenization-fidelity) for the
   Parameter-specific Resamplers that would change that.
2. **[sampling.py:3-4](../../src/meteoscape/manifold/sampling.py)** — *"A planned kernel registry adds
   nearest-neighbor without introducing a separate `sample` verb"* → the planned **Resampler**
   registry, and drop "nearest-neighbor" (decision 1: the cell is the enclosing one; the Resampler is
   what the registry varies).
3. **[config.py:87-89](../../src/meteoscape/config.py)** — *"near-exact values under the
   nearest-neighbor read-back"* → *under the identity Resampler*.

Removing the `TODO (temporary)` is the point of this stage: it currently instructs the next reader to
build something this RFC establishes must not be built.

### Stage 4 — records

1. **[edge/mcp.md](../edge/mcp.md) → Invariants**, new entry:
   *An off-grid point is served from the enclosing store cell, so the store step is the fidelity
   floor: two distinct requested points inside one cell receive identical values. The response does
   not report which point answered* — *validated by:* `test_points_within_one_store_cell_share_one_vendor_call`.
2. **[architecture.md §Reservoir](../architecture.md#reservoir)** — one sentence naming the
   Coverage-contract invariant: an off-grid request returns a Coverage whose X/Y are the **requested**
   coordinates, carrying the enclosing cell's values.
3. **[ticket](../tickets/done/01-0117-off-grid-homogenization.md)** — tick the remaining criteria (four are
   already met by citation per facts 10–11; the rest close with stages 1–2 and this stage), move to
   `tickets/done/`, update the [delivery status](../tickets/README.md) row and capability table
   (`Partial → Done`).
4. **[0125](../tickets/01-0125-supported-python-embedding.md)** — one line: the Coverage-contract
   point-exactness invariant is already true and guarded, so that surface inherits it as an
   observable promise; its align does not need to re-decide it.

## Limitations and follow-ups

- **The tests characterize, they do not drive.** Stage 1–2 tests pass on first run; the mutation
  checks are what make them meaningful. Skipping a mutation check leaves a test that would not notice
  the behaviour disappearing.
- **The MCP surface still cannot show the answered coordinate.** Filed as an additive, compatible
  roadmap item on the [MCP edge record](../edge/mcp.md#roadmap); not this ticket's.
- **Which cell sourced a value is unexposed**, deliberately →
  [#14](../concerns.md#14-resolution-trace-and-observability), and not a provenance field
  ([ADR-0003](../adr/0003-provenance-and-origin.md)).
- **[#21](../concerns.md#21-serves-extent-vs-project-crop-ability) survives untouched** — `serves`
  still admits off-phase / different-step selections that `resample` refuses.
- **[#37](../concerns.md#37-storeless-materialized-producers-and-read-back-homogenization) untouched**
  — where a storeless producer's homogenization lives has no v1 driver.
- **A gridded provider reopens cell selection.** When a record carries many X/Y cells,
  `_relabel_onto`'s count-1 assert fires and *which* cell answers becomes a real question for the
  first time — the trigger for both the selection question and the first Parameter-specific Resampler
  ([#5](../concerns.md#5-read-time-homogenization-fidelity)).
