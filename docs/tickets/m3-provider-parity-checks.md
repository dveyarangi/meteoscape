# m3 — Provider parity checks

- **Status:** Ready (maintenance)
- **Depends on:** [002 — Core canonical parameters](./done/002-core-5-parameters.md) and
  [002b — Derived wind](./done/002b-derived-wind-calculator.md), both done.
- **Blocks:** Acceptance of any new Provider, beginning with
  [004 — Second-provider fallback](./004-second-provider-fallback.md).
- **Outcome:** Every shipped Provider has an opt-in live parity check that compares a
  single-Provider Meteoscape root with an independent response from the same external producer.

## Why

The deterministic Provider suite mocks HTTP at the `Transport`, and the current root-level
end-to-end test also uses a canned Open-Meteo response. Those tests correctly prove Meteoscape
behavior under controlled inputs, but they cannot detect drift between those inputs and the live
producer's request, schema, units, or values.

A manual Open-Meteo comparison on 2026-07-24 exercised the missing seam: the real stdio MCP root and
an independent direct Open-Meteo request returned matching values for all 168 hourly ticks across
the six exposed product parameters. Four pass-through parameters matched exactly; derived wind
matched to floating-point reconstruction precision. The useful result was not the particular
numbers—it was proving that a Provider-level independent oracle can validate the whole composed
path.

This work is maintenance, not a new product capability. It keeps Provider integrations honest and
therefore must land before the second Provider is accepted, but it need not delay unrelated request
shaping, storage, or homogenization work.

## Owning guidance

[Provider authoring guide](../provider-authoring.md) defines the durable contribution expectation and
the meaning of **Provider parity check**. This ticket supplies the executable home and first working
case; it must not duplicate that guidance.

## What to build

- Establish one discoverable home and one documented opt-in command for live Provider parity checks.
  Keep them outside the default deterministic test run.
- Add the Open-Meteo parity check as the reference implementation:
  - compose the real root with Open-Meteo as its only Provider and the built-in wind Calculator;
  - obtain the same bounded forecast independently from Open-Meteo;
  - compare every product parameter exposed by that profile;
  - treat the direct response as a provider reference, not meteorological truth;
  - use independent canonical conversion, circular wind-direction comparison, nodata alignment, and
    explicit per-parameter tolerances.
- Make the harness reusable without imposing one provider's response model, official client, or
  authentication scheme on another Provider.
- Emit reproducible failure evidence without leaking credentials.
- Document how Provider authors run their check locally when changing an integration.

## Acceptance criteria

- [ ] A documented opt-in command runs the live parity suite without changing the default
      `uv run pytest` behavior.
- [ ] Open-Meteo parity composes the real single-Provider root and compares all exposed product
      parameters with an independent live reference over the same bounded request.
- [ ] The reference path does not import or call the Open-Meteo Provider, `Normalizer`, taps, or
      Meteoscape conversion helpers.
- [ ] Equality, tolerance, circular-value, coordinate/time alignment, and nodata rules are explicit
      in the check and its diagnostics.
- [ ] A parity failure reports provider, request, parameter, valid time, expected/reference value,
      Meteoscape value, and difference; secret values are redacted.
- [ ] The Provider authoring guide links to the executable command and Open-Meteo example.
- [ ] Ticket 004 requires the TWC Provider to ship its own parity check before acceptance.
- [ ] Ruff, pyright, and the deterministic pytest suite remain green without network access.

## Follow-on automation

Scheduled execution, manual provider selection, changed-file routing, and optional
`provider/<provider-id>/**` branch hints are useful follow-ons. They are deliberately not prerequisites
for landing the harness and first parity check. Branch naming must not become the only way an affected
Provider is selected.

## Out of scope

- Comparing forecasts with observations or scoring meteorological accuracy.
- Cross-provider consensus or skill ranking.
- Making live network calls part of the default deterministic PR gate.
- Settling one credential policy for all future Providers.
