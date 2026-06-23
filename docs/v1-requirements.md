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

## Goal

A runnable MCP server that answers an hourly point-forecast request by selecting the best obtainable
provider per parameter, falling back on failure, and returning one normalized, provenance-stamped
**Timeline** Coverage — proving the cross-provider thesis end-to-end within the v1 invariants.

## Concrete decisions

### Providers (two)

| Provider | Key | Priority | Notes |
|---|---|---|---|
| **Open-Meteo** | keyless | **primary** | global, free; exercises the keyless path |
| **TWC** (The Weather Company) | API key | fallback | exercises secrets-injection seam |

- Priority order **is** the quality policy (implicit-priority Arbiter; selects, never combines).
  Reconfigurable via Arbiter config.
- **Missing TWC key → graceful degrade**: the Registry simply does not instantiate the unconfigured
  provider; the server starts and serves with Open-Meteo alone. (No fail-fast in v1.)
- At least one core parameter is declared by **only one** provider's `Capability`, so the
  per-parameter capability filter is actually exercised (see acceptance §3).

### Parameters (core 5, provider data only — no synthetic)

- air temperature (2 m)
- precipitation
- wind speed (10 m)
- wind direction (10 m)
- relative humidity (2 m)

The set is deliberately **heterogeneous** to exercise homogenization: precipitation is **extensive**
(accumulation over the cell), temperature / relative-humidity / wind-speed are **intensive**, and **wind
direction is circular** — it must be interpolated **angularly** (e.g. via sin/cos or u/v components),
never linearly averaged in degrees.

