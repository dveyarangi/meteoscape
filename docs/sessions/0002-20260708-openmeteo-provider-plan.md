# 0002 · 2026-07-08 · Open-Meteo provider — leaf shape & align

Planning the first concrete Provider leaf (isolated, fully tested). Contract-level outcomes landed in
their canonical homes (below); this records the leaf design and the still-open forks.

## Decisions — contract (recorded in place)

- **`SourceKey`** — structured producer identity `(provider, dataset)`, replacing a bare source string;
  shared by config (`SourceDef`) and data (atomic `Origin`), rendered as the Registry / `arbiter_priority`
  token. **Built** in `manifold/provenance.py` (`AtomicOrigin.source` now a `SourceKey`).
  → [glossary](../glossary.md), [ADR-0003](../adr/0003-provenance-and-origin.md).
- **`SourceDef`** — config recipe (`SourceKey` + `{impl, secret_ref, priority}`); `dataset`/mode fixed at
  construction, so datasets are distinct producer instances. → [glossary](../glossary.md).
- **Candidate identity = `SourceKey`** — dataset/model priority can discriminate *within* a provider;
  realized as separate instances, `project` unchanged (granularity **settled** into
  [ADR-0004](../adr/0004-producer-resolution-and-capability.md); only the geometric offering half stays
  open in [#20](../concerns.md#20-provider-multi-resolution-offerings-offering-aware-selection)).
- **Multi-resolution offerings — realization X (instances)** — each native resolution / server-side
  interpolation endpoint is a separate `SourceKey`-identified instance, so v1 capability shapes stay
  final and every future piece is additive: axis native `step`, a graded `Domain.match()`, offering-keyed
  Store identity. → [concern #20](../concerns.md#20-provider-multi-resolution-offerings-offering-aware-selection),
  ADR-0002 / ADR-0004 seams.

## Decisions — Open-Meteo leaf shape

- **Three collaborators**: `OpenMeteoProvider` (orchestrator: `Selection` → request → normalize →
  provenance) · `nodes/providers/base.py` (the fetch seam — `Transport` protocol, `FetchRequest`
  vendor-neutral GET `{path, params, headers}`, `HttpxTransport`) · `Normalizer` (raw → canonical).
- **Provenance authorship**: the **Provider** authors the full `Provenance` (cadence + clock) and
  passes it into `Normalizer.normalize(raw, provenance) -> Coverage` (session 0009 dropped
  `selection` — native geometry from the response, not the request). The intermediate
  `DistilledData` / `NormalizedFetch` type is **dropped** — the normalizer returns a `Coverage`
  directly and installs `Uniform(provenance)`.
- **Vendor mapping via `Channel`**: `Channel {produces: ParameterId, block: OpenMeteoBlock,
  vendor_vars: VendorVar[], decode}`; `VendorVar {name, block, native_unit?}`. Handles 1:1 scalar,
  unit conversion, and N:M vector transforms (wind → u/v). Canonical units requested from the API where
  possible; the Normalizer coerces the rest. **Phase C (session 0009) ships a scalar 1:1 mapping
  only** (`temperature_2m` → `air_temperature`); the `Channel` table is minted when issue 002 adds
  the remaining parameters / wind.
- **`OpenMeteoBlock` enum** — `HOURLY` in v1; `DAILY` / `CURRENT` / `MINUTELY_15` reserved (block is
  explicit, not an implicit "hourly" assumption).
- **Point `Timeline` domain**: `RegularDomain` with degenerate count-1 spatial + Z axes and a
  `RegularAxis` on `valid_time` (D1); returns the provider's **native point** coordinates.
- **Provider construction**: `dataset` fixed at build via `SourceKey` (Open-Meteo defaults to
  `best_match`); `Clock` injected at build ([session 0001](./0001-20260708-clock-cadence-footprint.md)).
- **Capability**: 5 canonical parameters, global XY `ContinuousAxis`, a **fat-tick** Z cell
  (`[~0, 10] m above_ground`) so near-surface parameters share one Domain, `valid_time` `RollingAxis`
  from a conservative cadence `{Δ=1h, L=1h, max_lead=16d}`.

## Open questions / continuation

- **HTTP transport** — closed in [session 0009](./0009-20260712-phase-c-spine-plan.md)
  (`HttpxTransport` retries, taxonomy, decoded JSON).
- **Request mapping** — closed in session 0009 (`start_hour`/`end_hour` = T first/last ticks).
- **`decode` signature** — exact raw-block → `(values, present)` shape, and the vector-channel path
  (with `Channel`, issue 002).
- **Code — only `SourceKey` built** — `provenance.py` now carries `SourceKey` +
  `AtomicOrigin.source: SourceKey`; the rest of the leaf lands in Phase C / 002. `Domain.match()` /
  axis `step` remain deferred seams (#20).
