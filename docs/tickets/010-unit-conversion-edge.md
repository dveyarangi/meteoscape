## Parent PRD

`docs/v1-requirements.md`

## What to build

The **unit conversion utility at the vendor edge** — deliberately absent until a vendor forces it.

**v1 position (sessions 0009/0012): verify-only, convert-never.** Every `Tap`'s `VendorVar.unit`
is checked against the vendor's reported units (`hourly_units` for Open-Meteo); a mismatch is
`runtime-failure` (our request builder or the vendor broke contract — never papered over by a silent
conversion). Quantity **transforms** (vendor speed/direction → canonical `wind_u`/`wind_v`) are
`decode`'s job and are not unit conversion.

**Trigger:** the first vendor unit that cannot be requested or served canonically. TWC (issue 004)
is the likely forcing case (metric tier serves km/h wind). Build then, against the real case:

- The shared **conversion utilities** (the architecture's "conversion library + Normalizer protocol"
  kernel item) — factor/offset conversions keyed by unit pair.
- `Tap`-level native→canonical conversion: `VendorVar.unit` declares the native unit, the tap
  converts to the parameter's `canonical_unit` on ingest (write-time, in the data — per the
  normalization rule of thumb, `architecture.md` §Normalization vs. homogenization).
- Record **conversion-edge qualities** (lossless vs degrading) with the parameter conventions
  ([concern #10](../concerns.md#10-parameter-conventions)).

## Acceptance criteria

- [ ] A vendor unit differing from canonical is converted on ingest at the `Tap`, driven by
      `VendorVar.unit` — no conversion logic in `decode` or downstream of the Normalizer.
- [ ] Verification remains: a vendor unit matching neither the declared native unit nor a
      convertible one is `runtime-failure`, not a guess.
- [ ] Conversions are exact factor/offset (lossless); anything else is recorded per concern #10.
- [ ] Unit tests cover convert-on-ingest, verify-mismatch, and the no-op canonical path.

## Blocked by

- Blocked by `docs/tickets/002-core-5-parameters.md` (the `Tap` / `VendorVar` seam)
- Expected to be forced by `docs/tickets/004-second-provider-fallback.md`

## User stories addressed

- User story 4
