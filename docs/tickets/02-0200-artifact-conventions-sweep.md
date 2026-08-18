# Artifact conventions sweep

**Legacy id:** m6 · **Kind:** Maintenance

- **Status:** Planned (maintenance) — its own align precedes implementation; this ticket carries
  the design sketch, not settled design.
- **Depends on:** [m5 — Edge records](./done/01-0090-edge-records.md) (done) — the Edge record must
  exist as an artifact type before the roster that classifies it is remapped.
- **Outcome:** one canonical **artifact conventions registry**; every document type in the
  [documentation map](../README.md) analyzed against the artifact definitions and classified;
  conventions (numbering, lifecycle, location) remapped where they drift; the registry names each
  convention's owner instead of requiring artifact-supporting skills to duplicate it.

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
   - **A split does not imply a child.** Both real splits in this project (the second provider out of
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
   - **RFC filename identity (settled 2026-08-11).** An RFC uses the exact basename of its owning
     ticket: `docs/tickets/RR-NNNN-slug.md` pairs with `docs/rfc/RR-NNNN-slug.md`. Moving either
     completed artifact to its `done/` folder preserves the basename. Repositioning an active
     ticket renames its RFC in the same change. The decisive constraint is one RFC per
     implementation-ready ticket; an independent RFC sequence and datestamp create a second
     identity without describing a second lifecycle.
   - **RFC citation identity (settled 2026-08-11).** The independent RFC serial is retired from
     document titles and link text as well as filenames. Cite a plan by its owning ticket's slug
     (for example, `TWC provider RFC`), never by an RFC number or the ticket's mutable position.
     Authored and amended dates remain document metadata so a completed RFC retains its historical
     context without gaining a second identity.
   - **RFC convention ownership (settled 2026-08-11).** The `plan-impl` skill owns the RFC filename
     and citation convention because it creates and repeatedly amends that artifact. This replaces
     this ticket's older assumption that every convention must live in a central registry. The
     registry should name and link to an artifact-local owner; other skills should follow that owner
     rather than restating the rule.
   - **RFC document header (settled 2026-08-11).** The H1 is the owning ticket's title followed by
     `â€” implementation plan`, with no RFC serial, release/position, or date in the heading. An
     `**Authored:** YYYY-MM-DD` metadata line follows; `**Last amended:** YYYY-MM-DD` is present only
     after a later revision. The title follows the ticket if its slug/title changes, while the dates
     preserve the plan's historical context.
3. **Registry home:** extend the [documentation map](../README.md) table or mint a sibling
   conventions document — decided at the align.
4. **Skill slimming:** each convention has one named owner. Cross-artifact conventions may live in
   the registry; artifact-local operational conventions may live in the skill that creates and
   maintains that artifact. Other skills reference the owner instead of restating the rule.

## Acceptance criteria (provisional until the align)

- [ ] The conventions registry exists; every artifact type in the documentation map is classified
      on all axes (granularity, lifecycle, normative/descriptive, validated-by, owning skill).
- [x] A sequencing scheme supporting nested subtickets is decided and documented (adopted or
      explicitly rejected with reasons). — **done 2026-08-02**, see scope item 2.
- [ ] Every convention has one named owner; no artifact-supporting skill restates another owner's
      convention.
- [ ] Contradictions found during the roster analysis are resolved or filed as concerns.

## Out of scope

- The `/edge` skill and Edge records themselves — [edge records](./done/01-0090-edge-records.md).
- A metaskill that *generates* artifact-supporting skills — deferred until the registry proves
  insufficient.
- Any code change.
