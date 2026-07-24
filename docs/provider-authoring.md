# Provider authoring guide

This guide owns the contribution contract for adding or changing a Meteoscape **Provider**. The
architecture defines what a Provider is; this document states the implementation evidence expected
from its author.

## Contribution bundle

A Provider contribution includes:

- the Provider leaf, its `Normalizer`, `Capability`, provenance, cadence, and cohesive
  `ProviderManifest`;
- deterministic unit and integration tests that mock the HTTP `Transport`, not the Provider;
- a live **Provider parity check**; and
- any parameter definitions, conversions, secrets, configuration, and operator documentation needed
  to compose the Provider.

The deterministic suite proves Meteoscape behavior under controlled inputs. The parity check covers
the separate risk that the controlled inputs or request assumptions no longer match the external
producer.

## Provider parity check

A Provider parity check independently obtains the external producer's reference response and compares
it with the result of a Meteoscape profile composed with that single Provider. It is a provider
conformance check, not a forecast-accuracy or meteorological-truth test.

Each Provider author should:

1. Build the real Meteoscape root with only the Provider under test enabled, plus the Calculators
   needed to expose products derived solely from that Provider.
2. Send the same location, time window, and parameter request through that root and through an
   independent reference reader.
3. Prefer a provider-maintained official client when it exposes the required semantics. If none is
   available or suitable, use a minimal direct fetch and parse of the provider's public response.
4. Keep the reference reader independent: it must not call the Provider, its `Normalizer`, its taps,
   or Meteoscape conversion helpers.
5. Align values by their declared coordinates and valid times, convert the reference into canonical
   units independently, and compare every parameter the single-Provider profile exposes for the case.
6. Declare comparison semantics explicitly: exact equality for lossless pass-through values,
   justified numeric tolerances for conversions, circular distance for direction, and matching nodata
   positions.
7. On failure, retain enough evidence to reproduce the comparison: both requests, both responses,
   coordinates, valid-time axis, units, and per-parameter differences.

The check must use bounded requests and respect the provider's credentials, quotas, attribution, and
terms of use. Secret-bearing live checks must never expose credentials in fixtures, logs, or failure
artifacts.

## When to run it

Run the affected Provider's parity check when changing:

- that Provider, its reference reader, or its manifest;
- shared normalization or unit-conversion machinery it uses;
- a Calculator whose exposed output is included in the single-Provider comparison; or
- composition or surface code that changes the compared request or result.

Live parity is intentionally separate from the default deterministic `pytest` suite until
[m3 — Provider parity checks](./tickets/m3-provider-parity-checks.md) supplies the executable harness
and its automation policy. A new Provider is not complete without its parity check.