**Encoding (v1's position on the data-model slots, [ADR-0002](./adr/0002-data-model.md)).** All five share
`aggregation = point` (no windowed `max` / `min` / `mean`); precipitation differs only by `kind`. Because it
is **extensive**, the shared `valid_time` axis carries **hourly `bounds`** — precipitation reads them as its
per-cell accumulation extent, while the intensive params sample at the tick and ignore the extent
(accumulation rides on `kind` + extent, **not** a `CellAggregation`). One uniform hourly extent serves every
parameter, so the per-parameter `bounds` override stays deferred. Every `ParameterData` carries
`present = None` and a `Uniform` provenance.

Each `ParameterData` carries its canonical unit (Normalizer reconciles vendor units) and per-parameter
provenance incl. `expiration`.

### Request / tool contract

- **One MCP tool: `get_forecast`.**
- Inputs: `latitude`, `longitude` (required); optional `parameters` (subset of the core 5; default
  all), `start`, `end`. **Output resolution is hourly** — no `step` input; coarser re-aggregation and
  sub-hourly stay deferred ([concern #15](./concerns.md#15-coarser-grid-resampling-and-aggregation-semantics)).
- **Location is lat/lon only** in v1 (place-name + geocoding deferred → `ideas.md`).
- The edge builds the request Selection (lat/lon **point** + hourly `valid_time` over the horizon). Each
  `Countable` `Reservoir` internally **quantizes to its own declared store grid** for retention and
  **homogenizes back onto the requested point at read** (read-time **S**), so the
  answer lands on the **requested** lat/lon — rounding is the store lattice's own business
  ([ADR-0002](./adr/0002-data-model.md)).

### Output

- **Compact, agent-friendly JSON**: a `valid_time` array + one `ParameterData` per parameter (values +
  unit + per-parameter provenance, incl. origin and `expiration`).

- Response is at the **requested** lat/lon (homogenized from the store grid; the underlying native/store
  resolution rides in provenance).
- CoverageJSON compliance and a request `format` selector are **deferred** → `ideas.md`.

### Time axis

- **Hourly forecast, latest run.** The forward horizon is **capability-resolved, not a request cap**:
  per parameter the Arbiter admits only providers whose Capability **temporally contains** the requested
  extent (whole-request `Domain`-containment), picks the highest-priority such provider, and **falls back
  wholesale** to the next; beyond the union of provider coverage a parameter is **`capability-mismatch`**
  (omitted) — no splicing along `valid_time` in v1.
- A configurable **default horizon** (≈ 7 days) applies only when the caller omits `end`; `start` / `end`
  stay a **free window** (no interval enum — the `Domain` already models arbitrary extents).
- The **available envelope** (parameters × max horizon) is the **union of provider Capabilities**; v1
  narrates it statically in the tool description (a capabilities-introspection tool/resource is a
  deferred seam).
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
- **Single-origin timeline per parameter** — each `ParameterData` comes from one provider's latest run,
  whose `issue_time` is carried by that parameter's `ProvenanceField`; the Coverage has no response-level
  run identity, and v1 performs no cross-run combination.
- **Retentive in-memory `Store`s** wired into both positions (Source + best view): they **retain across
  requests** — **freshness** read off each `ParameterData`'s `expiration` (serve-vs-refill), with a
  separate **configurable retention interval** bounding memory — and **declare their grid `Domain`**
  (hourly + spatial; the Source's is **provider-exact or a configured guess**,
  [ADR-0002](./adr/0002-data-model.md)). A request is resolved by **`quantize`** — serve fresh
  **assimilable units** (v1: a per-parameter timeline at a spatial cell) ∪ a **store-shaped refill** of
  the missing/stale ones, each fetched **whole** (`provider.project(store_shape)`), then **homogenized
  onto the request (S)**. **Partial refill is spatial and per-parameter only**: a point reuses its cached
  enclosing units and refetches just the missing ones, and each parameter resolves independently;
  `assimilate` **replaces whole units**. A parameter's **time window is single-origin** — fetched
  **whole** from one provider
  (one run, one `expiration`); v1 never **temporally splices**, so a temporal miss or window-extension
  refetches the **whole window** from the selected provider, a primary failure **falls back wholesale**
  (the entire window from the next provider), and a window no provider can serve whole is an **error** —
  never cached-primary ∪ fallback along `valid_time`. A non-retentive pass-through `Store` survives only
  as a **test double**, not a wired position. (In-memory only; a *persisting* `Store` stays deferred.)
- **`priority`-reconciler Arbiter** — implicit-priority select + fallback per parameter; only the
  default `priority` reconciler (no `tile` / `consensus` / `feather` coverage reconcilers), no explicit
  scoring.
- **No synthetic parameters** — provider data only; no calculators / combiners.
- **Null Gateway** policy (identity/limits pass through).
- **Freshness** read straight off each `ParameterData`'s provenance `expiration` (`fresh ⇔ expiration > now`)
  — i.e. the run is still current; `expiration` (`fetched_at + cadence`) proxies run-rollover
  ([concern #4](./concerns.md#4-issue_time-definition)).

### Config & secrets

- One typed config (Pydantic Settings): enabled providers, provider secrets (TWC key), Arbiter
  ordering. Secrets **injected at construction**, never read from globals.
- **Cache / grid config**: the `Store`s' **spatial step** (best-view configurable — *not* hardcoded;
  coarser = more cache sharing, more interpolation; the Source's is provider-exact or a configured guess)
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
- **Stack (concrete libraries)**: Python · async throughout · **Pydantic v2** (typed config + canonical
  model / validation) · **httpx** (provider HTTP) · **FastMCP / official MCP SDK** (the surface). The
  architecture body stays library-agnostic (typed config + MCP surface); these are v1 build choices.

## Acceptance criteria (definition of done)

1. `get_forecast(lat, lon[, parameters, start, end])` returns a normalized **hourly Timeline**
   with the core-5 parameters — units canonicalized, per-parameter provenance incl. `expiration`.
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

## Out of scope for v1 (deferred)

Per [`architecture.md`](./architecture.md#extension-points) / `ideas.md`: Grid realization,
cross-run combination, synthetic parameters/calculators, coverage `reconciler`s (obs + forecast), persisting `Store`,
real quotas/rate-limits, place-name geocoding, CoverageJSON / `format` selector, HTTP transport.

## Open / TBD during build

- Which specific core parameter is single-provider for the §3 demo (config-driven `Capability`).
- Concrete canonical unit choices per parameter (parameter conventions still deferred at contract
  level).
- **Single-flight** coalescing of concurrent same-key refills (cache-stampede guard) — already a
  `Reservoir` seam in [ADR-0004](./adr/0004-producer-resolution-and-capability.md); **deferred** in v1
  (local stdio, low concurrency), built when contention warrants.
- **Capabilities introspection** surface (an MCP tool/resource reporting the available envelope from the
  Capability union) — deferred; v1 narrates statically in the tool description.
- **Homogenization kernel sophistication / accuracy bounds** — beyond v1's degenerate nearest-neighbor
  kernel (acceptance §4): **per-kind** kernels (linear intensive, area-weighted extensive, angular
  circular), higher-order accuracy guarantees, and a provider **`exact`** capability (true off-grid points
  bypassing the store-grid floor) stay deferred
  ([concern #5](./concerns.md#5-read-time-homogenization-fidelity)).
- **Provider-real freshness** signal (vs the static `fetched_at + cadence` estimate) → `ideas.md`.
