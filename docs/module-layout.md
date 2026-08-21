# Meteoscape · Module layout

Implementation-level layout for `src/meteoscape/`. Kept out of the
[architecture contract](./architecture.md); organized **by architectural layer**, not
folder-per-role — see each module's inline note and the dependency rule below. This document owns
module placement and responsibilities, not milestone status.

**Stack:** Python · async (I/O-bound throughout; the Provider contract is async) · typed settings + validation · an async HTTP client (provider fetch) · an MCP SDK (the first surface). *Concrete library choices and their pins live in [`pyproject.toml`](../pyproject.toml).*

```text
src/meteoscape/
├── __init__.py                # re-exports SourceKey (from identity) + main
├── server.py                  # thin entrypoint: catalogues + declared profile (OFFERINGS/CALCULATORS/ROOT_STORE) + secrets → ProfileConfig → binders → ProfileDef → weave → Gateway
├── config.py                  # profile declaration types (StoreSpec, OfferingDef, CalculatorDef, ArbiterPolicy, ProfileConfig) + secret_env_name / secrets_from_env — the one home of the env spelling; no typed env-config object
├── gateway.py                 # Gateway (caller-policy boundary + composition handle: resolve + aclose) + the Closeable facet — above the surfaces, since every surface receives a composition and none provides one; a caller hands it the construction sites and it decides which of them hold anything (the system's one isinstance-Closeable test)
├── observability.py           # Sentry init seam (no-op without a DSN)
├── errors.py                  # error taxonomy: capability-mismatch / runtime / bad-request + build-time CompositionError (pure leaf; Tier-0 so manifold and nodes each author their own composition errors — ADR-0007)
├── clock.py                   # Clock protocol + Metronome + StoppedClock; injected by SourceBinder.build
├── identity.py                # SourceKey — Tier-0 leaf; stamped onto atomic Origin
├── parameters.py              # parameter vocabulary leaf — identity types + v1 ParameterId constants
│
├── manifold/                  # algebra-knot — errors + parameters + identity
│   ├── core.py / capability.py / data.py / coverage.py / domain.py / sampling.py / cadence.py / provenance.py
│   # sampling.py — private aligned-crop/read-back engine behind Coverage.project
│   # domain.py — geometry, incl. the per-axis extent-containment predicates both reach consumers read downward (ADR-0007)
│
├── nodes/
│   ├── store.py / reservoir.py / arbiter.py / calculator.py
│   # store.py — Store protocol + StoreFactory (allocates substrates and remembers them, so the composition root can release what the graph opened) + substrate implementations
│   # reservoir.py — Reservoir composite only (Store + child)
│   # arbiter.py — Producer + Reconciler (owns priority AND per-parameter domain composition) + build_reconciler
│   ├── composition.py         # SourceBinder + CalculatorBinder → SourceRegistry + CalculatorRegistry; ProfileDef; validate_calculators (weave's precondition: inputs producible + cycle guard); require_separable — the shared build-time geometry guard both composition folds (arbiter, calculator) narrow through, each supplying its own rule and declarer (ADR-0007)
│   ├── weaver.py              # allocate Stores; wire Source/Calculator Producers and scoped/top Arbiters
│   ├── catalog/               # injected catalogues above manifold — cohesive plugin faces
│   │   ├── paramtable.py      # ParameterTable — ParameterId → ParameterDef; StaticParameterTable.core()
│   │   ├── providers.py       # OfferingSpec, SecretSlot, ProviderManifest, ProviderCatalog, secret_slots
│   │   └── calculators.py     # CalculatorManifest, CalculatorCatalog
│   ├── providers/
│   │   ├── base.py            # Provider: project + capability + source_key (its geometry is published by the Capability, ADR-0007); Transport/FetchRequest
│   │   ├── timeline.py        # point+series family: TimelineProvider (algebra) + RollingTimeline (live member) + TimelineProbe/TimelineDelivery/TapTable (vendor seam)
│   │   ├── normalization.py   # shared native→canonical conversion edges (scale factors, quantity transforms)
│   │   ├── <vendor>.py        # one vendor's Probe + tap table + cadence + ProviderManifest — declarations, no algebra
│   │   └── builtin.py         # the shipped provider set — CATALOG: ProviderCatalog; availability is a system prop, the first named set (#26)
│   └── calculators/
│       ├── wind.py            # wind_uv kernel + its CalculatorManifest
│       └── builtin.py         # the shipped calculator set — CATALOG: CalculatorCatalog
│
└── api/                       # mcp_app — the surface adapters; each registers its own shutdown hook over the Gateway it is handed

# Dependency rule: errors, parameters, clock, identity ← manifold ← nodes ; manifold ← gateway ← api ; api → manifold + parameters + gateway + nodes/catalog's ParameterTable (vocabulary only — never a binder, the Weaver, or a node: a surface receives a composition, it never builds one) ; server.py composes all.
#   gateway.py imports the algebra and nothing else; nodes/ never imports it (release is declared structurally, by defining aclose), so gateway and nodes are independent peers above manifold.
# Catalogue is a role: parameters.py is the vocabulary leaf; provider/calculator/parameter-table catalogues live in nodes/catalog/ above manifold with their cohesive plugin manifests.
# Injection (plain values only):
#   SourceBinder(ProviderCatalog).build(defs, secrets, clock, parameters) → SourceRegistry  # secrets: impl_id → value
#   CalculatorBinder(CalculatorCatalog).build(defs, parameters) → CalculatorRegistry  # keyed by CalculatorKey; resolves output ParameterDefs from the manifest
#   validate_calculators(ProfileDef) → None  # raises CompositionError; weave's first step / precondition (owns the cycle guard)
#   Weaver(stores: StoreFactory, clock: Clock).weave(ProfileDef) → Manifold  # best-view root; concretely Reservoir(store, Arbiter, clock), promised as the algebra (ADR-0005)
#   Capability.reach(ParameterId) → Domain  # a Manifold's Reach; composites compose it, raising if unresolvable (ADR-0007)
#   build_reconciler(ArbiterPolicy, SourceRegistry, CalculatorRegistry) → Reconciler  # holds priority[ProducerKey]
#   Arbiter(producers, reconciler, scope=None)  # producers = Producer{node, key}; reconciler owns priority AND domain composition; scope = the parameters this Arbiter resolves (a Calculator's inputs at a scoped one)
#   compose(profile, providers, calculators, secrets, clock) → Gateway  # builds StoreFactory(clock): one clock, structurally; hands the Gateway both construction sites in construction order (SourceRegistry.providers, StoreFactory.created), so it can release what they hold
# tests/deterministic/ mirrors src; provider tests mock the HTTP transport; `testpaths` makes it
# the default `uv run pytest` scope. tests/parity/ holds the live opt-in Provider parity checks
# (`uv run pytest tests/parity`): comparison.py engine + readers/ (import-clean reference readers)
# → edge/provider.md.
```
