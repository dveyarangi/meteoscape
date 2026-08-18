# Second-provider fallback — implementation plan

**Authored:** 2026-08-18
**Last amended:** 2026-08-18 (pass 2: e2e rides the existing respx harness; parity is not collected
by CI at all; the double-projection trap gets a test; one-loop shape guidance. Pass 3, two
convergent reviews: `TODO(#30)` at the exhaustion site; e2e asserts the backstop's own `exp`;
only-`RuntimeFailure`-only-from-the-child pinned — projection-time `CapabilityMismatch` and the
closed-projection engine break stay uncaught, each with a test; store-level no-splice verified
structural; observability pointer to 0195. Pass 4: 429-not-retried verified at the transport;
exhaustion message must carry the last fault's text — the wire shows only the message;
`test_tool_error_prefixes` greenness re-attributed: it mocks above the Arbiter. Pass 5: the
composite check derives `secret_ref` from the manifest's `SecretSlot` — no vendor conditionals in
the instrument)

Implements [01-0121 — second-provider fallback](../../tickets/done/01-0121-second-provider-fallback.md).

## 1. What changes

One behavior, one place. Today, when the producer chosen for a parameter blows up mid-request, the
whole request fails. After this ticket, the Arbiter tries the next producer in priority order:

```
ask temperature
  → priority-0 producer  → RuntimeFailure (vendor 429, timeout, garbage…)
  → priority-1 producer  → serves its whole window          request succeeds
```

No new config, no new policy object, no reconciler change — the 2026-08-18 align settled all three
(recorded in the ticket). The change is confined to `Arbiter.project`
([arbiter.py](../../../src/meteoscape/nodes/arbiter.py)).

## 2. Facts this plan stands on (verified in code)

- `Reconciler.select` already returns the **full** priority-ordered candidate list; `project` walks
  it and keeps the first candidate whose `serves` admits — [arbiter.py](../../../src/meteoscape/nodes/arbiter.py)
  `project`.
- The fault arrives at **projection** time, after winners are grouped per producer — both on the
  single-winner fast path and inside `_assemble`. So fall-through means: catch the fault, re-select
  for that producer's parameters with the faulted producer excluded, project again.
- Every transport-level fault is already one class, `RuntimeFailure`
  ([base.py](../../../src/meteoscape/nodes/providers/base.py)) — a 429 and a 500 are indistinguishable
  here, by design.
- A Source is `Reservoir(store, Provider, clock)`. A Source with fresh holdings serves them without
  touching the vendor — so fallback triggers only on a real fault, never instead of a warm serve.
- The no-splice rule survives the **root store across requests** with no extra work: a Holding's
  key carries no T and assimilate is insert-or-overwrite whole — *"a spliced `valid_time` is
  unrepresentable"* ([store.py](../../../src/meteoscape/nodes/store.py) `assimilate`). A fallback
  answer simply replaces the primary-origin Holding.
- The wire promise being changed is the [MCP edge record](../../edge/mcp.md) invariant
  *"`runtime-failure` is whole-request"*, carried as Roadmap 1. Loosening it is **compatible**:
  requests that used to fail now succeed; no succeeding request changes.

## 3. Behavior rules (determinate)

1. **Fall-through on fault.** A `RuntimeFailure` from a winner's projection sends that producer's
   admitted parameters back through selection, skipping every producer that already faulted in this
   request. The next admitting candidate is projected for those parameters — the **whole** window,
   from that one producer (wholesale; the no-splice rule is
   [v1-requirements](../../v1-requirements.md) § v1 invariants).
2. **Request-scoped memory only.** "Already faulted" lasts for one `project` call. No cross-request
   state, no circuit breaker — standing spend authority is the
   [governor](../../tickets/02-0155-vendor-budget-governor.md)'s.
3. **Exhaustion fails the whole request.** If a parameter that was admitted and attempted runs out
   of candidates (all faulted, or none of the rest admit), the request fails with `RuntimeFailure`,
   and the error text names the parameter, the producers that faulted, **and the last fault's own
   text** — only the message crosses the MCP wire as `ToolError` text, so a bare "producers
   faulted" would erase the cause the operator sees today. It does **not** become a
   silently-omitted parameter: silent omission means "never admitted", and moving membership on
   faults is [0190](../../tickets/01-0190-error-taxonomy-partial-success.md)'s scope, deferred with
   [#30](../../concerns.md#30-response-membership-under-runtime-degraded-fallback). The exhaustion
   raise site carries a `TODO(#30)` comment — 0190 dissolves this whole-request failure into
   per-parameter reasons, and the marker keeps later code from treating it as settled shape.
4. **Only `RuntimeFailure`, and only from the child.** A `CapabilityMismatch` a child raises at
   projection time propagates unchanged — fall-through is for faults, not for unservability. And
   the Arbiter's own closed-projection check raises a `RuntimeFailure` that is an **engine break in
   a producer's costume** ([#39](../../concerns.md#39-python-embedding-surface-and-public-failures)'s
   inventory) — the catch must wrap the child `project` call only, never the assembly checks, or a
   real bug would be retried into hiding. Admission, provenance authoring, and everything else:
   unchanged.

The loop's local shape is the implementer's choice; the rules above and the tests below are the
contract. Two constraints on that shape, both simplifications:

- **One projection loop, not two error paths.** Today `project` forks into a single-winner fast
  path and `_assemble`. Wrapping each fork in its own fault handling would double the paths;
  instead, restructure to one loop — project parameter-groups until everything admitted is served
  or exhausted — and at the end return the lone Coverage unwrapped when a single projection served
  everything (existing tests assert `result is coverage`; that identity stays), else assemble.
