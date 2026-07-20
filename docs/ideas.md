# Ideas / backlog

Loosely-held future ideas captured during design. Not commitments; not scoped. Architecture
extension points live in [`architecture.md`](./architecture.md#extension-points); this file is for
product/feature ideas that haven't earned a decision yet.

## Inputs

- **Place-name location requests + geocoding.** Let callers ask by place name (e.g. "Berlin")
  instead of lat/lon; resolve to coordinates at the edge before building the Selection. Deferred
  from v1 (v1 takes lat/lon only) — geocoding is a separate capability from weather access and
  pulls in a geocoding dependency/provider.

## Outputs

- **Requested output `format`.** Let the caller choose the response serialization (e.g. compact
  JSON vs OGC CoverageJSON) via a `format` field on the request. v1 emits compact JSON only; the
  surface adapter would select the serializer at the edge.
- **Caller `timezone` rendering.** An optional request `timezone` renders `valid_time` in the
  caller's zone at serialization. Pure edge conversion — the engine's time model stays aware-UTC
  end-to-end (canonical Domain/provenance never carry a display zone); providers are always queried
  in UTC.
- **Caller unit-system selection.** An optional request `units` (e.g. `metric` / `imperial`, or
  per-parameter overrides) converts values from canonical units at serialization. Pure edge
  conversion — internal values stay in each parameter's canonical unit (`parameters.md`); pairs
  with the `timezone` idea above as the two display-preference knobs.
- **Provenance detail flag.** The default per-parameter provenance block is compact —
  `{source, exp}`, the two agent-actionable facts. An optional `provenance=full` request knob
  expands it with `issue_time`, `fetched_at`, and (for synthetic parameters, 002b) the lineage of
  their inputs' origins. Third member of the display-preference family (timezone, units,
  provenance detail); pure edge serialization.

## Freshness

- **Provider-real freshness metadata.** Where a provider exposes real freshness signals (next
  run / issue time, model-cycle expiry, HTTP `Expires` / `Cache-Control`), author each `ParameterData`'s
  `issue_time` / `expiration` from that instead of the static cadence-model `{Δ, L}` estimate
  ([ADR-0003](./adr/0003-provenance-and-origin.md)); fall back to the configured cadence only when
  no real signal is available.
