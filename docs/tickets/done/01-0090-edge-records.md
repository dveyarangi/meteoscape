# m5 — Edge records and the `/edge` skill

- **Status:** Done (2026-07-25) — skill, format file, `/align`/`/sync-arch` rules, glossary
  term, both record homes, and the populated Normative MCP record landed. Includes the same-day
  reframe: the Edge record is the architecture ↔ user-oriented-design seam document, not a
  customer-facing contract; customer text derives from it.
- **Depends on:** none — documentation and skill tooling only; no code path changes.
- **Related:** [m6 — Artifact conventions sweep](../01-0200-artifact-conventions-sweep.md) later
  classifies Edge records in the artifact registry; it does not gate this ticket.
- **Outcome:** per-surface **Edge records** — the consumer-visible contract of each product
  surface, validated by edge tests — with an `/edge` skill to establish and maintain them, and
  edge awareness wired into `/align` and `/sync-arch`.

## Why

The consumer-visible contract of each product surface has no owning document: architecture.md owns
the internal shape, but the *promise* (what an embedder or MCP client may rely on, and the strict
upstream invariants edge tests must validate) is scattered across tickets, requirements, and code.
[Concern #39](../../concerns.md#39-python-embedding-surface-and-public-failures) already forecasts one
such document ("the public API guide") for the embedding surface.

An Edge record is a **normative** artifact — something breaks if it is wrong, and edge tests are
the mechanism that catches it. "Edge" is *not* generalized to mean any artifact: in this project
*edge* stays the system's outer boundary (glossary discipline), and Edge records document exactly
that boundary's contract. The wider artifact taxonomy this distinction seeds belongs to
[m6](../01-0200-artifact-conventions-sweep.md).

## Decisions (recorded as the align resolves them)

- **One Edge record per product surface** (2026-07-25): embedding surface and MCP surface each get
  their own record; later protocols add theirs. The surfaces have independent lifecycles (MCP is
  live in code; the embedding facade is open at #39), so a unified document would carry a permanent
  half-normative split. Shared canonical semantics (Selection/Coverage behavior, cross-surface
  consistency) stay in architecture.md/ADRs; Edge records reference, never restate.
- **Edge record ≠ architecture.md** (2026-07-25): the Edge record owns the consumer-visible
  promise; architecture.md keeps the internal shape.
- **Home and naming** (2026-07-25): `docs/edge/<surface>.md` (`mcp.md`, `embedding.md`) — the
  singular collection directory matches `docs/adr/` / `docs/rfc/` house style. No numbers, no
  `done/`: Edge records are living documents named by surface; history is git's. At landing,
  [#39](../../concerns.md#39-python-embedding-surface-and-public-failures)'s "public API guide"
  wording is repointed at `docs/edge/embedding.md`. Glossary entry **Edge record** added at the
  align (2026-07-25).
- ~~**Record format** (2026-07-25): sections `Contract` / `Invariants` / `Not promised` /
  `Compatibility`; the record narrates to the surface's end user.~~ **Reframed (2026-07-25,
  same day):** the Edge record is **not** a customer-facing contract document — it is the **seam
  between architecture and user-oriented design**, the living aggregation surface for one
  product edge's status. Audience: the project at work. Customer-facing descriptions (tool
  description text, public API docs) are *derived from* the record as subsets, never the source.
  Sections: `Contract` (consumer-visible shape as built — the derivation source) / `Invariants`
  (per-invariant validators inline; **⚠ unguarded** legal in a Stub, a finding in a Normative
  record) / `Concerns` (pointers into concerns.md with the edge-local reading) / `Roadmap`
  (staged caller-visible evolution, plans not promises). Normative core, descriptive periphery.
  The format file lives on the align skill's shelf (`EDGE-FORMAT.md`), `/edge` references it.

## What to build

1. **`/edge` skill (narrow):** establish/populate a per-surface Edge record from existing
   docs/code; monitor changes against it; validate code and docs against it; `/align` on major or
   incompatible changes. Edge records carry the compact end-user contract (embedded code or API
   endpoint description) and the strict upstream invariants edge tests validate.
2. **Edge awareness in `/align` and `/sync-arch`:** `/align` gains a challenge rule symmetric to
   the glossary rule — when a plan touches consumer-visible behavior, check the affected surface's
   Edge record; a contradiction is either a plan bug or a deliberate contract change, and a
   contract change must be named breaking/compatible out loud. An `EDGE-FORMAT.md` joins the align
   skill's format files (alongside `GLOSSARY-FORMAT.md` / `ADR-FORMAT.md`) so inline updates land
   in one shape. `/sync-arch`'s validated doc set gains the Edge records.
3. **Populate the live surface:** the MCP surface record is populated from what is live in code;
   the embedding record starts as the stub home #39's decisions will land in.

## Acceptance criteria

- [x] Each existing product surface (embedding, MCP) has an Edge record home established
      (`docs/edge/mcp.md`, `docs/edge/embedding.md`, both `Status: Stub`, 2026-07-25).
- [x] The MCP record is populated from the live surface and graduates to `Normative`
      (2026-07-25: contract, seven guarded invariants, seven scoped concerns, six roadmap
      stages; the errors.py `RuntimeFailure` docstring over-promise found and fixed in the same
      pass).
- [x] The `/edge` skill exists and states the establish / monitor / validate / align goals against
      per-surface records (2026-07-25).
- [x] `/align` carries the Edge challenge rule and `EDGE-FORMAT.md`; `/sync-arch` lists Edge
      records in its doc set (2026-07-25).
- [x] Glossary carries the resolved terms (Edge record vs lowercase boundary *edge*) (2026-07-25).

## Out of scope

- The artifact conventions registry, normative/descriptive classification of the whole doc roster,
  and skill slimming — [m6](../01-0200-artifact-conventions-sweep.md).
- Settling concern #39's open embedding-facade decisions — the embedding Edge record starts as the
  home those decisions will land in, not a forcing function for them.
- Any code change; deterministic and parity suites are untouched.
