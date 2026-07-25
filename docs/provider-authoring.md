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
   independent reference reader, and compare at the root's **public protocol payload** (today: the
   MCP response) — never at engine internals. Parity judges the whole composed path, including the
   serialization edge where unit labels, nodata-as-`null`, and time formatting live.
3. Prefer a provider-maintained official client when it exposes the required semantics. If none is
   available or suitable, use a minimal direct fetch and parse of the provider's public response —
   and record the suitability justification in the check, so the deviation is conscious rather than
   habitual.
4. Keep the reference reader independent **structurally**: the reader module imports no Meteoscape
   code at all — not the Provider, its `Normalizer`, its taps, or conversion helpers, and nothing
   that transitively reaches them. The deterministic suite enforces this with a guard test; only
   the parity test file (which composes the root) may import Meteoscape.
5. Align values by their declared coordinates and valid times, convert the reference into canonical
   units independently, and compare every parameter the single-Provider profile exposes for the case.
6. Declare comparison semantics explicitly: exact equality for lossless pass-through values,
   justified numeric tolerances for conversions, circular distance for direction, and matching nodata
   positions. Where the engine deliberately withholds a value as nodata under a defined condition
   (for example `wind_direction` below the wind Calculator's calm floor), the check adopts the
   engine's own named constant for that condition — never a reinvented threshold that can drift.
7. Absorb the vendor's model-run boundary: the two fetches happen moments apart, so a run
   publishing between them produces a legitimate mismatch. Retry the whole comparison once,
   composing a **fresh root** for the attempt — a reused root may serve retained values from the
   first attempt and can never clear the boundary.
8. On failure, retain enough evidence to reproduce the comparison: both requests, both raw
   responses, coordinates, valid-time axis, units, and per-parameter differences. Parity evidence
   is perishable — the vendor forecast that produced a mismatch rolls over within hours — so
   retention happens at failure time, not on request. Raw vendor responses are failure evidence
   only, never the comparison target: comparing raws would validate the fetch while skipping the
   parse → normalize → convert → derive chain where drift actually bites.

The check must use bounded requests and respect the provider's credentials, quotas, attribution, and
terms of use. Secret-bearing live checks must never expose credentials in fixtures, logs, or failure
artifacts.

## Running and writing a parity check

The executable home is `tests/parity/` ([m3](./tickets/done/m3-provider-parity-checks.md),
[RFC 0007](./rfc/done/0007-20260725-m3-provider-parity-checks.md)). Live parity is structurally
outside the default deterministic suite — `testpaths` scopes `uv run pytest` to
`tests/deterministic/`, so live checks run only by explicit opt-in:

```sh
uv run pytest tests/parity                  # all live parity checks
uv run pytest tests/parity -k open_meteo    # one provider
```

A new Provider's check is three pieces, with Open-Meteo as the reference example:

- **Reference reader** — `tests/parity/readers/<provider>.py` (see `readers/open_meteo.py`):
  fetches and parses the vendor's public response, converts to canonical units independently, and
  returns a `parity.comparison.ReferenceTimeline` plus raw evidence. Imports no Meteoscape code —
  the deterministic guard test (`test_parity_reader_guard.py`) enforces this for every module in
  `readers/`, so a new reader is guarded with no registration.
- **Live test** — `tests/parity/test_<provider>.py` (see `test_open_meteo.py`): composes the real
  single-Provider root, drives it through the in-process MCP client, declares the per-parameter
  `ParitySpec`, retries once with a fresh root, and on final failure writes the evidence bundle
  and fails with the summary.
- **Deterministic coverage** — a `parse_reference` test over a canned vendor response in
  `tests/deterministic/` (see `test_parity_reader_open_meteo.py`); the shared engine itself is
  already covered by `test_parity_comparison.py`.

## When to run it

Run the affected Provider's parity check when changing:

- that Provider, its reference reader, or its manifest;
- shared normalization or unit-conversion machinery it uses;
- a Calculator whose exposed output is included in the single-Provider comparison; or
- composition or surface code that changes the compared request or result.

Scheduled and change-routed automation is deliberate follow-on work
([m3](./tickets/done/m3-provider-parity-checks.md)). A new Provider is not complete without its
parity check.
