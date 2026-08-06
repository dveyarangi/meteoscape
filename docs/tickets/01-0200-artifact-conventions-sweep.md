# Artifact conventions sweep

**Legacy id:** m6 · **Kind:** Maintenance

- **Status:** Planned (maintenance) — its own align precedes implementation; this ticket carries
  the design sketch, not settled design.
- **Depends on:** [m5 — Edge records](./done/01-0090-edge-records.md) (done) — the Edge record must
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
2. ~~**Remap conventions** where the analysis demands it, including **sequencing types**: the flat
   NNN ticket numbering cannot express subticket hierarchies without breaking order. Design
   sketch — fixed-width positional numbering with reserved nesting levels (`00100000` /
   `00101000` / `00101010`), or a letter-slot variant (`001---` / `001A--` / `001A1-`), or
   somethin' + maintenance flag? Whether existing tickets renumber, or the scheme applies only
   forward, is an align question.~~

   **Settled at the 2026-08-02 align — ticket sequencing only; the rest of this ticket stands.**
   Scheme adopted and documented in
   [Ticket numbering](./README.md#ticket-numbering): `RR-NNNN-slug.md`, positions stepping by 10,
   insertion by splitting the difference, `.NNNN` for subtickets, depth reserved for genuine
   children, maintenance demoted from prefix to `Kind`, citation by slug. **All existing tickets
   were renumbered** (not forward-only): the alternative left the next-to-do ticket sorting last,
   which was the symptom that motivated the change. Legacy ids are mapped in
   [Legacy ids](./README.md#legacy-ids).

   Two findings from the align that this ticket's remaining scope should carry:
   - **The letter suffix meant two different things.** `002b`/`002c` were descendants of a *live*
     parent; `003a`/`003b` were fragments of a *dissolved* one. Same syntax, different relation.
   - **A split does not imply a child.** Both real splits in this project (Visual Crossing out of
     second-provider fallback, snapped request mode out of request shaping) produced a
     *prerequisite* of the parent — which must sort *before* it, so it cannot nest. Nesting
     expresses "extends or fixes an already-positioned parent", not "carved out of work that
     hasn't started."
   - **Ticket-criteria altitude (2026-08-06).** The behavior-altitude rule landed in the
     `to-tickets` skill (criteria state observable behavior; code shape is the RFC's; refactor
     criteria = behavior preserved + constraint machine-enforced + dependents unblocked). The
     [delivery status](./README.md)'s phrase "individual tickets own implementation detail and
     acceptance criteria" predates it and reads as license for shape-in-criteria — sharpen it at
     the sweep (tickets own the definition of done; implementation detail is each ticket's
     RFC's), and fold the altitude rule into the registry so the skill stops being its private
     owner.
3. **Registry home:** extend the [documentation map](../README.md) table or mint a sibling
   conventions document — decided at the align.
4. **Skill slimming:** each artifact-supporting skill references the registry for conventions it
   currently restates; no skill remains the private owner of a shared convention.

## Acceptance criteria (provisional until the align)

- [ ] The conventions registry exists; every artifact type in the documentation map is classified
      on all axes (granularity, lifecycle, normative/descriptive, validated-by, owning skill).
- [x] A sequencing scheme supporting nested subtickets is decided and documented (adopted or
      explicitly rejected with reasons). — **done 2026-08-02**, see scope item 2.
- [ ] No artifact-supporting skill restates a convention the registry owns.
- [ ] Contradictions found during the roster analysis are resolved or filed as concerns.

## Out of scope

- The `/edge` skill and Edge records themselves — [edge records](./done/01-0090-edge-records.md).
- A metaskill that *generates* artifact-supporting skills — deferred until the registry proves
  insufficient.
- Any code change.
