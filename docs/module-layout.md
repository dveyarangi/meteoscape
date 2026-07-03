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
├── catalog/                   # the parameter catalog — a leaf (depends on nothing inward): what a parameter *is*
│   ├── vocabulary.py          #   ParameterId, Unit, Quantity (identity), ParameterDef; closed enums ExtentScaling / CellStatistic / MeasurementScale
│   └── table.py               #   ParameterTable interface + StaticParameterTable (v1: core-5); injected into Normalizer / Capability / edge
│
├── manifold/                  # the Manifold algebra-knot — imports errors + catalog (the vocabulary it speaks in)
│   ├── core.py                #   Manifold protocol + facets (Countable, Writable) + Selection (the one request type: Domain + parameters, mode = the Domain's shape: Continuous|Snapped|Enumerable) +
│   │                          #   Coverage interface (= Manifold ∧ Countable ∧ capability ∧ ranges ∧ provenance, Coverage <: Manifold)
│   ├── capability.py          #   Capability (per-parameter ParameterDef × covered Domain) — the Manifold serving facet; Coverage/Provider expose it (composition open: concern #16)
│   ├── data.py                #   ParameterData (values/present mask) — the per-parameter payload of the Coverage boundary; pure numbers positional to the Domain, descriptors ride the Coverage's capability
│   ├── coverage.py            #   concrete Coverage realizations: Timeline (v1 dense impl); Grid (later)
│   ├── domain.py              #   Domain (set-algebra: contains/intersect) + EnumerableDomain refinement (enumerate/index/len); per-axis Axis = Sequence[Cell] (RegularAxis computes from anchor/step/count), Cell = coordinate + optional bounds (a Z cell's coordinate is (vertical_reference, value)), exposed via the Separable facet; representations regular (v1)/rectilinear/curvilinear-later. quantize + read-back homogenization live on the Store/Reservoir, not here
│   └── provenance.py          #   the Coverage provenance plane over (parameter, point): Origin (atomic/synthetic) + Provenance + ProvenanceField (Uniform + PerParameter; PerPoint later)
│
├── nodes/                     # concrete Manifolds — depends on manifold/ + catalog/
│   ├── reservoir.py           #   Store (the Writable+Countable Manifold composite interface) + Reservoir (retention composite: Store + one child)
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

# Dependency rule (acyclic, inward): errors, catalog ← manifold ← nodes ; api → manifold + catalog ; server.py composes all.
# nodes/registry + nodes/weaver take plain config *values* by injection from server.py (never the config.py type).
# tests/ mirrors modules; provider tests mock the HTTP transport.
# future seams (not built): enrichers/, scheduler.py (background plane → synthetic Sources).
```
