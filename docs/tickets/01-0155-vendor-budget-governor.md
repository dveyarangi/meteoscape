# Vendor budget governor

- **Status:** Planned (own align precedes) — minted at the 2026-08-10 beeline align.
- **Depends on:** [vendor-call ledger](./01-0124-vendor-call-ledger.md) (the counter this gives
  authority to), [004 — Second-provider fallback](./done/01-0121-second-provider-fallback.md) (where a
  refused call sends the request instead)
- **Outcome:** A configured vendor budget stops the deployment from spending past it — the request
  falls through to the backstop rather than failing.

## Parent

The release-01 bee-line requires a metered TWC primary to stop spending at an operator-set budget
([delivery status](./README.md)). Durable context: [architecture § Source](../architecture.md#source).

## What to build

The **second slice of the ledger** — the same injected object, now consulted before a vendor call is
issued. Budget exhausted ⇒ the Source raises a `runtime-failure` **without an HTTP call**, and
[004](./done/01-0121-second-provider-fallback.md)'s fall-through routes the request to Open-Meteo for
free. The governor and the relief valve are one mechanism:

```
request ──► Source(TWC) ──► ledger: budget spent?
                                │
                        no ─────┴───── yes
                         │              │
                    vendor call    runtime-failure, no call
                                        │
                                   Arbiter falls through ──► Source(Open-Meteo) ──► answer
```

## Why this is not a Capability change

Tempting alternative: let quota exhaustion **narrow TWC's `Capability`** so selection simply skips
it — no fault, no fall-through needed. Rejected at the 2026-08-10 align, because it makes capability
lie. The architecture already refuses this exact move for retention — *"retention adds no
capability; the `Store` grid is a fidelity floor, not a boundary"* — since a `Capability` declares
**what a producer can serve**, not **whether it is allowed to right now**. Letting runtime budget
state move a declaration would also make the narrated reach at the MCP edge flicker with spend.

So: quota never touches capability. It produces a fault, and faults already have a route.

## Decisions this ticket's align owns

- **Budget expression** — calls per period, per vendor, per key? A budget is only meaningful against
  the period the vendor prices on, which is the ledger's period question inherited.
- **Behaviour at exhaustion when there is no backstop** — a single-provider deployment has nowhere
  to fall through to. Refuse (fail the request) or serve stale Holdings past `expiration`? The
  second is a genuine product option and a genuine contract change, since the MCP edge currently
  promises `exp` as a usable staleness bound ([edge/mcp.md](../edge/mcp.md) Invariants).
- **Headroom policy** — a hard stop at 100 % is rarely what an operator wants; reserving a slice for
  interactive traffic while batch work stops earlier is a policy, not a constant.
- **Whether the budget is observable to callers** at any surface, or purely operator-facing.

## Acceptance criteria

- [ ] With the budget exhausted, no HTTP call is issued to the vendor — pinned at the transport, not
      inferred from the ledger's own count.
- [ ] The request still succeeds, served by the backstop, with provenance naming the backstop.
- [ ] A deployment with no configured budget behaves exactly as before: the governor is inert, not
      defaulted to some number.
- [ ] Budget state never appears in any `Capability` or narrated reach — a guard pins that the
      declared reach is identical with the budget spent and unspent.
- [ ] Crossing the budget is visible in the ledger read-out; an operator can tell "we stopped" from
      "the vendor was down".

## Parent scope addressed

- Roadmap Phase 2 (operational substrate): bring-your-own-keys and policy without a hosted control
  plane.
