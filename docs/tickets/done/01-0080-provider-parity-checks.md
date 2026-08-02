# m3 — Provider parity checks

- **Status:** Done (maintenance)
- **Plan:** [RFC 0007](../../rfc/done/0007-20260725-m3-provider-parity-checks.md) (aligned 2026-07-25)
- **Depends on:** [002 — Core canonical parameters](./01-0030-core-5-parameters.md) and
  [002b — Derived wind](./01-0030.0010-derived-wind-calculator.md), both done.
- **Blocks:** Acceptance of any new Provider, beginning with
  [004 — Second-provider fallback](../01-0150-second-provider-fallback.md).
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

[Provider authoring guide](../../edge/provider.md) defines the durable contribution expectation and
the meaning of **Provider parity check**. This ticket supplies the executable home and first working
case; it must not duplicate that guidance.

## What to build

- ~~Establish one discoverable home and one documented opt-in command for live Provider parity
  checks. Keep them outside the default deterministic test run.~~ **Resolved (align 2026-07-25,
  [RFC 0007](../../rfc/done/0007-20260725-m3-provider-parity-checks.md)):** the existing suite moves whole
  to `tests/deterministic/` and parity checks live in `tests/parity/`;
  `testpaths = ["tests/deterministic"]` makes the default `uv run pytest` structurally unable to
  collect a live test. The opt-in command is `uv run pytest tests/parity`
  (per-provider: `-k <provider-id>`).
- Add the Open-Meteo parity check as the reference implementation:
  - compose the real root with Open-Meteo as its only Provider and the built-in wind Calculator;
  - ~~obtain the same bounded forecast independently from Open-Meteo;~~ **Resolved (align
    2026-07-25, [RFC 0007](../../rfc/done/0007-20260725-m3-provider-parity-checks.md)):** a minimal direct
    JSON fetch, not the official FlatBuffers client — for Open-Meteo the public JSON API is itself
    the canonical documented interface, the reader stays auditable, and failure evidence is
    human-readable; the suitability justification is recorded so the guide's official-client
    preference is deviated from consciously. Bounded request: Berlin `52.52, 13.41`, all six
    product parameters, the surface's default window (currently the fixed 168 h horizon; alignment
    is by declared valid-times, so the check is insensitive to 003c changing the default), UTC;
  - compare every product parameter exposed by that profile;
  - treat the direct response as a provider reference, not meteorological truth;
  - ~~use independent canonical conversion, circular wind-direction comparison, nodata alignment,
    and explicit per-parameter tolerances.~~ **Resolved (align 2026-07-25,
    [RFC 0007](../../rfc/done/0007-20260725-m3-provider-parity-checks.md)):** exact equality for the four
    pass-through parameters; `absolute(1e-6 m/s)` for `wind_speed`; `circular(1e-6°)` for
    `wind_direction`; nodata positions match exactly in both directions, with one carve-out — at
    ticks where the reference speed is below the calm floor, the payload's `wind_direction` is
    expected to be `null` (same constant as the Calculator, below). Alignment is by declared ISO
    valid-times (Meteoscape first, reference bounded to the payload's window); a Meteoscape tick
    missing from the reference is a failure. On mismatch the whole comparison retries **once**,
    composing a **fresh root per attempt** — required once 006 lands retention, or the retry would
    serve the cached first run and could never clear a vendor model-run boundary.
- The wind Calculator gains a **calm floor**: below `CALM_SPEED_FLOOR` (a named epsilon constant in
  `calculators/wind.py`, guarding the degenerate `atan2(0,0)` — not a meteorological calm policy),
  `wind_direction` is nodata (`present=False`) instead of an arbitrary reconstructed angle. The
  parity spec imports the same constant. Deterministic coverage exercises the floor; the
  `wind_direction` note in [parameters.md](../../parameters.md) records the undefined-below-floor rule.
- ~~Make the harness reusable without imposing one provider's response model, official client, or
  authentication scheme on another Provider.~~ **Resolved (align 2026-07-25,
  [RFC 0007](../../rfc/done/0007-20260725-m3-provider-parity-checks.md)):** the harness couples through a
  neutral data shape, not a lifecycle — a shared comparison engine (`tests/parity/comparison.py`)
  takes the **MCP payload** (in-process `fastmcp` client over the composed single-Provider root —
  the only neutral, stable data shape Meteoscape emits) and a **`ReferenceTimeline`** produced by a
  per-provider reader living in `tests/parity/readers/` that imports no `meteoscape` code, compared
  under a per-parameter spec (`exact` / `absolute(tol)` / `circular(tol)`). Raw vendor responses are
  retained as failure evidence, never the comparison target.
- ~~Emit reproducible failure evidence without leaking credentials.~~ **Resolved (align 2026-07-25,
  [RFC 0007](../../rfc/done/0007-20260725-m3-provider-parity-checks.md)):** two channels split by audience —
  the assertion message carries the judging summary (provider, request, first-N mismatch table,
  counts); a failure-time evidence bundle on disk (gitignored `tests/parity/_artifacts/`) carries
  reproduction (both requests, both raw responses, full diff), because parity evidence is
  perishable — the vendor's forecast rolls over within hours. Redaction is mechanical in the shared
  writer: it scrubs the composed root's secret values from everything it writes (no-op for keyless
  Open-Meteo; the rule predates the first secret-bearing Provider).
