---
name: edge
description: Maintain per-surface Edge records — living seam documents aggregating a product edge's architectural status; contract shape, upstream invariants with their validation state, edge-scoped concerns, and staged roadmap. Use when establishing or populating an Edge record, checking changes or code against an edge, or deriving customer-facing edge descriptions.
---

# Edge records

An **Edge record** is the living per-surface document where everything about one product edge
aggregates — **the seam between architecture and user-oriented design**. It holds:

- the edge's current **Contract** shape — the consumer-visible request/response/outcome surface
  as built;
- the strict **Invariants** upstream machinery owes the edge, each naming the edge test that
  validates it;
- the edge-scoped **Concerns** — pointers into `docs/concerns.md` with their edge-local reading;
- the staged, caller-visible **Roadmap** of the edge's evolution, linked to owning tickets.

Customer-facing descriptions of the edge (tool descriptions, public API docs) are **derived from**
the record and must stay a subset of it — never the other way around.

One record per product surface, at `docs/edge/<surface>.md` (e.g. `mcp.md`, `embedding.md`).
Format: [EDGE-FORMAT.md](../align/EDGE-FORMAT.md) (the align skill's format shelf — one canonical
copy). "Edge record" and the reserved lowercase *edge* are defined in `docs/glossary.md`.

## Goals

Your goal is one or more of the following, according to the task at hand:

1. **Establish** — help the user create a surface's initial Edge record, or populate it from the
   existing docs, tests, and code. Start `Status: Stub`; a record graduates to `Normative` only
   when every stated invariant either names a passing validator or is consciously dropped.
2. **Monitor** — check recent changes (diff, branch, landed ticket) against the affected Edge
   records. A change that alters a promise must be named **breaking or compatible**; always
   `/align` with the user on major or incompatible changes before updating the record. New
   edge-touching concerns or roadmap shifts land in their sections as part of the same pass.
3. **Validate** — audit the existing code, tests, docs, and derived customer-facing text against
   the record: no code behavior may contradict a Normative promise; every named validator must
   still exist and still assert its promise; **⚠ unguarded** markers in a Normative record are
   findings; a derivation claiming what the record doesn't means the record is behind. Report
   contradictions with the evidence (test, code path, doc line) rather than silently fixing
   either side — which side is wrong is the user's call.
4. **Derive** — produce or refresh a customer-facing description of the edge (tool description
   text, public API doc) as a subset projection of the record.

## Boundaries

- Aggregate by reference: `concerns.md` owns concerns, tickets own delivery state,
  `architecture.md` owns the internal shape — the record holds the edge-local projection and the
  link, never a copy.
- Do not generalize *edge* to other artifacts: in this project, edge means the system's outer
  boundary. Arch-doc-to-code sync is `/sync-arch`; decision-time contract challenges live in
  `/align`'s Edge rule.
