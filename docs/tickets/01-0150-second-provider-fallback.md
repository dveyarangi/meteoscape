# Second-provider fallback

**Legacy id:** 004

- **Status:** Planned
- **Depends on:** [002 — Core canonical parameters](./done/01-0030-core-5-parameters.md),
  [003c — Request shaping](./01-0110-request-shaping.md), and
  [011 — Visual Crossing provider](./01-0120-visual-crossing-provider.md) (the second producer this ticket
  falls back *to*; 011 in turn rides [m4](./done/01-0100-snapped-t-request-mode.md))
- **Outcome:** Wholesale priority fallback across two producers.
- **Scope narrowed 2026-08-02 (align):** the **provider implementation moved to
  [011](./01-0120-visual-crossing-provider.md)** — Probe, manifest, secret slot, parity check, and the
  TWC → Visual Crossing sweep. This ticket keeps the **Arbiter behaviour** only. The two are tested
  differently and fail differently: 011 is a live parity question about one vendor's data; 004 is a
  deterministic question about selection and fall-through, provable against mocked transports with no
  network. Keeping them together would put a live-network dependency inside the fallback proof and let
  a vendor outage read as a fallback regression.

## Parent PRD

`docs/v1-requirements.md`

## What to build

Prove **select + wholesale fallback** over the two producers. The `Arbiter` carries a `priority` order
(Open-Meteo primary → Visual Crossing fallback); per parameter it tries candidates in order and, on a
`runtime-failure` from the primary, **falls back wholesale** to the next provider's whole window —
never an A-then-B splice along `valid_time`. Demonstrable via a forced provider failure.

Note what this requires of the algebra rather than of either provider: today a `RuntimeFailure` fails
the **whole request**, and per-candidate fall-through needs the reconciler widening recorded at
[#28](../concerns.md#28-reconciler-interface-selection-ordering-vs-per-cell-fold). The
[MCP edge record](../edge/mcp.md) carries this as Roadmap 4, and its *"`runtime-failure` is
whole-request"* invariant is the promise this ticket changes — a **compatible** change (a request that
used to fail now succeeds), to be restated in that record at landing.

See `docs/v1-requirements.md` (Providers, v1 invariants → wholesale-fallback rule) and
`docs/architecture.md` (Arbiter).

## Acceptance criteria

- [ ] With both providers enabled, results come from the primary (Open-Meteo).
- [ ] On a forced primary `runtime-failure`, the `Arbiter` falls back to Visual Crossing and serves the
      **whole** window for that parameter from the fallback.
- [ ] Fallback is wholesale and single-origin — no cached-primary ∪ fallback splice along `valid_time`.
- [ ] Per-parameter provenance on a fallback answer names the **fallback** source, with its own
      `expiration` — authored by the wrapper from that Probe's declared cadence.
- [ ] Unit + mocked-transport integration tests cover primary-serves and forced-failure-fallback.
      **No live network in this ticket** — the vendor's own correctness is
      [011](./01-0120-visual-crossing-provider.md)'s parity check.
- [ ] The [MCP edge record](../edge/mcp.md)'s whole-request `runtime-failure` invariant and Roadmap 4
      are updated at landing, and the change is named **compatible**.

## User stories addressed

- User story 6
