# edge — rules installed into skills

Machine input for the installer, read by nobody at session time. Amend a rule here, then
install it with overwrite; the block in a target is never the place.

| target | anchor |
|---|---|
| `.agents/skills/maintain/SKILL.md` | `## Installed from other mechanisms` |
| `.agents/skills/align/SKILL.md` | `### Challenge against the Edge records` |
| `.agents/skills/verify/SKILL.md` | `## Installed from other mechanisms` |

## E1 — the records are checked by their maintainer

- **target** `.agents/skills/maintain/SKILL.md`
- **authority** the user, 2026-10-10

<rule>
Check the edge records and their sidecars with `edges.py --check` — form, never content. A
diagnostic is a finding; repair it under the repair policy.
</rule>

## E2 — a record is held to what it names

- **target** `.agents/skills/maintain/SKILL.md`
- **authority** the user, 2026-10-10

<rule>
An edge record is of the code and configuration it names. When the scope moves a part that a
record under `docs/edge/` names, re-read what it says of that part. A promise the code no longer
keeps is drift, reported with its evidence and never rewritten to fit.
</rule>

## E3 — a plan is challenged against the edges it touches

- **target** `.agents/skills/align/SKILL.md`
- **authority** the align skill's own text, moved here 2026-10-10

<rule>
When the plan touches an edge — where the system meets those who consume it or extend it — check
that edge's record under `docs/edge/`. A contradiction with its Contract or Invariants is either a
plan bug or a deliberate contract change, and a contract change is named **breaking or
compatible** out loud before proceeding. As decisions land, write them into the record in the
shape of `.agents/skills/edge/EDGE-FORMAT.md`: a contract change in `Contract` and `Invariants`,
marked `⚠ pending — <ticket>` until its ticket lands and the record set `Normative (tentative)`
while any is pending, a promise without a validator marked **⚠ unguarded**; newly surfaced
edge-scoped concerns as pointers in `Concerns`; staging shifts in `Roadmap`.
</rule>

## E4 — a landed change at an edge writes its record

- **target** `.agents/skills/verify/SKILL.md`
- **authority** the user, 2026-10-10

<rule>
When the landed work changes an edge — a promise in its Contract or Invariants, an invariant's
validator, or a check of its Extending — the same commit writes its record under `docs/edge/`. A
promise the landing makes true loses its `⚠ pending` mark, and the record leaves
`Normative (tentative)` when no mark is left; a landing that breaks a promise no decision changed
is a finding, never written into the record. The Roadmap entry of the ticket that landed is
removed. An extension observed live in this work has what was seen written in its sidecar, dated,
not only in the ticket or the session record.
</rule>
