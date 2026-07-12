# Meteoscape product roadmap

This document describes Meteoscape as a product, not only as an architecture. It
captures the target audience, differentiated product surface, competitor edges,
gaps, and a staged roadmap from v1 to a possible hosted cloud competitor.

The architecture contract lives in [`architecture.md`](./architecture.md). The
concrete v1 build scope lives in [`v1-requirements.md`](./v1-requirements.md).
This document should guide sequencing and product judgment.

## Product thesis

Meteoscape is a self-hostable weather intelligence engine that turns
heterogeneous weather sources into trusted, composable, task-oriented weather
products.

The goal is not merely to fetch weather data. The goal is to answer:

- Which weather answer should I trust for this task?
- Which source produced each value, when, and how fresh is it?
- What happens if a provider is unavailable, stale, missing a parameter, or
  weaker for this location and lead time?
- How do raw forecasts become decision-ready signals?

Open-Meteo and similar APIs are excellent at:

```text
latitude/longitude + variables -> weather JSON
```

Meteoscape should become excellent at:

```text
weather need -> best available answer + provenance + fallback + confidence + policy
```

## Audience and need

For casual application developers, a simple public forecast API is often enough.
Open-Meteo should satisfy many of those users. Meteoscape has a stronger reason
to exist when weather affects money, safety, scheduling, automation, or
accountable decisions.

Primary audiences:

- AI agents and MCP users that need weather-aware actions with provenance,
  freshness, and confidence.
- Operational teams in energy, utilities, logistics, construction, agriculture,
  events, field service, drones, renewables, municipal operations, and insurance.
- Platform teams that already integrate several weather vendors and want one
  policy-controlled substrate.
- Operators who need to **run the engine themselves** — on-prem, regional cloud,
  air-gapped, or sovereignty-constrained environments.
- Teams that want to inject local stations, radar, satellite, model output, or
  private observations into that same engine.
- Advanced local-weather, IoT, and home-automation users who care about source
  control and where the stack runs.

The strongest need appears where one or more of these are true:

- A single provider is not trusted enough.
- The stack must be self-hosted (control, sovereignty, residency, air-gap).
- Local or private data matters.
- The output is a decision, not just a meteorological variable.
- The system must explain why it chose an answer.
- Provider policy, cost, region, licensing, or data sovereignty matters.
- Forecast confidence should improve from archived performance.

## Product pillars

### 1. Homogenized cross-provider access

One request shape resolves across providers into canonical parameters, canonical
units, a common time/space domain, and a compact response.

Differentiator:

- Callers ask for weather semantics, not vendor fields.
- Providers are normalized at the edge.
- The engine can select per parameter and fall back when a source fails.

### 2. Caching, storage, and freshness

Stores are not only performance caches. They are part of correctness: values are
served only while fresh under provider cadence or provider-real freshness
metadata.

Differentiator:

- Freshness is visible in provenance.
- Repeat requests can avoid vendor calls without serving stale data.
- Later archives can support verification and provider skill scoring.

### 3. Composable API pipelines

The Manifold graph lets sources, stores, arbiters, calculators, and future
profiles compose under one projection model.

Differentiator:

- New product surfaces can reuse the same internals.
- "Best view", comparison, consensus, archives, and decisions can be added as
  profiles rather than separate systems.

### 4. Derived parameters as composable DAGs

Derived weather products are first-class nodes, not ad hoc response fields.

Differentiator:

- Wind speed/direction from canonical wind components is the v1 proof.
- Later derivations can include dewpoint, heat index, wind chill,
  evapotranspiration, solar signals, fire-weather ingredients, and domain
  indices.
- Synthetic provenance can record derivation lineage.

### 5. Consensus, disagreement, and confidence

Meteoscape should expose when sources agree, disagree, fail, or go stale.

Differentiator:

- Confidence becomes a product surface.
- Comparison precedes blending.
- Archives can later calibrate confidence by source, region, parameter, and lead
  time.

### 6. MCP-native surface

The first surface is for agents, not generic dashboards.

Differentiator:

- Simple tools can expose trusted weather answers to agent workflows.
- Trace and provenance help agents avoid treating one API response as ground
  truth.
- Other surfaces, including REST, can follow without changing the engine.

