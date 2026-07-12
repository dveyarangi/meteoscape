## Parent PRD

`docs/v1-requirements.md`

## What to build

The thinnest end-to-end path through the whole spine — a walking skeleton that proves the
Manifold composition resolves a real request. A `forecast_hourly(lat, lon)` MCP tool call becomes a
canonical `Selection` (lat/lon point + hourly `valid_time` window), passes the null `Gateway`, and
resolves down the wired DAG: best-view `Reservoir` → `Arbiter` (single candidate, `priority`
reconciler) → **Source** (the `Reservoir(store, Provider)` role) → Open-Meteo `Provider` + its
`Normalizer` → an HTTPS fetch. The response is
one normalized hourly `Timeline` carrying a **single** `ParameterData` (air temperature) in its
canonical unit, with per-parameter provenance including `expiration`, serialized as compact
agent-friendly JSON.

Stand up only the minimal version of every module needed to make this path real: the Coverage model
(`Timeline` / `ParameterData` / `ProvenanceField`), `Domain` / `Selection`, the `Reservoir` (the Source
role `Reservoir(store, Provider)`, wired over a **stub `Store`** — no retention yet),
`Arbiter`, the Open-Meteo `Provider`, a minimal `SourceBinder.build` → `SourceRegistry` +
`Weaver.weave(ProfileDef)` / thin `server.py`, and the MCP adapter. On-grid /
identity homogenization only; no fallback, no caching, one parameter.

See `docs/architecture.md` (Major components, Data / request flow, Config/binders/Weaver),
`docs/v1-requirements.md` (Goal, Runtime), and `docs/sessions/0002-20260708-openmeteo-provider-plan.md`
(the leaf design: `Transport` / `FetchRequest` / `HttpxTransport`, Provider-authored provenance;
**Phase C uses a scalar 1:1 normalizer** — `Channel` / N:M wind lands at issue 002, see
[session 0009](../../docs/sessions/0009-20260712-phase-c-spine-plan.md)).

## Implementation plan

Ordered to run the **highest-divergence-risk layer first**: the build seam
(`OfferingDef` → `SourceBinder` → `SourceRegistry` → `ProfileDef` → `Weaver`) was reshaped across
sessions 0003–0005 and **has never executed**. Weaving is **pure construction, not projection** — it
only instantiates and wires nodes, so it needs the value types merely *constructible* (they already
are), not behaviourally complete. Proving the seam assembles (Phase A) before committing the provider
and the runtime value-type behaviour (Phases B–C) de-risks the shape while a fix is still cheap.

**Phase A — weave the graph** (build path; a fix here is an afternoon, later it ripples). Source half
only — the Calculator graph has nothing to wire until 002b (`CalculatorBinder.build` itself lands now,
empty). **Planned in detail — decisions + TDD cycle list — in
[session 0007](../../docs/sessions/0007-20260711-phase-a-weave-plan.md)**; headline decisions:
`StoreFactory`-injected `Weaver` + interim `StubStore`, fake provider as test fixture only,
strict binders (`CompositionError`) with degrade owned by `Settings`, `compose(profile, catalog, …)`
in `server.py`, empty weave legal, `open_meteo_enabled=False` until Phase C.

**Phase B — make the value types behave** (runtime leaves; test-first). Independent of Phase A, but
needed before the request path can project. **Planned in detail — decisions + TDD cycle list — in
[session 0008](../../docs/sessions/0008-20260712-phase-b-value-types-plan.md)**; headline decisions:
`contains` = extent (reach) containment for every representation (tick alignment lives in the
sampling engine / `quantize` / `serves`, never geometry); `Axis.extent` = tick span (`cellular`
affects only `Cell.bounds`; the extensive horizon-edge goes to `serves` at 002); four axes mandatory
at construction; enumeration order X → Y → Z → T, T fastest (index arithmetic only in Domain +
engine); spatial tolerance `1e-9`° (float noise, not a snapping radius); **`Timeline` the class →
`CoverageRecord`** (one memory-backed realization; Timeline/Grid = domain shapes; backing may vary,
shape never); one private sampling engine (`manifold/sampling.py`) behind `Coverage.project` — no
second verb, aligned crop is the only v1 kernel, registry minted at 007.

Positions held: pure-Python sequences (numpy/xarray deferred behind the interface); aware-UTC datetimes
throughout; `intersect` / `PerPoint` / rectilinear / curvilinear / `Domain.match` stay declared seams
(concerns #12, #13, #20 untouched).

**Phase C — the spine**: swap the fake for the real Open-Meteo `Provider` — the `Transport` /
`FetchRequest` / `HttpxTransport` seam; the `Provider` + minimal scalar `Normalizer` (the `Channel`
vendor-mapping table is minted at 002 with the wind vector case) with cadence-derived provenance;
real `Reservoir.project` (pure delegate) + `Arbiter.project` (real admission, single selection,
guarded assembly); MCP adapter Selection-building + Coverage serialization under the
**`forecast_hourly`** tool. The **e2e test on mocked transport** closes here, where Phase B's
behaviour meets the graph Phase A wove. **Planned in detail — decisions + TDD cycle list — in
[session 0009](../../docs/sessions/0009-20260712-phase-c-spine-plan.md)**; headline decisions:
single-parameter leaf (capability never advertises what the server won't attempt), source lattice
optional until 006's store consumes one, exact 2 m Z cell on the request (fat cell is capability
*reach*; mixed-height bundles → concern #24), `start_hour`/`end_hour` exact-window fetch, connect
retries only, all transport faults → `runtime-failure`, per-parameter `{source, exp}` provenance in
the response.

## Acceptance criteria

- [x] `forecast_hourly(lat, lon)` over a local stdio MCP server returns an hourly `Timeline` with a single
      `ParameterData` (air temperature).
- [x] The value is in its canonical unit (Normalizer reconciles the vendor unit).
- [x] Each `ParameterData` carries per-parameter provenance with an `Origin` and `expiration`
      (run-anchored `A + Δ + L` from the provider's `CadenceDef`,
      [ADR-0003](../../docs/adr/0003-provenance-and-origin.md)).
- [x] The full spine is wired by `Weaver.weave(ProfileDef)` over a `SourceBinder`-built
      `SourceRegistry` (best-view `Reservoir` → `Arbiter` → `Source` → Open-Meteo `Provider`);
      `server.py` holds no construction logic of its own.
- [x] One end-to-end integration test drives the tool with **mocked HTTP transport** (mock the
      transport, not the provider); behavioural tests cover the deep modules with real logic (the
      `Normalizer`; the `Domain`'s point/hourly handling) through their own public interface. Thin
      pass-throughs (`Gateway`, `Source`, `Weaver` wiring) are exercised via the end-to-end test, not
      isolation-mocked.

## Blocked by

- Blocked by `issues/20260623_v1/000-project-bootstrap.md`

## User stories addressed

- User story 1
- User story 4
- User story 5
