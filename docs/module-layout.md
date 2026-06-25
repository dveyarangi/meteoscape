# Meteoscape · Module layout

Implementation-level layout for `src/meteoscape/`. Kept out of the [architecture contract](./architecture.md); organized **by architectural layer**, not folder-per-role — see each module's inline note and the dependency rule below.

**Stack:** Python · async (I/O-bound throughout; the Provider contract is async) · typed settings + validation · an async HTTP client (provider fetch) · an MCP SDK (the first surface). *Concrete library choices live in [`v1-requirements.md`](./v1-requirements.md).*

```text
src/meteoscape/
├── __init__.py
├── server.py                  # thin entrypoint: config → Registry → Weaver → Gateway (no construction logic of its own)
├── config.py                  # typed settings: secrets, enabled providers, policy config + derivation registry
├── observability.py           # Sentry init seam (no-op without a DSN)
├── errors.py                  # error taxonomy: capability-mismatch / runtime / bad-request (pure leaf)
│
├── manifold/                  # the Manifold algebra-knot — self-contained (imports only errors)
│   ├── core.py                #   Manifold protocol + capabilities (Countable, Writable) + Selection (the one request type: Domain + parameters, mode = the Domain's shape: Continuous|Snapped|Enumerable) +
│   │                          #   Coverage interface (= Manifold ∧ Countable ∧ ranges, Coverage <: Manifold)
│   ├── coverage.py            #   concrete Coverage realizations: Timeline (v1 dense impl); Grid (later)
│   ├── domain.py              #   Domain (set-algebra: contains/intersect) + EnumerableDomain refinement (enumerate/index/len); per-axis Axis = Sequence[Cell] (RegularAxis computes from anchor/step/count), Cell = coordinate + optional bounds, exposed via the Separable facet; representations regular (v1)/rectilinear/curvilinear-later. quantize + read-back homogenization live on the Store/Reservoir, not here
│   ├── provenance.py          #   Origin (atomic/synthetic) + Provenance + ProvenanceField (Uniform; PerPoint later)
│   └── parameters/            #   parameter vocabulary, per-parameter data, + the ParameterTable seam
│       ├── vocabulary.py      #     ParameterId, Unit, Quantity (identity), ParameterDef; closed enums Kind / CellAggregation
│       ├── data.py            #     ParameterData (values/present mask/unit/aggregation + ProvenanceField), positional to the Domain
│       └── table.py           #     ParameterTable interface + StaticParameterTable (v1: core-5); injected into Normalizer / Capability / edge
│
├── nodes/                     # concrete Manifolds — depends on manifold/
│   ├── reservoir.py           #   Store (the Writable+Countable Manifold composite interface) + Reservoir (retention composite: Store + one child)
│   ├── capability.py          #   Capability (parameters × covered Domain) — the Source→Arbiter selection contract
│   ├── arbiter.py             #   Arbiter: per-parameter fold via reconciler (priority default) + fallback
│   ├── source.py              #   Source = Reservoir(store, Provider) + Capability surface
│   ├── registry.py            #   provider leaf-factory: provider-id→class catalog, instantiate (secrets injected)
│   ├── weaver.py              #   build-time graph constructor: producers' Capabilities + policy config → wired DAG + Stores
│   └── providers/
│       ├── __init__.py
│       ├── base.py            #   composable fetch pipeline (http/auth/retry/error-map)
│       ├── normalization.py   #   Normalizer protocol + shared unit/time/parameter conversion utils
│       └── <vendor>.py        #   one deep module per provider (later)
│
└── api/                       # the edge — depends on manifold/ (not nodes)
    ├── __init__.py
    ├── gateway.py             #   caller-policy boundary → best view (null policy)
    └── mcp_app.py             #   MCP surface adapter: protocol ↔ canonical → Gateway (rest_app.py later)

# Dependency rule (acyclic, inward): errors ← manifold ← nodes ; api → manifold ; server.py composes all.
# nodes/registry + nodes/weaver take plain config *values* by injection from server.py (never the config.py type).
# tests/ mirrors modules; provider tests mock the HTTP transport.
# future seams (not built): enrichers/, scheduler.py (background plane → synthetic Sources).
```