### 7. Task-oriented surfaces

Task-oriented products are custom compositions — derived fields, thresholds, and
policy wired for an operational need (window suitability, go / no-go, domain
indices, and similar). The caller sees a **task-shaped API response**, not a raw
forecast dump; provenance can ride along when useful.

Differentiator:

- Operators and packs can add task-specific logic without forking the product.
- Thin packs first; the catalogue grows with proven needs.

### 8. Archive management and statistical analysis

Retaining observations, forecasts, and model runs unlocks retrospective skill
analysis.

Differentiator:

- Provider selection can improve from historical performance.
- Users can backtest decision rules.
- Forecast confidence can be calibrated instead of guessed.

### 9. Self-hosting

Meteoscape is meant to be run by the operator: on-prem, regional cloud,
air-gapped, or under data-residency constraints. Packaging, secrets, and policy
live with the deployment.

Differentiator:

- Operators control where the engine runs, what it talks to, and how secrets and
  policy are held.
- Bring-your-own provider keys follow from that control.

### 10. Local and private data as sources

The same resolution pipeline can admit local stations, regional radars,
satellite products, private forecasts, and internal model output.

Differentiator:

- Public weather APIs cannot see many private/local data sources.
- Private sources participate in fallback, comparison, and decision products
  under the same policy as public providers.

### 11. Alerts and delivery channels

Two related seams:

- **Alerts** — ingest official warnings and/or raise threshold-based alerts from
  model or local data; shape, deduplicate, and prioritize them. Alert records
  carry provenance, confidence, and affected area.
- **Delivery** — how those alerts reach a consumer. First path is **poll** (MCP /
  API pull). Push, email templates, WhatsApp, SMS, and similar channels come
  later.

## Competitive landscape

### Open-Meteo

Open-Meteo is the strongest benchmark. It has broad model coverage, simple HTTP
APIs, forecast and historical products, geocoding and adjacent APIs, a generous
free tier, and strong developer adoption.

Where Open-Meteo is stronger:

- Public forecast API convenience.
- Model breadth and global coverage.
- Immediate developer usability.
- Hosted scale and public trust.
- No-key/free-tier adoption.
- Simplicity for common app use cases.

Where Meteoscape can differentiate:

- Cross-vendor arbitration (and later private-source arbitration).
- Per-parameter provenance and freshness.
- Policy-controlled provider choice.
- Disagreement and confidence as first-class outputs.
- Self-hostable deployment from early versions.
- Agent-native MCP surface.
- Composable derived products and task-oriented decisions.
- Archive-backed verification and provider skill scoring.

Strategic implication:

- Do not compete first as "Open-Meteo, but newer".
- Use Open-Meteo-like simplicity as the usability bar.
- Compete on trust, policy, comparison, self-host control, and decisions.

### Alliander Weather Provider API

Alliander's project is a mature weather data access and formatting platform with
FastAPI, OpenAPI, Docker, xarray/NetCDF workflows, tests, and concrete KNMI/CDS
adapters.

Where Alliander is stronger:

- Mature REST product and operational packaging.
- Concrete KNMI/CDS source support.
- NetCDF/CSV/JSON output formats.
- Dataset/repository maintenance scripts.
- Existing test and documentation surface.

Where Meteoscape can differentiate:

- Caller asks for weather semantics rather than selecting source/model.
- Automatic per-parameter selection and fallback.
- Provenance/freshness as core contract.
- MCP and agent workflow focus.
- Composable Manifold pipeline for future profiles.
- Decision and confidence surfaces beyond data retrieval.

Strategic implication:

- Alliander validates a real need for uniform weather access, especially in
  operational/data-heavy settings.
- It is not the primary competitive threat for a decision/trust product.

### Commercial weather APIs

Examples include OpenWeather, Tomorrow.io, Visual Crossing, The Weather Company,
Meteomatics, and region-specific providers.

Where they are stronger:

- Hosted commercial reliability.
- Existing data licensing and enterprise sales.
- Rich provider-specific products.
- Support and SLAs.

Where Meteoscape can differentiate:

- Self-hostable multi-vendor substrate (run it yourself; bring your own keys).
- Multi-vendor fallback instead of single-vendor lock-in.
- Optional private/local source integration on that same substrate.
- Transparent provenance and comparison across providers.
- Task-specific products that can include commercial APIs as inputs.

