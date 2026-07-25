# m6 — Artifact conventions sweep

- **Status:** Planned (maintenance) — its own align precedes implementation; this ticket carries
  the design sketch, not settled design.
- **Depends on:** [m5 — Edge records](./done/m5-edge-records.md) (done) — the Edge record must
  exist as an artifact type before the roster that classifies it is remapped.
- **Outcome:** one canonical **artifact conventions registry**; every document type in the
  [documentation map](../README.md) analyzed against the artifact definitions and classified;
  conventions (numbering, lifecycle, location) remapped where they drift; artifact-supporting
  skills reference the registry instead of restating it.

## Why

The doc-supporting skills (`to-tickets`, `to-spec`, `align`, `sync-arch`, `conclude`) share one
artifact lifecycle — scaffold/populate → maintain inline → detect drift → escalate — and each
restates its supporting conventions (numbering, `done/` folders, reference-don't-duplicate, format
files). The restatements are drifting apart. The 2026-07-25 align surfaced the load-bearing
classification the registry must encode: **normative** artifacts carry a validation obligation
(something breaks if the document is wrong, and a mechanism should catch it — architecture.md,
ADRs, glossary, Edge records) while **descriptive** artifacts are records nothing validates
against (sessions, ideas). Granularity (singleton / ledger / per-instance) and lifecycle (living /
transient-with-`done/` / append-only) are the other axes.

## Scope (to be firmed at this ticket's align)

1. **Analyze the full doc roster** against the artifact definitions: every row of the
   [documentation map](../README.md) gets granularity, lifecycle, normative-vs-descriptive,
   validated-by, and owning-skill classifications; mismatches between a document's actual behavior
   and its class are findings to resolve, not footnotes.
2. **Remap conventions** where the analysis demands it, including **sequencing types**: the flat
   NNN ticket numbering cannot express subticket hierarchies without breaking order. Design
   sketch — fixed-width positional numbering with reserved nesting levels, e.g.:
   - `00100000 — improve docs`
   - `00101000 — create /edge skill`
   - `00101010 — append /edge records to /align`
   - `00102000 — extract artifact conventions`

   or

   - `001---`
   - `001A--`
   - `001A1-`
   - `001B--`
   or somethin'
   + maintenance flag?
   Whether existing tickets renumber, or the scheme applies only forward, is an align question.
3. **Registry home:** extend the [documentation map](../README.md) table or mint a sibling
   conventions document — decided at the align.
4. **Skill slimming:** each artifact-supporting skill references the registry for conventions it
   currently restates; no skill remains the private owner of a shared convention.

## Acceptance criteria (provisional until the align)

- [ ] The conventions registry exists; every artifact type in the documentation map is classified
      on all axes (granularity, lifecycle, normative/descriptive, validated-by, owning skill).
- [ ] A sequencing scheme supporting nested subtickets is decided and documented (adopted or
      explicitly rejected with reasons).
- [ ] No artifact-supporting skill restates a convention the registry owns.
- [ ] Contradictions found during the roster analysis are resolved or filed as concerns.

## Out of scope

- The `/edge` skill and Edge records themselves — [m5](./m5-edge-records.md).
- A metaskill that *generates* artifact-supporting skills — deferred until the registry proves
  insufficient.
- Any code change.
