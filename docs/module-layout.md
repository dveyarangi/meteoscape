# Meteoscape · Module layout

Implementation-level layout for `src/meteoscape/`. Kept out of the
[architecture contract](./architecture.md); organized **by architectural layer**, not
folder-per-role — see each module's inline note and the dependency rule below. This document owns
module placement and responsibilities, not milestone status.

**Stack:** Python · async (I/O-bound throughout; the Provider contract is async) · typed settings + validation · an async HTTP client (provider fetch) · an MCP SDK (the first surface). *Concrete library choices live in [`v1-requirements.md`](./v1-requirements.md).*

```text
src/meteoscape/
├── __init__.py                # re-exports SourceKey (from identity) + main
├── server.py                  # thin entrypoint: catalogues + Settings → ProfileConfig → SourceBinder + CalculatorBinder → ProfileDef → validate_calculators → weave → Gateway
├── config.py                  # Settings + OfferingDef + CalculatorDef + ProfileConfig + store/arbiter knobs; secrets(); never handed to nodes as Settings
├── observability.py           # Sentry init seam (no-op without a DSN)
├── errors.py                  # error taxonomy: capability-mismatch / runtime / bad-request (pure leaf)
├── clock.py                   # Clock protocol + Metronome + StoppedClock; injected by SourceBinder.build
├── identity.py                # SourceKey — Tier-0 leaf; stamped onto atomic Origin
├── parameters.py              # parameter vocabulary leaf — identity types + v1 ParameterId constants
│
├── manifold/                  # algebra-knot — errors + parameters + identity
│   ├── core.py / capability.py / data.py / coverage.py / domain.py / sampling.py / cadence.py / provenance.py
│   # sampling.py — private aligned-crop/read-back engine behind Coverage.project
│
├── nodes/
│   ├── store.py / reservoir.py / arbiter.py / calculator.py
│   # store.py — Store protocol + StoreFactory + substrate implementations
│   # reservoir.py — Reservoir composite only (Store + child)
│   # arbiter.py — Source map + SourceRegistry + ArbiterPolicy (reconciler owns priority)
│   ├── composition.py         # SourceBinder + CalculatorBinder → SourceRegistry + CalculatorRegistry; ProfileDef
│   ├── weaver.py              # allocate Stores; wire Source/Calculator Producers and scoped/top Arbiters
│   ├── reach.py               # build-time wiring check over ProfileDef: validate_calculators (inputs producible + cycle guard). Geometry is composed by each node's Capability (ADR-0007), not here
│   ├── catalog/               # injected catalogues above manifold — cohesive plugin faces
│   │   ├── paramtable.py      # ParameterTable — ParameterId → ParameterDef; StaticParameterTable.core()
│   │   ├── providers.py       # OfferingSpec, SecretSlot, ProviderManifest, ProviderCatalog
│   │   └── calculators.py     # CalculatorManifest, CalculatorCatalog
│   └── providers/
│       ├── base.py            # Provider: project + capability + source_key (its geometry is published by the Capability, ADR-0007)
│       ├── normalization.py
│       └── <vendor>.py
│
└── api/                       # gateway + mcp_app

# Dependency rule: errors, parameters, clock, identity ← manifold ← nodes ; api → manifold + parameters ; server.py composes all.
# Catalogue is a role: parameters.py is the vocabulary leaf; provider/calculator/parameter-table catalogues live in nodes/catalog/ above manifold with their cohesive plugin manifests.
# Injection (never the Settings type):
#   SourceBinder(ProviderCatalog).build(defs, secrets, clock, parameters) → SourceRegistry
#   CalculatorBinder(CalculatorCatalog).build(defs, parameters) → CalculatorRegistry  # keyed by CalculatorKey; resolves output ParameterDefs
#   validate_calculators(ProfileDef) → None  # raises CompositionError; runs BEFORE weave (owns the cycle guard)
#   Weaver(stores: StoreFactory).weave(ProfileDef) → Manifold  # best-view root; concretely Reservoir(store, Arbiter), promised as the algebra (ADR-0005)
#   Capability.domain(ParameterId) → Domain  # a Manifold's Reach; composites compose it, raising if unresolvable (ADR-0007)
#   build_reconciler(ArbiterPolicy, SourceRegistry, CalculatorRegistry) → Reconciler  # holds priority[ProducerKey]
#   Arbiter(producers, reconciler)  # producers = Producer{node, key}; reconciler owns priority AND domain composition
#   compose(profile, providers, calculators, secrets, clock, stores) → Gateway
# tests/ mirrors src; provider tests mock the HTTP transport.
```