Strategic implication:

- Commercial providers should often be inputs to Meteoscape, not only
  competitors.
- The product should make provider substitution, fallback, and auditability
  valuable.

## Roadmap

### Phase 1: Best View Foundation

Purpose: prove the normalized, provenance-stamped forecast engine end to end.

Core scope:

- MCP `forecast_hourly`.
- Canonical v1 parameters and units.
- Timeline output for a point and hourly time window.
- Open-Meteo as first provider.
- One fallback provider or test provider path.
- Priority-based Arbiter selection.
- Per-parameter provenance and expiration.
- Derived wind speed/direction from canonical components.
- In-memory Store/Reservoir freshness semantics.
- Minimal structured logs for resolution decisions.
- Capability-mismatch, runtime-failure, and bad-request errors.

Proof:

- Ask once and get one normalized answer.
- Repeat fresh request avoids provider calls.
- Primary failure falls back.
- Each returned parameter carries origin and expiration.

Explicit non-goals:

- Consensus.
- Decision products.
- Archives.
- Sophisticated interpolation.
- REST, NetCDF, CSV.
- Provider skill scoring.

### Phase 2: Operational Substrate

Purpose: make the engine useful as a **self-hosted** operational substrate —
packaging, config, secrets, and multi-provider operation under operator control.

Core scope:

- Provider-real freshness metadata where available.
- Configurable provider enablement, secrets, and priority policy.
- Provider capability discovery surface.
- Cache hit/miss metrics and provider latency/error metrics.
- Retention tuning and store observability.
- Additional provider plugins such as NWS, KNMI, TWC, Tomorrow.io, or regional
  public services.
- Basic self-host packaging and operational docs.
- Optional REST surface if demand appears.
- Local/regional station provider interface (optional in this phase).

Proof:

- Operators can deploy and run Meteoscape themselves against several providers.
- Operators can inspect what the deployment can answer.
- Bring-your-own keys and policy work without a hosted control plane.

### Phase 3: Comparison and Confidence

Purpose: expose the value that makes Meteoscape more than a simple forecast API.

Core scope:

- `compare_forecast`.
- Return selected best view plus provider alternatives.
- Per-parameter and per-time disagreement metrics.
- Fallback trace sidecar.
- Confidence labels or scores.
- Source agreement/disagreement explanations.
- Provider freshness and latency in diagnostics.
- Quality scoring beyond static priority, initially metadata-only.

Proof:

- The product can explain which forecast to trust.
- Users can see when rain timing, wind, or temperature materially disagree.
- Agents can condition decisions on confidence, not only values.

### Phase 4: Composable Weather DAGs

Purpose: turn derived parameters into reusable product assets.

Core scope:

- Derived parameter registry.
- Calculator DAGs beyond wind.
- Synthetic provenance lineage.
- Reusable derivation packs.
- User-defined derivation hooks.
- Dependency and capability closure validation.
- Incremental recompute as an optimization if needed.

Candidate derivations:

- Dewpoint.
- Heat index.
- Wind chill.
- Feels-like temperature.
- Evapotranspiration.
- Solar potential.
- Fire-weather ingredients.
- Road/frost/icing ingredients.

Proof:

- Weather products can be composed, audited, and reused.
- Derived values retain traceable lineage back to source parameters.

### Phase 5: Task-oriented surfaces

Purpose: ship task-shaped API products for operational needs, built from
composable derived fields and policy.

Core scope:

- Task-shaped request / response APIs (outcome, drivers, thresholds as needed).
- One or two narrow packs as experiments.
- Provenance on the response when it earns its place.

Proof:

- Callers get an operational answer from a task API, not a DIY script over raw
  forecasts.
- Packs stay few until the pattern is proven.

### Phase 6: Archives, Verification, and Statistical Analysis

Purpose: build the long-term moat.

Core scope:

- Archive management for observations, forecasts, and model runs.
- Run collections keyed by issue time.
- Forecast-vs-observation verification.
- Provider skill scoring by region, lead time, parameter, and season.
- Confidence calibration from historical performance.
- Backtesting for decision products and thresholds.
- Statistical summaries and climatology baselines.

Proof:

