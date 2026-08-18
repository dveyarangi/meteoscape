# Second-provider fallback

**Legacy id:** 004

- **Status:** Done (landed 2026-08-18)
- **Plan:** [Second-provider fallback RFC](../../rfc/done/01-0121-second-provider-fallback.md) — one
  projection loop, results per projection, the catch around the child call only.
- **Depends on:** [002 — Core canonical parameters](./01-0030-core-5-parameters.md),
  [003c — Request shaping](./01-0110-request-shaping.md), and
  [011 — TWC provider](./01-0120-twc-provider.md) (v1's default primary — an ordering
  dependency plus the composite parity check's second live vendor; the deterministic proof itself
  needs no vendor; 011 in turn rides [m4](./01-0100-snapped-t-request-mode.md))
- **Outcome:** Wholesale priority fallback across two producers.

> **Load-bearing as of the 2026-08-10 align, and the primary inverted.** This ticket was written
> with Open-Meteo primary and TWC as the spare, where fall-through was resilience polish. TWC is now
> the primary, and it is **metered** — a 429 or an exhausted quota arrives as `runtime-failure`,
> which today fails the whole request. Fall-through is therefore what makes a metered primary safe
> to depend on, and it is the same mechanism that gives the
> [vendor budget governor](../02-0155-vendor-budget-governor.md) somewhere to send traffic when it
> refuses a call. **Open-Meteo is the backstop**: keyless, free, already parity-checked.
>
> One implementation note found while aligning: `Reconciler.select(parameter, candidates)` already
> returns a **`Sequence`**, and `Arbiter.project` already walks it
> ([arbiter.py](../../../src/meteoscape/nodes/arbiter.py)) — it breaks on the first candidate whose
> `serves` admits and never resumes after a *fault*. So this is "keep the walk alive across a
> fault", not a new selection mechanism. ~~Per the align, fall-through arrives as **policy** on
> `ArbiterPolicy` rather than as unconditional Arbiter behaviour.~~ *Re-decided 2026-08-18: no
> `ArbiterPolicy` change, no knob — fall-through **is** the `priority` reconciler's meaning
> ("select + fallback"); "off" is composing one producer; different fault behaviour is a different
> `Reconciler`.* Shape fact for the RFC: the fault surfaces at **projection** time, after winners
> are grouped — fall-through re-enters selection for the faulted producer's whole parameter group.
- **Scope narrowed 2026-08-02 (align):** the **provider implementation moved to
  [011](./01-0120-twc-provider.md)** — Probe, manifest, secret slot, parity check. This ticket
  keeps the **Arbiter behaviour** only. The two are tested
  differently and fail differently: 011 is a live parity question about one vendor's data; 004 is a
  deterministic question about selection and fall-through, provable against mocked transports with no
  network. Keeping them together would put a live-network dependency inside the fallback proof and let
  a vendor outage read as a fallback regression.

## Parent PRD

`docs/v1-requirements.md`

## What to build

Prove **select + wholesale fallback** over priority-ordered producers. The `Arbiter` carries a
`priority` order; per parameter it tries candidates in order and, on a `runtime-failure` from the
winner, **falls back wholesale** to the next candidate's whole window — never an A-then-B splice
along `valid_time`. Demonstrable via a forced producer failure. Which vendor sits at which priority
is configuration (v1's default composes TWC at 0, Open-Meteo at 1 — [config.py](../../../src/meteoscape/config.py)),
and the mechanism never branches on producer identity: identity flows through it only as data
(`ProducerKey` ordering lookups, provenance attribution).

> **2026-08-18 align — criteria de-vendored, two instruments.** Vendor names are configuration, so
> the criteria are stated over priority-ordered anonymous producers. Two instruments: the
> **deterministic suite** (mocked transports) proves the mechanism including fall-through; a
> **configurable composite parity check** (manual live run under `tests/parity`, provider order and
> keys as arguments) proves the configured serving order — order only, since a live vendor cannot
> be forced to fault.

Note what this requires of the algebra rather than of either provider: today a `RuntimeFailure` fails
the **whole request**, and this ticket changes only that — the Arbiter's walk survives a fault and
tries the next candidate. It needs **no** reconciler widening: the
[#28](../../concerns.md#28-reconciler-interface-selection-ordering-vs-per-cell-fold) widening serves
*combining* reconcilers, which must see values; fall-through never sees values. The
[MCP edge record](../../edge/mcp.md) carries this as Roadmap 1, and its *"`runtime-failure` is
whole-request"* invariant is the promise this ticket changes — a **compatible** change (a request that
used to fail now succeeds), to be restated in that record at landing.

See `docs/v1-requirements.md` (Providers, v1 invariants → wholesale-fallback rule) and
`docs/architecture.md` (Arbiter).

## Acceptance criteria

- [x] On a forced `runtime-failure` from the priority-0 producer, the `Arbiter` falls back to the
      priority-1 producer and serves the **whole** window for that parameter from it.
      *(~~"results come from the primary (TWC)"~~ — removed 2026-08-18, delivered by
      [011](./01-0120-twc-provider.md).)*
      *(~~"a 429 falls through like any other runtime-failure, pinned explicitly"~~ — folded
      2026-08-18: the transport makes every HTTP fault the same `RuntimeFailure`
      ([base.py](../../../src/meteoscape/nodes/providers/base.py)), so the pin could not fail; quota
      semantics live at the [ledger](../02-0124-vendor-call-ledger.md) and
      [governor](../02-0155-vendor-budget-governor.md).)*
- [x] Fallback is wholesale and single-origin — no cached-primary ∪ fallback splice along `valid_time`.
      *(Structural below the Arbiter too: a Holding carries no T in its key and is replaced whole,
      so a spliced `valid_time` is unrepresentable — [store.py](../../../src/meteoscape/nodes/store.py).)*
- [x] Per-parameter provenance on a fallback answer names the producer that **actually served**,
      with its own `expiration` — authored by the wrapper from that Probe's declared cadence.
- [x] Unit + mocked-transport integration tests cover healthy-path priority order and
      forced-failure fall-through, over anonymous producers.
      **No live network in the deterministic suite** — each vendor's own correctness is its
      parity check ([011](./01-0120-twc-provider.md)).
- [x] A **configurable composite parity check** exists under `tests/parity` (manual, opt-in live):
      it takes the provider order and the relevant keys as arguments, composes the profile
      accordingly, and verifies the answer's provenance names the configured priority-0 producer —
      reordering the arguments inverts the expectation. Serving order only; no forced-fault case.
- [x] The [MCP edge record](../../edge/mcp.md)'s whole-request `runtime-failure` invariant and Roadmap 1
      are updated at landing, and the change is named **compatible**.

## User stories addressed

- User story 6
