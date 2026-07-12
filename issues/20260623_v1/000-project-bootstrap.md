## Parent PRD

`docs/v1-requirements.md`

> **Status: done (2026-07-11).** All modules landed. The catalog package was reshaped by
> [ADR-0005](../../docs/adr/0005-build-time-composition.md) after this issue was written: vocabulary →
> `parameters.py` (Tier-0 leaf), table → `nodes/catalog/paramtable.py` (catalogue role); paths below
> updated to match. Two modules landed slightly ahead of the no-behaviour rule — `cadence.py` (anchor
> math) and `capability.py` (`serves`) carry logic with no tests yet; their behavioural tests are owed
> in 001 Phase A.

## What to build

The **walking-skeleton** init slice: the inert scaffolding every later slice stands on, with **no
forecast behavior**. This slice is deliberately allowed to be horizontal because it carries no behavior
— it transcribes shapes already fixed by accepted ADRs, so there is nothing to test the shape of and no
"imagined behavior" to outrun. All behaviour-bearing logic stays vertical / test-driven from 001 onward.

In scope:

- **Project skeleton + packaging** — the module layout from [`docs/module-layout.md`](../../docs/module-layout.md),
  a dependency/packaging file pinning the v1 stack (Python · async · Pydantic v2 · httpx · the
  MCP SDK · the test runner), and baseline tooling (format / lint / type-check).
- **ADR-fixed value types, v1 degenerate cases only** — the data-model and provenance types from
  [ADR-0002](../../docs/adr/0002-data-model.md) / [ADR-0003](../../docs/adr/0003-provenance-and-origin.md)
  as inert types: the regular point/hourly `Domain` (+ `Axis`), `Selection`, `Timeline` `Coverage`,
  `ParameterData`, `Uniform` `ProvenanceField`, atomic `Origin` / `Provenance`.
- **Parameter vocabulary + table** — the vocabulary (`ParameterId`, `Unit`, `Quantity` identity,
  `ParameterDef`; the **closed enums** `ExtentScaling` / `CellStatistic` / `MeasurementScale`) in
  `parameters.py`, and the **`ParameterTable`** interface + a **`StaticParameterTable`** v1
  representation hosting the v1 `ParameterDef`s in `nodes/catalog/paramtable.py`. Consumers
  (`Normalizer`, `Capability`, the edge) reach parameter facts by **injection**, never via hardcoded
  enums; `Quantity` / `ParameterDef` are table-sourced, not enums. File / UI-backed representations are
  deferred.
- **Protocol signatures only** — `Manifold.project`, `Countable`, `Writable.assimilate` as typed
  signatures (no implementation).
- **Reserved slots as declared seams** — `PerPoint`, the per-parameter `bounds` override, windowed
  `CellStatistic`, rectilinear / curvilinear `Domain` representations, `Domain.intersect` — declared
  but **not** implemented (no speculative code).
- **Error taxonomy types** — `capability-mismatch` / `runtime-failure` / `bad-request`.

## Acceptance criteria

- [x] **Packaging** — the project installs into a fresh environment; module layout matches
      [`docs/module-layout.md`](../../docs/module-layout.md), modules behaviour-free.
- [x] **`errors.py`** — `capability-mismatch` / `runtime-failure` / `bad-request` taxonomy types.
- [x] **`manifold/core.py`** — `Manifold` / `Countable` / `Writable` protocols + the `Coverage`
      contract + `Selection` (signatures / value type only).
- [x] **`nodes/reservoir.py`** — `Store` / `Reservoir` declared as signatures, behaviour deferred to
      their slices.
- [x] **`manifold/domain.py`** — `Domain` / `EnumerableDomain` interface + `RegularDomain` (point/hourly)
      + `Axis` / `RegularAxis` (via the `Separable` facet); rectilinear / curvilinear representations and
      `intersect` declared as seams.
- [x] **`manifold/data.py`** — `ParameterData` (pure `values` / `present`).
- [x] **`manifold/provenance.py`** — `ProvenanceField` + `Uniform` / `PerParameter`, atomic `Origin` /
      `Provenance`; `PerPoint` and `SyntheticOrigin` declared as seams.
- [x] **`manifold/coverage.py`** — `Timeline` (the v1 `Coverage` realization); `Grid` declared as a seam.
- [x] **`parameters.py`** — `ParameterId`, `Unit`, `Quantity`, `ParameterDef`; closed enums
      `ExtentScaling` / `CellStatistic` / `MeasurementScale`.
- [x] **`nodes/catalog/paramtable.py`** — `ParameterTable` + `StaticParameterTable` (v1 set); parameter
      facts reached by injection, not hardcoded enums.
- [x] **Smoke test** — the MCP server starts and registers the `forecast_hourly` tool (no forecast
      behaviour).
- [x] **No behaviour** — no behaviour-bearing logic and no behavioural tests in this slice (begins 001).
      *(Exceptions noted in Status: `cadence.py` / `capability.py` logic landed early, tests owed in
      001 Phase A.)*

## Blocked by

None - can start immediately.

## User stories addressed

Foundational — no user story directly; unblocks all subsequent slices (001+).