- Meteoscape learns which sources are trustworthy where.
- Quality scoring can become data-driven rather than statically configured.

### Phase 7: Alerts and delivery channels

Purpose: alert product first; delivery channels second.

Core scope:

- Official alert ingestion.
- Threshold alerts from model or local data.
- Deduplication and severity shaping.
- Alert records with provenance, confidence, and affected area.
- **Poll delivery** (MCP / API) as the first channel.
- Later: push, webhooks, email templates, SMS, WhatsApp, and similar.
- Suppression / policy where it earns its place.

Proof:

- Callers can poll a coherent alert set tied to sources and freshness.
- Push and messaging channels are additive, not required for the alert product.

### Phase 8: Hosted Cloud Product

Purpose: become a possible Open-Meteo-class competitor, but with a different
center of gravity.

Cloud thesis:

```text
Hosted weather confidence and decision API, with Open-Meteo-class convenience
plus multi-source trust, provenance, and task products.
```

Core scope:

- Hosted forecast and comparison APIs.
- Managed provider integrations.
- Bring-your-own-provider keys.
- Optional private-source onboarding for hosted tenants.
- Hosted archives and verification.
- Team/org policies.
- Usage metering and billing hooks.
- SLA and support model.
- Public SDKs and examples.
- Free/simple tier only when the trust layer is already compelling.

Proof:

- Users choose Meteoscape for trust, confidence, and decision surfaces, not only
  because it can return a forecast.

## Gaps to close

### Product gaps

- The first demo must show value beyond "forecast via MCP".
- The language must lead with user outcomes, not internal algebra.
- Task packs need careful domain scoping; they are task APIs, not a generic
  "weather advice" catalogue.
- Confidence must be honest. Early versions may use simple disagreement and
  freshness signals before archive-calibrated skill scores exist.
- Open-Meteo-level ease of use remains the usability bar even when the internals
  are more advanced.

### Technical gaps

- Concrete providers are not implemented yet.
- Core `project` behavior for Reservoir, Arbiter, Calculator, Gateway, and
  domains still needs implementation.
- Store behavior and freshness semantics need behavior tests.
- Resolution trace sidecar shape is still open.
- Homogenization kernels are initially simple and need a later fidelity roadmap.
- Provider capability discovery needs a product surface.
- Self-host packaging and operational docs are not yet present.

### Go-to-market gaps

- The likely audience is smaller and more serious than a general free weather
  API audience.
- Stars are not the main success metric. Usage, deployments, integrations,
  retained users, and paid operational value matter more.
- The cloud competitor path requires provider licensing, hosting reliability,
  billing, support, and trust.

## Validation plan

Validate demand before overbuilding later phases.

Signals to seek:

- Developers ask for fallback, provenance, or self-hosted deployment.
- Users compare Meteoscape output against Open-Meteo rather than asking why it
  exists.
- Agents use provenance/confidence in downstream decisions.
- Operators deploy without a hosted control plane (keys, policy, packaging).
- Separately: operators want to plug in private stations or regional sources.
- Users ask for task products after seeing normalized forecasts.
- Archives become useful for explaining provider quality.

Early validation demos:

1. A single `forecast_hourly` response with per-parameter provenance and expiration.
2. A forced provider failure showing fallback and trace.
3. A self-hosted multi-provider run with operator-supplied keys and priority.
4. A comparison response showing source disagreement over a rain window.
5. A local station overriding or augmenting a public provider.
6. A thin task-pack API for one operational need.

## Positioning

Short positioning:

> Trusted weather decisions from heterogeneous weather sources.

Developer positioning:

> One self-hostable weather engine for normalized forecasts, provider fallback,
> provenance, confidence, and composable derived weather products.

Agent positioning:

> An MCP-native weather tool that tells agents not only what the forecast is, but
> where it came from, whether it is fresh, whether sources disagree, and how much
> to trust it for the task.

Cloud positioning:

> A hosted weather confidence and decision API for teams that need more than a
> single-provider forecast.

## Strategic rule

Do not build "Open-Meteo, but newer".

Build the layer that makes Open-Meteo, commercial providers, and official
services trustworthy, comparable, policy-aware, and actionable. Self-hosting is
the primary deployment form; private/local sources are an optional extension of
the same engine.
