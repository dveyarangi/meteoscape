# Edge record Format

One record per product surface, a living document at `docs/edge/<surface>.md` (e.g. `mcp.md`,
`embedding.md`). No numbers, no `done/` — the record is named by its surface and never completes;
history is git's.

An Edge record is the **seam between architecture and user-oriented design**: the living surface
where everything about one product edge aggregates — its current contract shape, the strict
invariants upstream machinery owes it (with their validation state), the edge-scoped concerns,
and its staged evolution. The audience is the project at work (user and agents). Customer-facing
descriptions of the edge (tool descriptions, public API docs) are **derived from** the record and
must stay a subset of it — never the other way around.

## Structure

```md
# Edge — {Surface}

- **Status:** Stub | Normative

## Contract

The edge's consumer-visible shape as built: request, response, outcomes — the source of truth
customer-facing derivations project from. Reference canonical semantics (ADRs, architecture)
instead of restating them.

## Invariants

The strict behavior upstream machinery owes this edge. One bullet each, **each naming its
validator inline:**

- Vendor nulls reach the wire as JSON `null` — *validated by:* `tests/deterministic/...`
- An invariant with no test is marked **⚠ unguarded**.

## Concerns

Edge-scoped open questions and risks — pointers into `docs/concerns.md` (which stays their
owner), each with its edge-local reading: what this concern means at this surface.

## Roadmap

The staged, caller-visible evolution of this edge — one line per stage, linked to its owning
ticket. Plans, not promises.
```

## Rules

- **Normative core, descriptive periphery.** `Contract` and `Invariants` are promises — in a
  `Status: Normative` record everything there is true of the live edge (`Stub` is the only
  license for aspiration). `Concerns` and `Roadmap` are aggregation — pointers and plans, never
  validated, no delivery-status vocabulary (status lives in `docs/tickets/README.md`).
- **Per-invariant validators, not a separate section.** Each promise points at the test that
  enforces it, so `/edge` and `/sync-arch` can check mechanically that the validator still
  exists and still asserts the promise. **⚠ unguarded** is legal in a Stub, a finding in a
  Normative record.
- **Aggregate by reference.** `concerns.md` owns concerns, tickets own delivery state,
  architecture.md owns the internal shape — the record holds the edge-local projection and the
  link, never a copy.
- **Derivations are subsets.** Any customer-facing text about the edge must be derivable from
  the record; if a derivation says something the record doesn't, the record is behind — fix it
  first.
- **A contract change is named out loud.** Any edit that changes a promise is declared breaking
  or compatible at the moment it is made (the `/align` Edge challenge rule). When a Roadmap
  entry's ticket lands, the same edit that updates `Contract` removes the entry.
