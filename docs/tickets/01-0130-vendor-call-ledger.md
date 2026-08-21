# Vendor-call ledger (meter slice)

- **Status:** Planned (own align precedes)
- **Depends on:** [011 — TWC provider](./done/01-0120-twc-provider.md) (the first metered vendor, and the
  reason this exists), [config and secrets](./done/01-0123-config-secrets-degrade.md)
  (the construction path a ledger is injected through),
  [supported Python embedding surface](./01-0125-supported-python-embedding.md) (the pilot lifecycle
  in which the metered primary becomes a real customer)
- **Blocks:** [vendor budget governor](./01-0155-vendor-budget-governor.md) — the same object, given
  the authority to refuse.
- **Outcome:** An operator can answer how many vendor calls a deployment spent, against which
  vendor, and over what period, with no effect on what any request returns.

## Parent

The release-01 bee-line makes a metered keyed provider observable before it becomes
budget-governed ([delivery status](./README.md)). TWC-as-primary is the private
[pilot deployment](../pilot-requirements.md)'s declaration at the embedding edge, not the public
shape. The durable architectural context is [architecture § Source](../architecture.md#source).

## Why this is not a Gateway concern

Vendor-call metering belongs at the **Source** seam, not the **Gateway** caller-policy seam. The
Gateway cannot do this job:

```
   caller ──► Gateway ──────► profile root (Reservoir) ──► Arbiter ──► Source ──► Provider ──► VENDOR
              ▲                      │                                                          ▲
              │                      └── retention decides here whether                         │
        counts REQUESTS                  a vendor is touched at all                      counts CALLS
     (caller quota — a real,                                                        (vendor spend — this
      separate meter, and the                                                        ticket's meter)
      REST surface's concern)
```

On a warm store a request costs **zero** vendor calls. A meter above the `Reservoir` therefore
counts something with no relationship to spend. The two meters are both legitimate and they are not
the same instrument.

## What to build

A **vendor-call ledger**: an injected ambient collaborator, in the same position and lifecycle as
`Clock` — `compose` builds it and threads it down, so a deployment has exactly one
([ADR-0005](../adr/0005-build-time-composition.md)). It records one entry per **outbound vendor
call**, attributed to the `SourceKey` that made it.

The counter cannot live in the leaf: a Provider is **stateless by contract**, and a Probe may not
even read a `Clock` ([architecture § Provider](../architecture.md#provider-leaf-manifold),
[edge/provider.md](../edge/provider.md)). The ledger holds the state; the leaf holds a reference.

**This slice observes only.** The ledger has no authority to refuse a call, and no code path
branches on its contents. That authority is [01-0155](./01-0155-vendor-budget-governor.md), and the
split is deliberate: watch what the real spend is before letting a budget throttle production
traffic — the same discipline the roadmap applies to bias correction (*"correct only after the bias
proves stable"*).

## Decisions this ticket's align owns

- **The `metered` declaration** — decided 2026-08-21 (0124 align review) to be a **provider
  property on `ProviderManifest`** (`open-meteo: True`, `twc: True`, `collector-obs: False`),
  never derived from key-existence; this ticket mints the field ([ADR-0005](../adr/0005-build-time-composition.md)
  gains it then) and **restores the metered-uncached refusal** in the `SourceBinder` — where
  build-time refusals live, and where the TODO sits; `wire_source` only reads store presence — that the
  [scatter substrate](./done/01-0124.0010-scatter-substrate.md) loosening leaves as a TODO-marked gap —
  a storeless metered vendor must refuse again once the fact exists to read.
- **What an entry is** — one HTTP request, or one `Provider.project`? These differ the moment a
  provider paginates or a natural fetch unit answers wider than the ask.
- **Attribution granularity** — per `SourceKey`, per offering, per parameter? Vendors price
  differently, and a per-parameter count is not derivable after the fact from a per-call one.
- **Period and persistence** — a vendor quota is usually calendar-scoped (per day, per month). A
  process-lifetime counter cannot answer a calendar question, which couples this to the
  [persisting store](./01-0145-persisting-store.md)'s substrate question without necessarily sharing
  its answer.
- **Read-out channel** — [minimal resolution logging](./02-0195-minimal-resolution-logging.md) owns
  producer-selection and store hit/refill evidence, which an operator reads *together* with spend.
  This slice ships the smallest honest read-out it needs; 0195 later absorbs or extends it rather
  than duplicating it. 0195 itself stays in release 02 — it depends on per-parameter selection and
  the error taxonomy, which the beeline demotes.
- **What a fault costs.** A call that 429s is still a call. Whether failed calls count against the
  meter is a vendor-contract question, per vendor.

## Acceptance criteria

- [ ] Every outbound vendor call is recorded, attributed to its `SourceKey`, with a period stamp.
- [ ] A warm-store request that touches no vendor records **nothing** — the meter measures calls,
      not requests, and this is the assertion that proves it.
- [ ] The ledger is injected, not global: two composed profiles in one process do not share a
      counter unless deliberately handed the same one.
- [ ] The Provider leaf remains stateless — a guard pins that no count is held below the injection
      point.
- [ ] No behavioural change: a suite run with the ledger disabled and one with it enabled return
      identical Coverages for identical requests.
- [ ] No secret, key, or credential appears in any ledger entry or its read-out.

## Parent scope addressed

- Roadmap Phase 2 (operational substrate): provider metrics under operator control.
