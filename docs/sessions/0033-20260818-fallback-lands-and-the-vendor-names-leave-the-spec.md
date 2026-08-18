# 0033 · 2026-08-18 · Fallback lands, and the vendor names leave the spec

**Scope:** the same day as 0032's close, picked up at `/recall`. One product ticket start to finish —
0121 through align, five planning passes, implementation, review, close, and a `/sync-arch`. The
session opened with a challenge to the recall summary itself: *"the project is shaped to be
provider-agnostic — is this 'metered primary' rooted deep in the docs? it should not be."*

## Work done

- **`/recall` → a challenge** — the summary leaned on the beeline's narrative register ("a metered
  primary's 429"), and the challenge asked whether that framing had reached the mechanism. It had
  not: selection is `OfferingDef.priority` integers and `ArbiterPolicy`, with vendor-anonymity
  machine-enforced (`test_config_imports_nothing_from_nodes`). The prose, not the design, needed
  the correction.
- **`/align`, four decisions** — criteria de-vendored, the quota criterion folded, the
  `ArbiterPolicy` knob refused, and a ticket-internal contradiction about
  [#28](../concerns.md#28-reconciler-interface-selection-ordering-vs-per-cell-fold) corrected.
- **`/plan-impl` and four further validation passes** — pass 2 corrected two harness facts, pass 3
  verified the store-level no-splice and pinned the catch's scope, pass 4 caught the vanishing
  fault text, pass 5 found no defect and one elegance win. The passes ran dry, which is what
  ended them.
- **Implementation** — one projection loop replacing the fast-path/`_assemble` fork, request-scoped
  fault memory, results collected per projection.
- **`/review-impl`** — high match; three findings (two mechanical, one the pending close-out).
- **The close** — seven boxes checked, delivery status and the capability row updated, ticket and
  RFC moved into `done/` in one `move_doc` batch. The integrity guard then failed on a code comment
  citing the ticket's pre-move path: the mover rewrites documents, not comments, and the guard is
  what closes that loop — on the first close after its own.
- **`/sync-arch`** — all eight named validators verified live; two prose drifts corrected.

Footprint: **112 lines** in `src`, **241** in `tests`, against a doc corpus that mostly *shrank* per
edit. 409 tests, pyright and ruff clean.

## Settled this session

- **Fall-through is the `priority` reconciler's meaning, not configuration** — no `ArbiterPolicy`
  change and no operator knob; "off" is composing one producer; different fault behaviour is a
  different `Reconciler` → [0121 (done)](../tickets/done/01-0121-second-provider-fallback.md),
  [architecture § Arbiter](../architecture.md#arbiter).
- **Wholesale fall-through does *not* ride the #28 widening** — that widening serves *combining*
  reconcilers, which must see values; fall-through never sees values →
  [#28](../concerns.md#28-reconciler-interface-selection-ordering-vs-per-cell-fold),
  [ADR-0004](../adr/0004-producer-resolution-and-capability.md).
- **A mechanism's acceptance criteria name no vendor** — vendor identity flows through selection as
  data (ordering keys, provenance), never as a branch; the criteria are stated over priority-ordered
  producers, and vendor names live in the wiring layer and as test arguments →
  [0121 (done)](../tickets/done/01-0121-second-provider-fallback.md).
- **The catch wraps the child `project` call only** — the Arbiter's own closed-projection
  `RuntimeFailure` is an engine break in a producer's costume, and retrying it would hide a real bug
  → [RFC 0121 (done)](../rfc/done/01-0121-second-provider-fallback.md) § 3.
- **A projection-time `CapabilityMismatch` propagates** — fall-through is for faults, not
  unservability → same, rule 4.
- **The exhaustion error carries the last fault's own text** — only the message crosses the MCP wire,
  so a bare "producers faulted" would erase the cause an operator sees today → same, rule 3.
- **No-splice is structural below the Arbiter too** — a Holding's key carries no T and is replaced
  whole, so a spliced `valid_time` is unrepresentable across requests →
  [store.py](../../src/meteoscape/nodes/store.py) `assimilate`.
- **The MCP whole-request `runtime-failure` invariant is loosened, compatibly** — a request that used
  to fail may now succeed; no succeeding request changes → [edge/mcp.md](../edge/mcp.md),
  Roadmap 1 discharged.
- **A composite parity instrument takes its order as an argument** — provider order and keys are CLI
  options, `secret_ref` derives from the manifest's `SecretSlot`, so the check carries no vendor
  conditional → [tests/parity/test_composite.py](../../tests/parity/test_composite.py).

## Found, not settled

- **`architecture.md`'s Failure section states a target contract in the present tense** — "omits any
  whose candidates all fault… returns the producible subset" has never been true of the build, and
  fall-through moved the build one step closer, which is exactly when such a sentence starts reading
  as delivered. Marked **target** inline this session; the underlying question of when it becomes
  true is [#30](../concerns.md#30-response-membership-under-runtime-degraded-fallback) /
  [0190](../tickets/01-0190-error-taxonomy-partial-success.md).
- **Request-scoped fault memory has no name.** "A producer that faulted in this request is skipped
  for the rest of it" is a load-bearing rule with no glossary term. Deliberately left unnamed — a
  one-call-scoped list may not deserve vocabulary — but it is the kind of unnamed rule that later
  gets re-invented under a worse name.

## Open questions

All live in their owning documents; cited, not restated.

- Membership on exhaustion — omit the parameter or fail whole →
  [#30](../concerns.md#30-response-membership-under-runtime-degraded-fallback), Roadmap 3 at
  [edge/mcp.md](../edge/mcp.md).
- Per-parameter partial success and absence reasons →
  [0190](../tickets/01-0190-error-taxonomy-partial-success.md).
- Whether TWC's native units create the multi-vendor spread that triggers the conversion catalogue →
  [0122](../tickets/01-0122-unit-conversion-edge.md).
- Parity enforcement and routing → [#41](../concerns.md#41-parity-evidence-is-unenforced-and-unrouted).
- Tick convention → [#48](../concerns.md#48-a-tap-cannot-declare-where-its-value-sits-relative-to-the-tick)
  / [0126](../tickets/01-0126-tick-convention-declaration.md).

## Continuation

1. **0122 or 0123** — the delivery status states the fork: unit conversion if TWC's native units
   create the real spread its trigger waits for, else config and graceful degrade, which owns
   key-absent as the *degraded* mode.
2. **Sweep sessions 0028–0029 into `history/2026-08/`** when they age past the rolling window —
   `move_doc` makes this mechanical now.
3. **`uv sync` stayed blocked** all session (the running MCP server holds `meteoscape.exe`); work
   ran under `--no-sync`. Environment fact, not a defect — carried over from 0032.

## Advisory read

**What is great.** The session's best work was done before any code: the opening challenge caught a
framing error while it was still prose. "Metered primary" had colonised the ticket's mechanism
language and one acceptance criterion re-accepted a ticket already delivered — both would have
become code shape. The design was never wrong; the words around it were drifting toward a
vendor-shaped mechanism, and someone reading only the ticket would have built one.

**What is good enough.** Five planning passes on a change that is ultimately one loop. The passes
were not wasted — each of 2, 3 and 4 found something real — but the yield curve was visible, and
pass 5's single finding was an elegance improvement, not a defect. The stopping rule that worked was
watching the *kind* of finding degrade, not counting passes.

**What is questionable.** The RFC's line count grew across passes while the plan itself simplified.
Twice this session a "remove this" produced a net addition, and the second time it was called out.
The corpus convention — strike a decision, keep its reason — is right, but it has no compaction step
before a record closes; the reasons ride into `done/` at full length.

**What is out of balance.** Nothing structural. The doc-to-code ratio inverted again this session,
and for the second consecutive product ticket the plan was executable enough that implementation
found nothing the plan had not.

**Hidden edges.** The mover and the guard divide the corpus between them along a line neither
declares: `move_doc` rewrites *documents*, the integrity guard checks *code comments*, and a
lifecycle move touches both. The guard caught the gap immediately, so the pair is complete in
effect — but the completeness is emergent, not designed, and a future mover extension could
plausibly assume it owns comments too.

The second: the acceptance criteria and the architecture's target contract drifted in *opposite*
directions this session. The criteria over-specified reality (naming vendors a generic mechanism
never sees) while architecture under-specified it (describing an omission contract the build has
never had). Same corpus, same day — the failure mode is not a bias toward aspiration or toward
concreteness, but toward whichever register the document was written in.

**What would make life easier.** A compaction pass at close time — the moment a ticket moves to
`done/`, its struck questions have served their purpose and could collapse to one line each.
`/denoise` exists; it is simply not part of the close.

**What next.** 0122 or 0123, per the delivery status's fork.
