---
name: edge
description: Maintain Edge records — one per edge where the system meets those who consume it or extend it. Use when establishing or populating an Edge record; when adding an extension such as a host, or re-checking one after it changes; when checking changes or code against an edge; or when deriving consumer- or extender-facing text from a record.
---

Mechanism: edge

# Edge records

An **edge** is where the system meets those who consume it or extend it. Its **record** holds what
the system promises there and what it requires of what attaches, the checks a new extension
passes, where each extension stands, the edge-scoped concerns, and the staged roadmap. One record
per edge at `docs/edge/<edge>.md`, one sidecar per extension at `docs/edge/<edge>/<extension>.md`;
the shape is [EDGE-FORMAT.md](./EDGE-FORMAT.md).

Text for a consumer or an extender — tool descriptions, public API docs, an install guide — is
**derived from** the record and stays a subset of it, never the other way around.

## Goals

Your goal is one or more of the following, according to the task at hand:

1. **Establish** — help the user create an edge's record, or populate it from the existing docs,
   tests, and code. Start `Status: Stub`; a record graduates to `Normative` only when every stated
   invariant either names a passing validator or is consciously dropped.
2. **Extend** — attach a new extension, such as a host. Build its integration in its own home —
   code and configuration, never the record — to the record's `Contract`; pass each of the
   record's `Extending` checks in a live session; then write its sidecar, `Integration` naming
   where every part lives and `Conformance` one result per check, and its `Extensions` row. A
   check nobody watched is `unobserved`, however sure the documentation sounds. Pass the checks
   again for an extension that changed upstream or whose integration moved, rewriting only the
   results they touch.
3. **Monitor** — when asked, check recent changes (a diff, a branch) against the affected records.
   A change that alters a promise is a finding until a decision changes the promise: name it
   **breaking or compatible** and align with the user before the record is touched. New
   edge-touching concerns or roadmap shifts land in their sections as part of the same pass.
4. **Validate** — audit the code, tests, docs, and derived text against the record, after
   `edges.py --check` holds its form: no code behavior may contradict a Normative promise; every
   named validator must still exist and still assert its promise; **⚠ unguarded** markers in a
   Normative record are findings; a derivation claiming what the record doesn't means the record
   is behind. Report contradictions with the evidence (test, code path, doc line) rather than
   silently fixing either side — which side is wrong is the user's call.
5. **Derive** — produce or refresh text for a consumer or an extender as a subset projection of
   the record.

## Boundaries

- Aggregate by reference: the question store owns open questions, a ticket's header owns its
  delivery state, the architecture owns the internal shape, the code owns the integration — the record holds
  the edge-local projection and the link, never a copy.
- An edge is where the system meets someone outside it who consumes it or attaches to it. A seam
  between two of the system's own parts is the architecture's, never an edge.
