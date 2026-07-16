# 0009 · 2026-07-12 · Phase C — spine plan (align session)

Continues [session 0008](./0008-20260712-phase-b-value-types-plan.md) (Phase B landed). Grilled
Phase C of [issue 001](../tickets/done/001-walking-skeleton.md) — the real Open-Meteo leaf,
the composite behaviours, and the MCP edge — resolving every fork session 0002 left open. Along the
way the tool contract was reshaped (`forecast_hourly`), one contract change was weighed and declined
(per-parameter Selection domains), and concern #24 was filed. Deliverable: the decisions below + the
TDD cycle list.

## Decisions

- **The Phase C leaf declares `air_temperature` only.** Capability must never advertise what the
  running server will not attempt — a 5-parameter `OfferingSpec` over a 1-channel normalizer breaks
  that from day one. Session 0002's "5 canonical parameters" survives as the *full-leaf* target that
  issue 002 completes additively (`OfferingSpec.parameters` is data).
- **One `StoreSpec` for every store position that needs a configured guess** — replaces
  `RootStoreSpec` and kills `OfferingSpec.default_lattice`. Shape:
  `{ spatial_step: float, retention_interval: timedelta }`. Countable Providers still supply
  `provider.domain` (provider-exact) and need no guess; non-Countable Sources (Open-Meteo
  `best_match`) and the profile root both carry a `StoreSpec`. `StoreFactory` builds the declared
  grid from knobs at 006; Phase C StubStore still ignores them. (Corrects the Jul 11 asymmetry that
  treated the configured guess as root-only — ADR-0002 always allowed a guess for point vendors.)
- **Source `StoreSpec` authorship = catalogue default + optional operator override.**
  `OfferingSpec.store: StoreSpec | None` (required when the built Provider is not Countable);
  `OfferingDef.store: StoreSpec | None` — **whole-spec replace** when set (no field-wise merge);
  else catalogue. Binder: Countable → `store is None` on the record (ignore knobs);
  non-Countable → `OfferingDef.store ?? OfferingSpec.store`, else `CompositionError`. Profile root
  stays `ProfileConfig` / Settings as today. Phase C: OM catalogue ships fine
  `spatial_step=0.0001°`; no override needed.
- **`RegisteredSource = {provider, priority, store: StoreSpec | None}`** — drops
  `source_lattice: EnumerableDomain`. Invariant: Countable ⇒ `store is None`; non-Countable ⇒
  `store` set. **`StoreFactory.create(grid: EnumerableDomain | StoreSpec | None)`** — one face;
  Weaver passes `provider.domain` or the Source `StoreSpec`; **profile root passes
  `profile.root_store` (`StoreSpec`), never `None`**. Phase C Stub ignores every arm but must still
  expose a **harmless dummy `domain`** (structural `Countable` — not a fidelity claim); 006 builds
  the real declared grid from knobs / installs a provider-exact domain.
- **Minimal scalar normalizer; `Channel` is minted at 002.** One 1:1 mapping
  (`temperature_2m` → `air_temperature`) needs no `Channel`/`VendorVar` table — same precedent as the
  kernel registry ("one kernel needs no registry"). The N:M vector case (wind → u/v) forces the
  Channel shape at 002 with a real test; session 0002's Channel design remains the target shape, and
  its open `decode` signature is designed there, not blind.
- **`Normalizer.normalize(raw, provenance) -> Coverage`** — drops `selection` from the 0002
  signature (request Domain is homogenization, not normalization). Provider authors `Provenance`
  (cadence + clock) and passes it in; Normalizer builds native-geometry `CoverageRecord` +
  `Uniform(provenance)`. `DistilledData` stays dropped.
