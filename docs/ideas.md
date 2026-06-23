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

## Freshness

- **Provider-real freshness metadata.** Where a provider exposes real freshness signals (next
  run / issue time, model-cycle expiry, HTTP `Expires` / `Cache-Control`), author each `ParameterData`'s
  `expiration` from that instead of the static `fetched_at + cadence` estimate; fall back to the
  configured cadence only when no real signal is available.
