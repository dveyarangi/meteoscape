# v1 requirements

The concrete, testable **build scope** for v1 — the layer *below* the contract. It owns v1's
positions on the contract's seams (the [v1 invariants](#v1-invariants-positions-on-contract-seams))
and the specific, demonstrable decisions they imply (providers, parameters, tool surface,
inputs/outputs, acceptance criteria). The contract's seams themselves live in
[`architecture.md`](./architecture.md).

> This doc holds **concrete choices** the architecture deliberately defers (concrete providers, MCP
> tool specifics, parameter conventions). The architecture/glossary/ADRs remain the source of truth
> for the *contract*; nothing here may contradict them. Future/unscoped ideas live in
> [`ideas.md`](./ideas.md).
>
> This is a **release contract, not a progress tracker**. Implementation state and execution order
> are intentionally outside its scope.

## Goal

An installable Python package that can resolve an hourly point forecast headlessly through its
supported embedding surface and offer the same Phase 1 weather capability through a runnable MCP
server. Both select the best obtainable provider per parameter, fall back on failure, and return one
normalized, provenance-stamped **Timeline** Coverage — proving the cross-provider thesis end-to-end
within the v1 invariants.

## User stories

Three actors: the **agent** (an MCP client / AI tool calling `forecast_hourly`), the **embedder** (a
Python application author constructing and calling Meteoscape without a server), and the **operator**
(whoever configures and runs a server). Stories are numbered for stable reference from the
[acceptance criteria](#acceptance-criteria-definition-of-done); each maps to a criterion below.

**Agent**

1. As an agent, I want to request an hourly point forecast for a `latitude`/`longitude`, so that I can
   answer a weather question without integrating each vendor myself.
2. As an agent, I want to request only a subset of the core parameters, so that I get a compact answer
   scoped to what I actually need.
3. As an agent, I want to give a `start`/`end` window (or omit `end` and get everything the profile
   reaches), so that I control the forecast extent without learning per-provider limits.
4. As an agent, I want every value returned in a canonical unit, so that I can use and compare them
   without per-vendor unit handling.
5. As an agent, I want per-parameter provenance — origin and `expiration` — for each returned parameter, so
   that I know which provider/run produced each value and how fresh it is.
6. As an agent, I want the best obtainable provider chosen per parameter with automatic fallback on
   failure, so that a single vendor outage doesn't break my request.
7. As an agent, I want a forecast at my exact requested lat/lon even when it falls off a provider's grid,
   so that I don't have to interpolate the answer myself.
8. As an agent, I want the producible subset returned when some parameters can't be served, so that one
   unavailable parameter doesn't fail the whole request.
9. As an agent, I want failures reported as typed errors (`bad-request` / `capability-mismatch` /
   `runtime-failure`), so that I can react correctly — fix my input, drop the parameter, or retry.
10. As an agent, I want the tool description to narrate the available envelope (the served parameters and
    the profile's reach), so that I know what I can ask for before calling.

**Operator**

11. As an operator, I want to enable/disable providers and set their priority order via typed config, so
    that I control the quality policy without code changes.
12. As an operator, I want the TWC API key injected via config at construction, so that secrets never
    live in code or globals.
13. As an operator, I want the server to start and serve on Open-Meteo alone when the TWC key is absent,
    so that a missing optional secret degrades gracefully instead of failing startup.
14. As an operator, I want a fully-fresh repeat request served from cache without any provider call, so
    that I minimize latency and provider usage.
15. As an operator, I want the store grid step and retention interval to be configurable, so that I can
    tune cache sharing and memory bounds for my deployment.

**Embedder**

16. As an embedder, I want a documented, supported Python package surface for resolving forecasts, so
    that my application can use Meteoscape without running a protocol server.
17. As an embedder, I want failures exposed through a documented public contract, so that my
    application can handle expected failure modes without depending on internal exceptions.

## Concrete decisions

### Providers (two)

| Provider | Key | Priority | Notes |
|---|---|---|---|
| **Open-Meteo** | keyless | **primary** | global, free; exercises the keyless path |
| **TWC** (The Weather Company) | API key | fallback | exercises secrets-injection seam |

- Priority order **is** the quality policy (the `priority` reconciler selects, never combines).
  Reconfigurable via Arbiter config.
- **Missing TWC key → graceful degrade**: `Settings` never enables the offering (no `OfferingDef` is
  emitted), so the server starts and serves with Open-Meteo alone. Degrade is **enablement policy,
  owned by `Settings`**; the binder itself is **strict** — every def that reaches it is explicit
  operator intent, and it either binds or startup fails (`CompositionError`, build-time only — never a
  request-path taxonomy error).
- At least one core parameter is declared by **only one** provider's `Capability`, so the
  per-parameter capability filter is actually exercised (see acceptance §3).

### Parameters (6 canonical + 2 derived)

The agent-facing **product is 6**: air temperature (2 m), precipitation, wind **speed** (10 m), wind
**direction** (10 m), relative humidity (2 m), **cloud cover** (total column).
But **wind is canonical as u/v components** — providers
deliver native speed/direction, the **Normalizer converts to `wind_u` / `wind_v` on ingest** (both
linear, so linear interpolation of u/v *is* correct wind interpolation), and **`wind_speed` /
`wind_direction` are derived views served by Calculators** over `(wind_u, wind_v)`
([ADR-0002](./adr/0002-data-model.md) / [ADR-0004](./adr/0004-producer-resolution-and-capability.md)).

So the table holds **8 `ParameterDef`s**:

- **6 canonical** (provider-served): `air_temperature`, `precipitation`, `wind_u`, `wind_v`,
  `relative_humidity`, `cloud_cover`. `wind_u` / `wind_v` are **internal-only** — not requestable in v1.
- **2 derived** (Calculators over u/v): `wind_speed`, `wind_direction` — the **requestable** wind
  parameters. Both are lossless functions of the vector (`speed = hypot(u,v)`, `direction = atan2(...)`),
  so serving them is exact.

The set is deliberately **heterogeneous** to exercise homogenization *and* derivation: precipitation is
**extensive** (accumulation over the cell); temperature / relative-humidity / `wind_u` / `wind_v` are
**intensive** & **linear**; **`wind_direction` is circular** — the first non-linear `scale`;
**`cloud_cover` is the first cell-statistic (column) parameter** — a statistic over its Z cell's
`bounds` (`[0, TOA]`) → [ADR-0004](./adr/0004-producer-resolution-and-capability.md). v1's
degenerate nearest-neighbor read-back does **not interpolate**, so neither the linear u/v kernel nor an
angular direction kernel is exercised; any future direction kernel must be **angular** (via u/v),
never linearly averaged in degrees ([concern #5](./concerns.md#5-read-time-homogenization-fidelity)).

**Encoding (v1's position on the data-model slots, [ADR-0002](./adr/0002-data-model.md)).** All eight share
`statistic = point` (no windowed `max` / `min` / `mean`); precipitation differs only by `extent_scaling`. Because it
is **extensive**, the shared `valid_time` axis carries **hourly cell `bounds`** — precipitation reads them as
its per-cell accumulation extent, while the intensive params sample at the tick and ignore them
(accumulation rides on `extent_scaling` + extent, **not** a `CellStatistic`). One uniform hourly cell serves every
parameter, so the per-parameter bounds override stays deferred.

**Nodata rides the `present` mask, never a NaN sentinel** ([ADR-0002](./adr/0002-data-model.md)). A
Provider's `decode` emits a `ParameterData`; a vendor null becomes a **non-present cell** — a
*successful gap* — and serializes as JSON `null`. The **value at a masked cell is unspecified** and no
reader may interpret it. `present = None` is the **elided all-present case**, not an assertion that
gaps cannot occur: v1 expects Open-Meteo's hourly series to be complete, so `None` is the common
shape, but a null that does arrive is represented honestly rather than substituted. Presence is read
through `ParameterData` behaviour, so the elision is representation, not contract. A NaN sentinel is rejected because it is not dtype-agnostic and cannot be told apart from
a legitimate not-a-number value — and, at this surface, because `NaN` is not valid JSON.

The Coverage's provenance plane is `Uniform` for an atomic result; the derived wind views
**propagate** their u/v inputs' atomic origin verbatim (the derivation is lossless and invertible —
[ADR-0003](./adr/0003-provenance-and-origin.md)).

Every value is in its parameter's **canonical unit** (the Normalizer reconciles vendor units on ingest);
the unit rides the Coverage's `capability` descriptor block, not the `ParameterData` slice. Freshness is
the per-parameter provenance `expiration`.

### Request / tool contract

- **One MCP tool: `forecast_hourly`** — the shape is in the name: a future daily/aggregated product
  is a **sibling tool** (different statistics, its own narratable description), never a `step` knob
  on this one.
- Inputs: `latitude`, `longitude` (required); optional `parameters` (subset of the **6 product**
  params — temperature, precipitation, wind speed, wind direction, humidity, cloud cover; the internal
  `wind_u` / `wind_v` are **not** requestable; default all), `start`, `end`. **Output resolution is hourly** — no
  `step` input; coarser re-aggregation and
  sub-hourly stay deferred ([concern #15](./concerns.md#15-coarser-grid-resampling-and-aggregation-semantics)).
- **Location is lat/lon only** in v1 (place-name + geocoding deferred → `ideas.md`).
- The edge builds the request Selection (lat/lon **point** + hourly `valid_time` over the horizon). Each
  storing `Reservoir` internally **quantizes to its own private store lattices** for retention and
  **homogenizes back onto the requested point at read** (read-time **S**), so the
  answer lands on the **requested** lat/lon — rounding is the store lattice's own business
  ([ADR-0002](./adr/0002-data-model.md)).

### Output

- **Compact, agent-friendly JSON**: a `valid_time` array + one `ParameterData` per parameter (values),
  the canonical unit from the `capability` descriptor block, and per-parameter provenance (incl. origin
  and `expiration`).

- Response is at the **requested** lat/lon (homogenized from the store grid). The underlying native
  fidelity is **recoverable server-side via the provenance `SourceKey`**, not emitted as a dedicated field
  (offering ranking reads footprint Domain axis `step`s →
  [concern #20](./concerns.md#20-provider-multi-resolution-offerings-offering-aware-selection)).
- CoverageJSON compliance and a request `format` selector are **deferred** → `ideas.md`.

### Time axis

- **Hourly forecast, latest run.** The forward horizon is **capability-resolved, not a request cap**:
  per parameter the Arbiter admits only providers whose Capability **temporally contains** the requested
  extent (whole-request `Domain`-containment), picks the highest-priority such provider, and **falls back
  wholesale** to the next; beyond the union of provider coverage a parameter is **`capability-mismatch`**
  (omitted) — no splicing along `valid_time` in v1. The temporal footprint each Capability tests is a
  **clock-anchored window** around the run anchor (the provider's cadence,
  [ADR-0003](./adr/0003-provenance-and-origin.md)), realized by the `FootprintDomain`'s continuous
  T axis ([ADR-0002](./adr/0002-data-model.md)); the concrete per-provider `{Δ, L, max_lead}` are
  [concern #18](./concerns.md#18-clock-anchored-footprint-fidelity).
- Omitting `end` runs the window to the profile's **reach end** — what the caller gets when they do
  not say how far. There is **no configured default horizon**; `start` / `end` stay a **free window**
  (no interval enum — the `Domain` already models arbitrary extents).
- The **available envelope** the tool description narrates is the served parameters plus the profile's
  **reach** — both read off the woven root's `Capability`, which publishes the per-parameter `Domain` it
  serves; semantics, composition, and the admissible-by-construction default →
  [ADR-0007](./adr/0007-capability-carries-its-domain.md),
  [#29](./concerns.md#29-narrated-reach-what-a-profile-promises). v1 positions: because it
  composes off the woven graph, it reflects config resolution (enabled providers + present
  secrets) automatically, so a missing optional provider (for example, no TWC key) cannot advertise
  parameters or horizons the running server will not attempt. **Quality is not narrated** — a policy
  outcome the response reports per parameter via provenance
  (→ [#29](./concerns.md#29-narrated-reach-what-a-profile-promises)); quality tiers belong in
  separate profiles behind separate tools. A separate capabilities-introspection tool/resource remains
  a deferred seam.
- Current conditions fall out as the near-now sample. Observations/past data deferred.

### v1 invariants (positions on contract seams)

The positions v1 takes on the contract's seams. Each is a **seam already in the contract**, so it
lifts **without a contract change** — see the seams in
[architecture.md → Extension points](./architecture.md#extension-points) and
[Deferred decisions](./architecture.md#deferred-decisions).

- **Timeline realization, no Grid output** — each request resolves to a **single location**, served as a
  timeline; the `Store`s declare a **spatial grid** (their cache lattice), and an off-grid point is
  answered by **read-time homogenization (S)** from the enclosing store cells — not by emitting a spatial
  Grid field.
- **Single-origin atomic timelines; derived wind propagates its inputs' origin** — each **atomic**
  `ParameterData` comes from one provider's latest run, whose `issue_time` is carried by that
  parameter's `ProvenanceField`. The **derived** `wind_speed` / `wind_direction` **propagate** their
  `wind_u` / `wind_v` inputs' atomic origin **verbatim** — no synthesis: the derivation is the lossless,
  invertible inverse of the Normalizer's u/v conversion, so it preserves its input and the origin is
  literally that wind field. (Synthesis tracks the **calculation method**, not the input count: a
  `SyntheticOrigin` — lineage + method tag — is minted by a method-bearing *or* multi-origin derivation,
  neither of which v1 has → [ADR-0003](./adr/0003-provenance-and-origin.md).) Because a provider serves
  wind as one native fetch, both components are **co-sourced from the same provider/run** anyway. The
  Coverage has no response-level run identity, and v1 performs no cross-run combination.
- **Retentive in-memory `Store`s** wired into both positions (Source + best view): they **retain across
  requests** — **freshness** read off each `ParameterData`'s `expiration` (serve-vs-refill), with a
  separate **configurable retention interval** bounding memory — and hold **private per-axis lattices**
  (hourly + spatial; a Source's lattice is **a configured `StoreSpec` guess**,
  [ADR-0002](./adr/0002-data-model.md) / [ADR-0006](./adr/0006-materialization-granularity-and-store-shape.md)). A request is resolved by **`quantize`** — serve fresh
  **assimilable units** (v1: a per-parameter timeline at a spatial cell) ∪ a **store-shaped refill** of
  the missing/stale ones, each fetched **whole** (`provider.project(store_shape)`), then **homogenized
  onto the request (S)**. **Partial refill is spatial and per-parameter only**: a point reuses its cached
  enclosing units and refetches just the missing ones, and each parameter resolves independently;
  `assimilate` **replaces whole units**. A parameter's **time window is single-origin** — fetched
  **whole** from one provider
  (one run, one `expiration`); v1 never **temporally splices**, so a temporal miss or window-extension
  refetches the **whole window** from the selected provider, a primary failure **falls back wholesale**
  (the entire window from the next provider), and a window no provider can serve whole is an **error** —
  never cached-primary ∪ fallback along `valid_time`. The v1 graph wires retentive Stores in both
  positions; a non-retentive Store is only a **test double**. (In-memory only; a *persisting* `Store`
  stays deferred.)
- **`priority`-reconciler Arbiter** — priority-ordered select + fallback per parameter; only the
  default `priority` reconciler (no `tile` / `consensus` / `feather` coverage reconcilers), no explicit
  scoring.
- **Derived parameters (wind only)** — v1 exercises the Calculator seam with exactly the derived wind
  views (`wind_speed` / `wind_direction` over `wind_u` / `wind_v`): the Calculator node, its scoped
  Arbiter, Weaver memoized wiring, and **propagated** provenance. Other derivations (dewpoint, wind
  chill, …) stay deferred — as does origin **synthesis**, which arrives with the first method-bearing or
  multi-origin Calculator.
- **Null Gateway** policy (identity/limits pass through).

### Config & secrets

- One typed config (Pydantic Settings): the enabled **`OfferingDef`s** (v1 degenerate case — one per
  provider, offering `name` **always named**, e.g. Open-Meteo `best_match`), provider secrets (TWC key), and
  per-`SourceKey` priority. Secrets **injected at construction**, never read from globals.
- **Cache / grid config**: the `Store`s' **spatial step** (best-view configurable — *not* hardcoded;
  coarser = more cache sharing, more interpolation; the Source's is a configured `StoreSpec` guess)
  and **hourly** time step; cache **TTL = `expiration`**
  (serve-vs-refill freshness). Eviction is a separate **configurable retention interval** (time-based max
  age, e.g. 2 weeks) that only bounds memory — the Arbiter never serves stale entries, so retention is
  housekeeping, not correctness; **LRU is declined for v1**.

### Errors

- Mapped to MCP protocol errors via the taxonomy: `bad-request` (e.g. invalid lat/lon),
  `capability-mismatch`, `runtime-failure`. Partial success and the nodata-vs-failure semantics follow
  [Failure, nodata, and availability](./architecture.md#failure-nodata-and-availability).

### Runtime

- **Local stdio MCP server** via FastMCP. HTTP/remote transport deferred.
- **Stack (concrete libraries)**: **Python 3.14**, **async** throughout (asyncio). Runtime: **Pydantic v2**
  + **pydantic-settings** (typed config / validation), **httpx** (provider HTTP), **FastMCP** (the MCP
  surface), and **numpy** / **xarray** as the **internal backing of the canonical `Coverage` / `Domain`
  model** — kept strictly behind the `Domain` / `Coverage` interface, never in a Manifold contract
  surface. Tooling: **uv** (packaging / env), **ruff** (lint + format), **pyright** (types), **pytest** +
  **pytest-asyncio** + **pytest-cov**, **respx** (httpx mock transport), **hypothesis** (property-based
  tests). The architecture body stays library-agnostic (typed config + MCP surface); these are v1 build
  choices.

## Acceptance criteria (definition of done)

1. `forecast_hourly(lat, lon[, parameters, start, end])` returns a normalized **hourly Timeline**
   with the 6 product parameters (wind as speed/direction) — units canonicalized, per-parameter
   provenance incl. `expiration`.
2. **Select + fallback**: with both providers enabled, results come from the primary; on primary
   failure the Arbiter falls back to the other (demonstrable, e.g. via a forced provider failure).
3. **Per-parameter selection**: a parameter declared by only one provider is served from that
   provider while the rest come from the primary (capability filter).
4. **Off-grid point via homogenization (S)**: a request for an off-grid lat/lon is answered **at the
   requested point** by read-time homogenization from each `Reservoir`'s declared store grid (served from
   the nearest store cell — cached-fresh or refilled). The v1 **kernel is degenerate (nearest-neighbor,
   kind-agnostic)**: the value is the nearest store cell's, reported **at `sel.domain`**. `valid_time`
   stays hourly-aligned (identity). Per-kind / higher-order
   kernels stay deferred ([concern #5](./concerns.md#5-read-time-homogenization-fidelity)).
5. **Retentive `Store`, single-origin timelines**: wired in both positions; a **fully fresh** repeat is
   served **without a provider call**; a fresh parameter is reused while another is fetched (per-parameter,
   TTL = `expiration`). A parameter's **time window is single-origin** — a
   temporal miss or extension refetches the **whole window** from one provider, and a primary failure
   serves the **entire window** from the fallback (or errors), **never** an A-then-B `valid_time` splice.
6. **Secrets**: TWC's key is injected via typed config at construction; absent key → graceful
   degrade to Open-Meteo only.
7. **Errors** map correctly to MCP `bad-request` / `capability-mismatch` / `runtime-failure`.
8. **Tests**: unit + integration with mocked HTTP transport (per the TDD skill); provider tests mock
   the transport, not the provider.
9. **Derived wind via Calculator**: `wind_speed` / `wind_direction` are produced by a Calculator over the
   canonical `wind_u` / `wind_v` (providers deliver native speed/direction; the Normalizer canonicalizes to
   u/v on ingest), **propagating** the u/v inputs' atomic origin verbatim (lossless invertible transform —
   no `SyntheticOrigin`; the edge serializer stays on the `AtomicOrigin` path). Requesting only
   `wind_speed` routes through its Calculator and its scoped Arbiter, and the internal `wind_u` / `wind_v`
   are not directly requestable.
10. **Supported embedding path**: the public package surface settled in
    [concern #39](./concerns.md#39-python-embedding-surface-and-public-failures) resolves a v1 forecast
    without starting a protocol server. Integration tests exercise both embedded and MCP use and
    verify equivalent product semantics without prescribing their internal relationship.
11. **Embedding failures**: expected configuration and invocation failures are documented and tested
    at the public Python boundary according to the contract settled in concern #39. Callers do not
    need to import internal exception types to handle them.

## Out of scope for v1 (deferred)

Per [`architecture.md`](./architecture.md#extension-points) / `ideas.md`: Grid realization,
cross-run combination, **derived parameters beyond the wind views** (dewpoint, wind chill, …),
**origin synthesis** (`SyntheticOrigin` — method-bearing or multi-origin derivations),
coverage `reconciler`s (obs + forecast), persisting `Store`,
real quotas/rate-limits, place-name geocoding, CoverageJSON / `format` selector, HTTP transport.

## Remaining v1 design choices and explicit deferrals

- **Vertical reference is unmodeled in v1 — single-frame by construction.**
  [ADR-0002](./adr/0002-data-model.md) requires the Z axis to carry one axis-level
  **`vertical_reference`** (`above_ground` / `isobaric` / `height_above_msl`), and the implementation's
  `Axis` / `GridDomain` carry no such property. v1 is **entirely `above_ground`** — every declaration
  (2 m, 10 m, surface, the `[0, TOA]` column) shares that datum — so the attribute would be a constant
  nothing reads, and its absence changes no v1 behaviour.
  **The precondition it guards:** the slot must exist *before* any parameter in a **second frame**
  (soil depth, isobaric levels, flight levels) is declared. Z admission compares extents
  **numerically**, so without the tag `1000 hPa` would match `1000 m above ground` — a silent,
  physically meaningless admission of exactly the kind ADR-0002 rules out ("not linearly comparable";
  cross-frame conversion is a Calculator, not a resampler). No roadmap phase introduces a second frame,
  so the trigger is the **first such parameter**, and the slot must be built with that parameter rather
  than in v1. Absorbing it later is additive but not free — it touches the core geometry types and
  every Domain construction site, and `matches` must compare references before extents.
- The specific core parameter used for the §3 single-provider demonstration is intentionally open;
  the requirement is config-driven `Capability` routing rather than a particular parameter choice.
- The v1 canonical units are **committed** in [`parameters.md`](./parameters.md); conventions *beyond* the
  v1 set stay deferred at the contract level ([concern #10](./concerns.md#10-parameter-conventions)).
- **Single-flight** coalescing of concurrent same-key refills (cache-stampede guard) — already a
  `Reservoir` seam in [ADR-0004](./adr/0004-producer-resolution-and-capability.md); **deferred** in v1
  (local stdio, low concurrency), built when contention warrants.
- **Capabilities introspection** surface (an MCP tool/resource reporting the available envelope from the
  Capability union) — deferred; v1 narrates the startup-resolved active envelope in the tool description.
- **Homogenization kernel sophistication / accuracy bounds** — beyond v1's degenerate nearest-neighbor
  kernel (acceptance §4): **per-kind** kernels (linear intensive, area-weighted extensive, angular
  circular), higher-order accuracy guarantees, and a provider **`exact`** capability (true off-grid points
  bypassing the store-grid floor) stay deferred
  ([concern #5](./concerns.md#5-read-time-homogenization-fidelity)).
- **Provider-real freshness / reference-time** signal (vs the static cadence-model `{Δ, L}` estimate) → `ideas.md`.
