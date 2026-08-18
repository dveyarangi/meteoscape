# Second-provider fallback

**Legacy id:** 004

- **Status:** Planned
- **Depends on:** [002 — Core canonical parameters](./done/01-0030-core-5-parameters.md),
  [003c — Request shaping](./done/01-0110-request-shaping.md), and
  [011 — TWC provider](./done/01-0120-twc-provider.md) (which makes TWC the **primary**; this ticket
  builds the fall-through *away* from it; 011 in turn rides [m4](./done/01-0100-snapped-t-request-mode.md))
- **Outcome:** Wholesale priority fallback across two producers.

> **Load-bearing as of the 2026-08-10 align, and the primary inverted.** This ticket was written
> with Open-Meteo primary and TWC as the spare, where fall-through was resilience polish. TWC is now
> the primary, and it is **metered** — a 429 or an exhausted quota arrives as `runtime-failure`,
> which today fails the whole request. Fall-through is therefore what makes a metered primary safe
> to depend on, and it is the same mechanism that gives the
> [vendor budget governor](./02-0155-vendor-budget-governor.md) somewhere to send traffic when it
> refuses a call. **Open-Meteo is the backstop**: keyless, free, already parity-checked.
>
> One implementation note found while aligning: `Reconciler.select(parameter, candidates)` already
> returns a **`Sequence`**, and `Arbiter.project` already walks it
> ([arbiter.py](../../src/meteoscape/nodes/arbiter.py)) — it breaks on the first candidate whose
> `serves` admits and never resumes after a *fault*. So this is "keep the walk alive across a
> fault", not a new selection mechanism. Per the align, fall-through arrives as **policy** on
> `ArbiterPolicy` rather than as unconditional Arbiter behaviour; the current minimal policy shape
> is good enough to carry it.
- **Scope narrowed 2026-08-02 (align):** the **provider implementation moved to
  [011](./done/01-0120-twc-provider.md)** — Probe, manifest, secret slot, parity check. This ticket
  keeps the **Arbiter behaviour** only. The two are tested
  differently and fail differently: 011 is a live parity question about one vendor's data; 004 is a
  deterministic question about selection and fall-through, provable against mocked transports with no
  network. Keeping them together would put a live-network dependency inside the fallback proof and let
  a vendor outage read as a fallback regression.

## Parent PRD

`docs/v1-requirements.md`

## What to build

Prove **select + wholesale fallback** over the two producers. The `Arbiter` carries a `priority` order
(**TWC primary → Open-Meteo backstop**, inverted at the 2026-08-10 align); per parameter it tries
candidates in order and, on a
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

- [ ] With both providers enabled, results come from the primary (**TWC**).
- [ ] On a forced primary `runtime-failure`, the `Arbiter` falls back to **Open-Meteo** and serves
      the **whole** window for that parameter from the backstop.
- [ ] A quota-shaped failure (HTTP 429 / vendor quota-exhausted envelope) falls through like any
      other `runtime-failure` — pinned explicitly, because this is the failure the beeline's metered
      primary will actually produce.
- [ ] Fallback is wholesale and single-origin — no cached-primary ∪ fallback splice along `valid_time`.
- [ ] Per-parameter provenance on a fallback answer names the **fallback** source, with its own
      `expiration` — authored by the wrapper from that Probe's declared cadence.
- [ ] Unit + mocked-transport integration tests cover primary-serves and forced-failure-fallback.
      **No live network in this ticket** — the vendor's own correctness is
      [011](./done/01-0120-twc-provider.md)'s parity check.
- [ ] The [MCP edge record](../edge/mcp.md)'s whole-request `runtime-failure` invariant and Roadmap 4
      are updated at landing, and the change is named **compatible**.

## User stories addressed

- User story 6