- **Collect results per projection, not per producer.** A fault can re-route parameters onto a
  producer that already served others — it is then projected twice, and a `dict[ProducerKey, …]`
  would silently drop one answer. (Scoped Calculator-input Arbiters get fall-through for free —
  same class, no extra work.)

## 4. Proof

### Deterministic suite (extends [test_arbiter.py](../../../tests/deterministic/nodes/test_arbiter.py))

Needs one new fake in [fakes.py](../../../tests/deterministic/fakes.py): a provider that raises
`RuntimeFailure` on `project` (and records the attempt). Cases, all over anonymous producers:

- Priority-0 faults → priority-1 serves the whole window; result is the backstop's coverage;
  provenance origin names the backstop's key.
- The faulted producer is asked exactly once (no retry within the request).
- In a two-winner assembly, a fault re-routes only the faulted producer's parameters; the healthy
  winner's result is kept and its producer is not re-projected for the parameters it already serves.
- A fault re-routes onto a producer that **already served other parameters** (P0 declares {a,b} at
  priority 1, P1 declares {b} at priority 0: b's winner P1 faults, b lands on P0, which serves a
  and b in two projections) — both answers appear in the assembled result.
- Both candidates fault → `RuntimeFailure` propagates; message names the parameter, both
  producers, and contains the last underlying fault's text.
- After a fault, no remaining candidate admits → same exhaustion failure, not an omission.
- A child raising `CapabilityMismatch` at projection time propagates it — the backstop is not
  tried, and the error is the child's own.
- Two winners with differing answer domains still fail with the closed-projection message —
  `test_winner_domains_that_differ_fail_the_whole_request` must stay green through the
  restructure, proving the engine break is not caught as a fault.
- Healthy path unchanged: priority order serves, one projection (existing tests stay green).

### E2E (extends [test_e2e_forecast.py](../../../tests/deterministic/test_e2e_forecast.py))

The harness already composes the real catalog with respx-mocked HTTP, and `_compose_both` already
wires both vendors with a test key. One new case: respx answers the primary's URL with a 429 (the
motivating fixture flavor) and the backstop's URL with the canned forecast; the MCP payload
succeeds and each served parameter's `provenance.source` names the backstop, with `exp` derived
from the **backstop's** declared cadence — the criterion's "its own expiration" half. This is the
wiring layer, where v1's concrete vendors legitimately appear. `test_tool_error_prefixes` is
untouched — it feeds a failing view straight to the Gateway, above the Arbiter, so it cannot see
this change; the prefix match is all it pins.

### Composite parity check (new, manual, opt-in — `tests/parity/test_composite.py`)

- New conftest option `--provider-order` (comma-separated impl ids, default `twc,open-meteo`);
  reuses `--twc-api-key`. Skips naming the missing key when the order needs one it doesn't have.
- Builds a `ProfileConfig` directly from the order — `OfferingDef(impl, priority=index,
  secret_ref=manifest.secret.name if the manifest declares a `SecretSlot`)`, read from
  `PROVIDER_CATALOG` — never from vendor-named `Settings`. The manifest already owns the secret
  binding ([providers.py](../../../src/meteoscape/nodes/catalog/providers.py) `ProviderManifest.secret`),
  so the test body carries **no vendor conditionals**; vendor names enter only as the order
  argument and the key options.
- Asserts each directly provider-served parameter's provenance names the priority-0 impl;
  reordering the argument inverts the expectation. Serving order only — no forced-fault case
  (a live vendor cannot be made to fault on demand; ticket align 2026-08-18).

## 5. Stages (each ends green)

1. **Fakes** — add the faulting provider fake. No behavior change.
2. **Fall-through** — red: the deterministic cases above; green: the `Arbiter.project` change.
3. **E2E** — the mocked-transport MCP case.
4. **Composite parity** — the new file and conftest option. CI never touches it: pytest
   `testpaths` is `tests/deterministic` only ([pyproject.toml](../../../pyproject.toml)).
5. **Docs at landing** — [mcp.md](../../edge/mcp.md): restate the invariant (fault falls through;
   whole-request failure only on exhaustion), mark **compatible**, discharge Roadmap 1;
   [architecture.md](../../architecture.md) and [ADR-0004](../../adr/0004-producer-resolution-and-capability.md):
   fall-through does not ride the #28 widening;
   [delivery status](../../tickets/README.md): 0121 row Done, "Second provider and fallback" row
   updated; close ticket + this RFC via `move_doc`.

## 6. Out of scope (owned elsewhere)

- Per-parameter partial success and absence reasons — [0190](../../tickets/01-0190-error-taxonomy-partial-success.md), [#30](../../concerns.md#30-response-membership-under-runtime-degraded-fallback).
- Distinguishing quota faults from other faults; spend metering and refusal —
  [ledger](../../tickets/02-0124-vendor-call-ledger.md), [governor](../../tickets/02-0155-vendor-budget-governor.md).
- Per-parameter multi-provider routing on capability (not fault) — [0170](../../tickets/01-0170-per-parameter-selection.md).
- Retry policy and its missing failure signal — [#41](../../concerns.md#41-parity-evidence-is-unenforced-and-unrouted).
- Merge-type reconcilers — [#28](../../concerns.md#28-reconciler-interface-selection-ordering-vs-per-cell-fold);
  this plan keeps the narrow `select` interface.
- A route for admitted-but-unservable (`CapabilityMismatch` at projection, rule 4) —
  [#30](../../concerns.md#30-response-membership-under-runtime-degraded-fallback)'s standing question.
- Fall-through visibility beyond provenance (an operator log line per fault) —
  [0195](../../tickets/01-0195-minimal-resolution-logging.md).
