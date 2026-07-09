# Meteoscape · Module layout

Implementation-level layout for `src/meteoscape/`. Kept out of the [architecture contract](./architecture.md); organized **by architectural layer**, not folder-per-role — see each module's inline note and the dependency rule below.

**Stack:** Python · async (I/O-bound throughout; the Provider contract is async) · typed settings + validation · an async HTTP client (provider fetch) · an MCP SDK (the first surface). *Concrete library choices live in [`v1-requirements.md`](./v1-requirements.md).*

```text
src/meteoscape/
├── __init__.py                # re-exports SourceKey (from identity) + main
├── server.py                  # thin entrypoint: Settings → Registry.build → Weaver.weave → Gateway (no construction logic of its own)
├── config.py                  # typed settings: SourceDefs (sources()/secrets()), cache/grid knobs; never handed to nodes as a type
├── observability.py           # Sentry init seam (no-op without a DSN)
├── errors.py                  # error taxonomy: capability-mismatch / runtime / bad-request (pure leaf)
├── clock.py                   # the system time source (pure leaf): Clock protocol + Metronome (now() floored to a resolution tick) + StoppedClock (test); injected into Providers by Registry.build, never threaded through project
├── identity.py                # SourceKey — configured-producer identity (pure leaf); peer of errors/clock; stamped onto atomic Origin, shared with SourceDef
│
├── catalog/                   # the parameter catalog — a leaf (depends on nothing inward): what a parameter *is*
│   ├── vocabulary.py          #   ParameterId, Unit, Quantity (identity), ParameterDef; closed enums ExtentScaling / CellStatistic / MeasurementScale
│   └── table.py               #   ParameterTable interface + StaticParameterTable (v1: 5 canonical + 2 derived wind views); injected into Normalizer / Capability / edge
│
├── manifold/                  # the Manifold algebra-knot — imports errors + catalog + identity (the vocabulary it speaks in)
│   ├── core.py                #   Manifold protocol + facets (Countable, Writable) + Selection (the one request type: Domain + parameters, mode = the Domain's shape: Continuous|Snapped|Enumerable) +
│   │                          #   Coverage interface (= Manifold ∧ Countable ∧ capability ∧ ranges ∧ provenance, Coverage <: Manifold)
│   ├── capability.py          #   Capability = the Manifold serving facet (serves + parameters), dual of project; leaves FootprintCapability/EnumerableCapability + composites UnionCapability (Arbiter)/DerivedCapability (Calculator); Reservoir forwards
│   ├── data.py                #   ParameterData (values/present mask) — the per-parameter payload of the Coverage boundary; pure numbers positional to the Domain, descriptors ride the Coverage's capability
│   ├── coverage.py            #   concrete Coverage realizations: Timeline (v1 dense impl); Grid (later)
│   ├── domain.py              #   Domain set-algebra (contains/intersect) + EnumerableDomain refinement (enumerate/index/len); per-axis Axis via the Separable facet (base = extent span; EnumerableAxis = Sequence[Cell]; reps RegularAxis/ContinuousAxis); reps RegularDomain + FootprintDomain (v1), rectilinear/curvilinear later. Pure geometry — clock-relative RollingAxis lives in cadence.py
│   ├── cadence.py             #   CadenceDef: Provider run-cadence {Δ, L, max_lead} → anchor/issue_time, expiration, valid_time window (single source of time-relative derivations, ADR-0003); + RollingAxis, its clock-relative Axis face
│   └── provenance.py          #   the Coverage provenance plane over (parameter, point): Origin (atomic/synthetic) + Provenance + ProvenanceField (Uniform + PerParameter; PerPoint later); AtomicOrigin.source is a SourceKey (from identity)
│
├── nodes/                     # concrete Manifolds — depends on manifold/ + catalog/ + identity
│   ├── reservoir.py           #   Store (the Writable+Countable Manifold interface) + Reservoir (retention composite: Store + one child; a Source is the Reservoir(store, Provider) role — no separate type)
│   ├── arbiter.py             #   Arbiter: per-parameter fold via reconciler (priority default) + fallback; capability = UnionCapability over candidates
│   ├── calculator.py          #   Calculator: derived-parameter composite (output ⟸ inputs via fn through a scoped Arbiter); capability = induced DerivedCapability
│   ├── registry.py            #   producer leaf-factory: impl-id→class catalog; build(SourceDefs, secrets, clock) → SourceRegistry (SourceKey → RegisteredSource)
│   ├── weaver.py              #   build-time graph constructor: weave(SourceRegistry, DerivationRegistry, StoreConfig) → Manifold; ordering rides inside sources
│   └── providers/
│       ├── __init__.py
│       ├── base.py            #   Provider leaf: project + capability + source_key (identity only — never priority); composable fetch pipeline later
│       ├── normalization.py   #   Normalizer protocol + shared unit/time/parameter conversion utils
│       └── <vendor>.py        #   one deep module per provider (later)
│
└── api/                       # the edge — depends on manifold/ (not nodes)
    ├── __init__.py
    ├── gateway.py             #   caller-policy boundary → best view (null policy)
    └── mcp_app.py             #   MCP surface adapter: protocol ↔ canonical → Gateway (rest_app.py later)

# Dependency rule (acyclic, inward): errors, catalog, clock, identity ← manifold ← nodes ; api → manifold + catalog ; server.py composes all.
# nodes/registry + nodes/weaver take plain config *values* by injection from server.py (never the Settings type):
#   Registry.build(defs: Sequence[SourceDef], secrets, clock) → SourceRegistry
#   Weaver.weave(sources: SourceRegistry, derivations: DerivationRegistry, store: StoreConfig) → Manifold
# tests/ mirrors modules; provider tests mock the HTTP transport.
# future seams (not built): enrichers/, scheduler.py (background plane → synthetic Sources).
```
