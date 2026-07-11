# Meteoscape · Module layout

Implementation-level layout for `src/meteoscape/`. Kept out of the [architecture contract](./architecture.md); organized **by architectural layer**, not folder-per-role — see each module's inline note and the dependency rule below.

**Stack:** Python · async (I/O-bound throughout; the Provider contract is async) · typed settings + validation · an async HTTP client (provider fetch) · an MCP SDK (the first surface). *Concrete library choices live in [`v1-requirements.md`](./v1-requirements.md).*

```text
src/meteoscape/
├── __init__.py                # re-exports SourceKey (from identity) + main
├── server.py                  # thin entrypoint: catalogues + Settings → ProfileConfig → SourceBinder + CalculatorBinder → ProfileDef → weave → Gateway
├── config.py                  # Settings + OfferingDef + CalculatorSpec + ProfileConfig + store/arbiter knobs; secrets(); never handed to nodes as Settings
├── observability.py           # Sentry init seam (no-op without a DSN)
├── errors.py                  # error taxonomy: capability-mismatch / runtime / bad-request (pure leaf)
├── clock.py                   # Clock protocol + Metronome + StoppedClock; injected by SourceBinder.build
├── identity.py                # SourceKey — Tier-0 leaf; stamped onto atomic Origin
├── parameters.py              # parameter vocabulary leaf — identity types + v1 ParameterId constants
│
├── manifold/                  # algebra-knot — errors + parameters + identity
│   ├── core.py / capability.py / data.py / coverage.py / domain.py / cadence.py / provenance.py
│
├── nodes/
│   ├── reservoir.py / arbiter.py / calculator.py
│   ├── composition.py         # SourceBinder + CalculatorBinder → SourceRegistry + CalculatorRegistry; ProfileDef
│   ├── weaver.py              # Weaver.weave(ProfileDef) → Manifold (graph construction only)
│   ├── catalog/               # injected catalogues above manifold — cohesive plugin faces
│   │   ├── paramtable.py      # ParameterTable — ParameterId → ParameterDef; StaticParameterTable.core()
│   │   ├── providers.py       # OfferingSpec, SecretSlot, ProviderManifest, ProviderCatalog
│   │   └── calculators.py     # CalculatorManifest, CalculatorCatalog
│   └── providers/
│       ├── base.py            # Provider: project + capability + source_key
│       ├── normalization.py
│       └── <vendor>.py
│
└── api/                       # gateway + mcp_app

# Dependency rule: errors, parameters, clock, identity ← manifold ← nodes ; api → manifold + parameters ; server.py composes all.
# Catalogue is a role: parameters.py is the vocabulary leaf; provider/calculator/parameter-table catalogues live in nodes/catalog/ above manifold with their cohesive plugin manifests.
# Injection (never the Settings type):
#   SourceBinder(ProviderCatalog).build(defs, secrets, clock, parameters) → SourceRegistry
#   CalculatorBinder(CalculatorCatalog).build(specs) → CalculatorRegistry
#   Weaver.weave(ProfileDef) → Manifold
# tests/ mirrors modules; provider tests mock the HTTP transport.
```
