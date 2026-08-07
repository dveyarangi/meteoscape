# Day-anchored availability window

- **Status:** Ready — fixes the [003c](./done/01-0110-request-shaping.md) landing's live 400; the
  parity probe is failing for ~23 hours of every day until this lands.
- **Plan:** [RFC 0010](../rfc/0010-20260806-day-anchored-availability-window.md).
- **Depends on:** [003c — Request shaping](./done/01-0110-request-shaping.md) (done — the default
  window that first reaches the vendor's edge).
- **Outcome:** The declared availability matches the vendor's real day-quantized window — the
  free-window default works at any hour of the day, explicit starts earlier today serve, and the
  narrated horizon floors to whole days ("out to 15 days"), never overstating.

## Parent PRD

`docs/v1-requirements.md`

## Why

The 003c landing's acceptance probe (`uv run pytest tests/parity`) exposed a **shape** error in
the Open-Meteo declaration, not a numbers error: the vendor's availability is **midnight-anchored**
(probed 2026-08-06: `end_hour = today00+16d−1h` → 200, `today00+16d` → 400; `start_hour` reaches
~92 days back through the same endpoint), while our `CadenceDef.valid_time` slides with the clock
(`[floor(now)−1h, +16d]`). The declared window pokes past the vendor's ceiling for every hour of
the day except 00:xx UTC, so the full-reach default fails live. Shrinking `max_lead` to 15 d would
hide the shape error by cutting a day of real offering; the fix is to **declare the true shape** —
the availability window and the run cadence are two different clocks, and the vocabulary must say
so. [#18](../concerns.md#18-clock-anchored-footprint-fidelity)'s "the numbers, not the shape"
clause is corrected by this ticket.

Probe-side or leaf-side clamping was considered and rejected: the crop already exists
(`RollingAxis.clip` inside `ground`) and crops to the *declared* window — a truthful declaration
makes it precise everywhere at once (admission, narration, the fetch, 006's retention), while a
vendor-face clamp would leave the declaration lying to all of them and defeat the parity guard
that just caught this ([edge/provider.md](../edge/provider.md): a mis-declared provider must fail
loudly).

## Acceptance criteria

Behavioral — the *how* (the `CadenceDef` widening, the Open-Meteo declaration values, the
narration formula) is [RFC 0010](../rfc/0010-20260806-day-anchored-availability-window.md)'s.

- [ ] The omitted-`end` default request succeeds against the live vendor **at any hour of the
      day**; the live parity run is that check and no longer depends on when it runs (the 003c
      acceptance probe, re-armed).
- [ ] Every window within the vendor's actual forward availability serves — including an explicit
      `start` earlier today; a window wholly outside it remains `capability-mismatch`.
- [ ] The declared forward reach **equals** the vendor's probed availability: nothing the
      capability promises can draw a vendor rejection, and nothing the vendor serves at the
      forward edge is left unpromised. (The archive-deep *lower* edge stays deliberately
      undeclared — [#18](../concerns.md#18-clock-anchored-footprint-fidelity)'s residue.)
- [ ] The narrated horizon never overstates what every request can get: whole days, floored
      ("out to 15 days"); providers with an exact-days reach (the test fakes) narrate unchanged.
- [ ] Provenance behavior is unchanged: per-parameter `source` and `exp` are byte-identical to
      before — availability re-anchoring must not touch run identity or freshness.
- [ ] [ADR-0003](../adr/0003-provenance-and-origin.md) records the two-clock split (run clock:
      identity + freshness; shelf clock: availability window);
      [#18](../concerns.md#18-clock-anchored-footprint-fidelity) is corrected with the probe
      record and its residue (archive-depth lower edge, real availability signal);
      the [retentive-store ticket](./01-0115-retentive-store-freshness.md) gains the
      **open-ended request member** align-agenda item (one-sided open bounds designed together
      with `ANY`; the MCP edge's omitted-`end` flip and floor-narration-as-sentence decided
      there).

## User stories addressed

- User story 2, user story 3 (the free-window contract, now honest against the live vendor).