- **Request `Selection` shape** (the wire-shape of every v1 request): T = `floor(clock.now(), 1h)`
  UTC, step 1 h, count = `default_horizon/1h` (168), `cellular=True` (the committed hourly-bounds
  encoding — 002's precipitation reads them, intensive parameters ignore them); X/Y = count-1 axes at
  the requested lon/lat (nominal step); **Z = the exact 2 m point cell** — a single-parameter request
  carries its exact height; the provider Capability declares the fat near-surface *reach*
  (`[0, 10] m`), which contains it. No guessing, no fat request cell while requests are single-height.
- **`Selection` stays one-domain — per-parameter domains weighed and declined.** They reopen the
  Coverage co-domain invariant (`capability`/`ranges`/`provenance` positional to one
  `EnumerableDomain`), `EnumerableCapability`, the fresh Phase B sampling engine, the Arbiter's
  single target lattice, 006's quantize, the serializer's shared `valid_time`, and ADR-0001/0002.
  The need (serve `temperature_2m` exactly) is met by exact-Z Selections + the edge alias table
  (003); the mixed-height bundle fork (fat shared Z cell vs per-Z-group edge Selections) is
  **[concern #24](../concerns.md#24-parameter-height-carriage-fat-shared-z-cell-vs-per-z-group-requests)**,
  decided at 002/003 with the fetch-cost trade in view.
- **The tool is `forecast_hourly`; optional `start`/`end` stay in the contract.** Shape-named: a
  daily/aggregated product is different statistics — a **sibling tool** with its own narratable
  description, never a `step` knob (the substance of concern #15); also the natural REST path when
  HTTP lands. The window stays because the consumer is an LLM agent and response tokens are the
  scarce resource — "will it rain Saturday?" against a windowless tool pays the full 168-hour
  timeline forever. Phase C implements only lat/lon + default horizon; supplied `start`/`end` →
  `bad-request` ("not yet supported") until 003.
- **HTTP mapping**: `GET /v1/forecast`, `hourly=temperature_2m`, exact window via
  `start_hour`/`end_hour` = ISO-UTC of the Selection T **first tick** and **last tick**
  (`extent.lower` / `extent.upper` — tick span, **not** the last cell's upper bound). Open-Meteo
  treats both as inclusive; response length must equal T `count` (168). The default
  `forecast_days` window starts at 00:00 *today* — it would not contain the Selection; 003's free
  window needs exact mapping anyway. `timezone=UTC` explicit. No unit params — Open-Meteo's
  default is canonical `degC`; the normalizer **verifies** `hourly_units` and raises
  `RuntimeFailure` on a mismatch (verification, not conversion).
- **Transport policy**: `HttpxTransport(base_url, …)` owns the vendor host; `FetchRequest` is
  relative `{path, params, headers}` (session 0002). `Transport.fetch` returns **decoded JSON**;
  status / timeout / non-JSON raise `RuntimeFailure` inside the transport (shared taxonomy; leaves
  never see raw responses). Connect-level `retries=2` (httpx built-in; the dominant transient class,
  and Phase C has no second candidate to fall back to). **No response-level retry loop** — 5xx/429
  retry is real policy whose payoff shrinks once 004 makes the right second attempt a *different*
  candidate; reopened only on observed evidence. **Every transport fault → `RuntimeFailure`** —
  the other two taxa are semantically unreachable from inside the fetch (input edge-validated,
  admission already passed; a vendor 400 means *our* request builder is broken). 10 s total timeout
  as a constructor default.
- **`Reservoir.project` = pure delegate.** No no-op `assimilate` write-through fossil: it tests
  nothing and doesn't shrink 006's diff (the retentive flow replaces the whole body — the real read
  path returns from the *store*, homogenized). `StubStore.domain` returns a **harmless dummy
  `RegularDomain`** (four count-1 axes at nominal anchors — structural `Countable` only, not a
  fidelity claim) so `Reservoir.domain` never raises; replaced at 006.
- **`Selection.with_params` is minted** (ADR-0004's illustrative name, finally real): same `domain`,
  new parameter set; extras not ⊆ self → `ValueError`. The Arbiter's one projection is
  `candidate.project(selection.with_params(admitted))`; Calculator (002b) reuses it.
- **`Arbiter.project` = real admission, single selection, guarded assembly, producible subset.**
  Per requested parameter: first ranked candidate whose `capability.serves` admits
  (beyond-footprint is a miss for that parameter — no HTTP); **none → omit the parameter** (do not
  raise yet). After the fold: empty admitted set → raise `CapabilityMismatch` (whole-request only
  when nothing is produced); otherwise all surviving parameters must resolve to **one** candidate →
  **one projection** via `with_params(admitted)`, its Coverage returned as-is. Different winning
  candidates → `NotImplementedError` guard (per-parameter assembly lands at 005, loud not silently
  wrong). `RuntimeFailure` propagates (fallback lands at 004 with a test). MCP maps
  `CapabilityMismatch` → `capability-mismatch:` only on that whole-request raise; a partial Coverage
  is a normal success.
- **`Gateway.resolve` → `Coverage`** — served profiles always materialize; Gateway runtime-checks the
  root's `project` result is a Coverage (mismatch → non-taxonomy error). MCP serializes only.
- **MCP edge**: `build_mcp_app(gateway, clock, default_horizon)` (units ride the Coverage's
  descriptor block). **Default `parameters` = keys of the woven root `capability.parameters`**
  ("everything this server can attempt" — Phase C: `{air_temperature}`; grows with 002). Validation:
  lat/lon ranges → `bad-request`; unknown parameter names → `bad-request`; known-but-unserved
  parameters flow to the Arbiter's admission (omit / whole-request `capability-mismatch` if nothing
  remains — no special-casing). Optional `start`/`end` stay on the signature but supplied values →
  `bad-request` ("not yet supported") until 003. Response: one `valid_time` array (ISO-8601 UTC `Z`),
  per-parameter blocks `{unit, values, provenance: {source, exp}}` — **uniform per-parameter
  provenance** (hoisting declined: clients shouldn't branch on response shape), compact two-field
  block (`issue_time` is diagnostic → the future `provenance=full` knob, `ideas.md`); nodata →
  `null`. Taxonomy → FastMCP `ToolError` with stable prefixes (`bad-request:` /
  `capability-mismatch:` / `runtime-failure:`); non-taxonomy exceptions propagate (a bug looks like
  a bug). Tool description narrates the startup-resolved envelope: served parameters read
  dynamically off the woven root capability + static hourly/horizon text.
- **Display-preference knobs → `ideas.md`**: caller `timezone` rendering, caller unit-system
  selection, provenance detail flag — all pure edge serialization; the engine stays aware-UTC and
  canonical-unit end-to-end.
- **Registration & config**: the whole vendor leaf in `nodes/providers/open_meteo.py` exporting
  `MANIFEST`; `server.py` registers `{"open-meteo": MANIFEST}`. Conservative cadence
  `{Δ=1h, L=1h, max_lead=16d}` as vendor-module constants (concern #18 owns refinement; not
  operator-tunable before it means something). `open_meteo_enabled` default flips to `True`. No
  transport-injection seam in the manifest: `build` constructs the real `HttpxTransport`; the e2e
  mocks at the httpx layer via respx ("mock the transport, not the provider" — respx *is* the
  transport mock); provider unit tests inject a fake `Transport` via the constructor.

## Implementation plan (TDD — one test → one implementation, vertical)

`tests/nodes/providers/test_open_meteo.py`:

1. Request mapping *(leaf tracer bullet)* — capturing fake `Transport`: Selection → `FetchRequest`
   with lat/lon from X/Y, `hourly=temperature_2m`, `start_hour`/`end_hour` = first/last T ticks
   (extent endpoints; `len(hourly.time) == T.count`), `timezone=UTC`.
2. Normalizer happy path — canned Open-Meteo JSON → `CoverageRecord`: T axis rebuilt from
   `hourly.time` (hourly step verified), X/Y at the native point coords the response reports
   (**response Domain = native leaf Domain**, not the request's — off-grid identity waits until
   007; e2e must not assert request lat/lon equality on the serialized point),
   values `degC`-verified via `hourly_units`.
3. Unit mismatch → `RuntimeFailure`.
4. Malformed payload (missing block, ragged arrays) → `RuntimeFailure`.
5. Provenance authorship — `StoppedClock`: `issue_time = A`, `expiration = A + Δ + L`,
   `source = open-meteo/best_match`, `Uniform` plane.
6. `HttpxTransport` over respx — 200 → decoded JSON; 5xx / timeout / non-JSON → `RuntimeFailure`.

`tests/manifold/test_selection.py` (or a thin cycle on `core.py`):

7a. `Selection.with_params` — ⊆ rewrite keeps domain; extras → `ValueError`.

`tests/nodes/test_arbiter.py` (extend):

7. Admission — beyond-footprint on the only requested param → `CapabilityMismatch` without
   projecting (recording fake); in-footprint → projected once with `with_params(admitted)`;
   one served + one unserved → Coverage with the served subset (no raise); parameters resolving
   to different candidates → the `NotImplementedError` guard.

`tests/api/test_mcp_app.py`:

8. Selection building — floor(now) anchor, 168 ticks, Z = 2 m cell; out-of-range lat/lon →
   `bad-request`; unknown parameter name → `bad-request`; supplied `start`/`end` → `bad-request`.
9. Serialization — the schema above; `{source, exp}` provenance; nodata → `null`.
10. Error mapping — taxonomy → `ToolError` stable prefixes.
11. Envelope narration — description lists served parameters from the woven capability.

Wiring & regression:

12. `StoreSpec` — rename `RootStoreSpec` → `StoreSpec`; drop `OfferingSpec.default_lattice` /
    `source_lattice`; `RegisteredSource.store: StoreSpec | None`; `StoreFactory.create(
    EnumerableDomain | StoreSpec | None)`; Weaver root `create(profile.root_store)`; StubStore
    returns a harmless dummy `domain`; composition/weaver tests updated.
13. Config — `open_meteo_enabled=True` default; `test_config` / `test_server` updated.
14. **The e2e** *(closes issue 001)* — respx-mocked transport, FastMCP in-memory client:
    `forecast_hourly(52.52, 13.41)` → full JSON; plus an assertion that a second identical call
    **re-fetches** — documenting no-retention so 006 flips one assertion, not a story.

`Reservoir` / `Gateway` / `Weaver` pass-throughs get no isolation tests — the e2e covers them
(issue 001's testing rule). Refactor pass after green, never while red.

## Modules touched

`nodes/providers/base.py` (`Transport` / `FetchRequest` / `HttpxTransport`) ·
`nodes/providers/open_meteo.py` (new: provider, normalizer, `MANIFEST`, cadence constants) ·
`nodes/providers/normalization.py` (signature: `normalize(raw, provenance) -> Coverage`; no
`selection`) · `nodes/reservoir.py` / `nodes/arbiter.py` (project) · `nodes/composition.py` /
`nodes/store.py` / `nodes/weaver.py` (`StoreSpec` binding + stub dummy domain) ·
`api/mcp_app.py` (tool, Selection, serializer, errors, narration) ·
`server.py` (catalogue registration, Gateway → app wiring) · `config.py`
(`StoreSpec`, `open_meteo_enabled=True`) · docs: `v1-requirements.md` / `README.md` / roadmap /
issues (`forecast_hourly` rename — landed with this plan) · `concerns.md` (#24) · `ideas.md`
(timezone / units / provenance-detail) · issue 001 / session 0002 (Channel deferred to 002;
scalar Phase C path).

## Out of scope

The remaining 4 canonical parameters + `Channel`/`VendorVar` + extensive `serves` edge (002) ·
Calculator weave and derived wind (002b) · `parameters`/`start`/`end` implementation + alias table
(003) · fallback (004) · per-parameter assembly + `PerParameter` response provenance (005) ·
retentive `Store` / quantize / lattice re-strictness (006) · off-grid homogenization + kernel
registry (007) · response-level retry / quotas (Gateway, 008) · concern #24's mixed-height bundle
fork (002/003).

## Continuation

- Build Phase C per the cycle list; the e2e closes
  [issue 001](../tickets/done/001-walking-skeleton.md).
- Concern #24 decision point arrives at [issue 002](../tickets/done/002-core-5-parameters.md) /
  [issue 003](../tickets/003-request-shaping.md).