- Document how Provider authors run their check locally when changing an integration.

## Acceptance criteria

- [x] A documented opt-in command runs the live parity suite without changing the default
      `uv run pytest` behavior.
- [x] Open-Meteo parity composes the real single-Provider root and compares all exposed product
      parameters with an independent live reference over the same bounded request.
- [x] The reference path does not import or call the Open-Meteo Provider, `Normalizer`, taps, or
      Meteoscape conversion helpers — structurally: the reader module imports no `meteoscape` code
      at all (only the test file, which composes the root and builds the spec, may), enforced by a
      deterministic guard test that imports each reader and asserts no `meteoscape*` module loads.
- [x] Equality, tolerance, circular-value, coordinate/time alignment, and nodata rules are explicit
      in the check and its diagnostics.
- [x] A parity failure reports provider, request, parameter, valid time, expected/reference value,
      Meteoscape value, and difference; secret values are redacted.
- [x] The wind Calculator yields nodata for `wind_direction` below `CALM_SPEED_FLOOR`; the parity
      spec adopts the same constant; deterministic tests exercise the floor.
- [x] The Provider authoring guide links to the executable command and Open-Meteo example.
- [x] Ticket 004 requires the TWC Provider to ship its own parity check before acceptance.
- [x] Ruff, pyright, and the deterministic pytest suite remain green without network access.

## Docs to sync

Lands with the code, not after it:

- [module-layout.md](../../module-layout.md) — the `tests/` comment: deterministic suite moves to
  `tests/deterministic/`; live parity lives in `tests/parity/`.
- [edge/provider.md](../../edge/provider.md) — the durable parity-authoring rules (payload
  boundary, import-level independence, engine-constant adoption, fresh-root retry, evidence
  perishability) landed with the 2026-07-25 align; at landing, the "until m3 supplies the
  executable harness" sentence flips to a link to the opt-in command and the Open-Meteo example,
  plus harness usage examples (also an acceptance criterion).
- [parameters.md](../../parameters.md) — `wind_direction` gains the undefined-below-calm-floor nodata
  note.
- [cicd.md](../../cicd.md) — one line under the CI pipeline: live parity (`uv run pytest tests/parity`)
  is deliberately outside CI; `testpaths` keeps the default run deterministic.
- [Delivery status](../README.md) — the m3 entry under "Decisions still owned by tickets" and this
  ticket's row, at landing.

## Follow-on automation

If the retry-once policy still produces false alerts at model-run boundaries, improve the
mechanism (e.g. run pinning or reference metadata comparison) — deliberately not built until the
simple policy demonstrably fails.

Scheduled execution, manual provider selection, changed-file routing, and optional
`provider/<provider-id>/**` branch hints are useful follow-ons. They are deliberately not prerequisites
for landing the harness and first parity check. Branch naming must not become the only way an affected
Provider is selected.

## Out of scope

- Comparing forecasts with observations or scoring meteorological accuracy.
- Cross-provider consensus or skill ranking.
- Making live network calls part of the default deterministic PR gate.
- Settling one credential policy for all future Providers.
