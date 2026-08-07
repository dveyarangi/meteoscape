---
name: to-tickets
description: Use to decompose a parent work into independently-workable child tickets. Use to mint ticket(s), possibly a single one, when planning implementation without one.
---

# Decompose into tickets

Break a parent work into independently-grabbable tickets using vertical slices (tracer bullets), written as local markdown files under `docs/tickets/`. The parent is a **PRD** at inception, a **coarse ticket** when zooming in; or the currently discussed/referenced chunk of work; the same slicing principles apply at every resolution.

## Layout

- **Active tickets** live flat in `docs/tickets/RR-NNNN-short-title.md`. The naming and numbering
  rules are owned by [Ticket numbering](../../../docs/tickets/README.md#ticket-numbering) — read it
  before allocating a number; do not restate it here.
- **Completed tickets** move to `docs/tickets/done/` (all acceptance boxes checked). Keep the filename; only the folder changes.
- The **parent** is referenced by its own path (a PRD like `docs/v1-requirements.md`, or a ticket); child tickets do not duplicate it.

## Process

### 1. Locate the parent

Ask the user for the parent work item's path, unless it is already clear from context.

If the parent is a document not already in your context window, read it from the file. When the parent is the chunk of work under discussion, there is no file — the tickets must then carry their own context.

### 2. Explore the codebase (optional)

If you have not already explored the codebase, do so to understand the current state of the code.

### 3. Draft vertical slices

Break the parent into **tracer bullet** tickets. Each ticket is a thin vertical slice that cuts through ALL integration layers end-to-end, NOT a horizontal slice of one layer. Slice at the parent's own resolution: a coarse ticket's children are thinner passes through the same territory, still demoable or verifiable on their own.

Slices may be 'HITL' or 'AFK'. HITL slices require human interaction, such as an architectural decision or a design review. AFK slices can be implemented and merged without human interaction. Prefer AFK over HITL where possible.

A ticket blocked on unresolved product or architectural decisions may begin as a **decision-bearing
HITL ticket**. It is the eventual feature ticket in an earlier phase, not a separate decision slice;
name it for the product outcome it will deliver.

<vertical-slice-rules>
- The goal is to break down into small deliverables that can be tested by user, before the entire schema/service/UI is built. Vertical step-by-step.
- Each slice delivers a narrow but COMPLETE path through every layer (schema, API, UI, tests)
- A completed slice is demoable or verifiable on its own
- Prefer many thin slices over few thick ones
- A chunk that is already ticket-sized yields a single ticket — a valid outcome, not a failed decomposition
</vertical-slice-rules>

### 4. Quiz the user

Present the proposed breakdown as a numbered list. For each slice, show:

- **Title**: short descriptive name
- **Type**: HITL / AFK
- **Blocked by**: which other slices (if any) must complete first
- **Parent scope covered**: which user stories or acceptance criteria of the parent this addresses

Ask the user:

- Does the granularity feel right? (too coarse / too fine)
- Are the dependency relationships correct?
- Should any slices be merged or split further?
- Are the correct slices marked as HITL and AFK?

Iterate until the user approves the breakdown.

### 5. Create the ticket files

For each approved slice, write a markdown file at `docs/tickets/RR-NNNN-short-title.md` (e.g. `docs/tickets/01-0210-add-user-auth.md`).

Allocate positions per [Ticket numbering](../../../docs/tickets/README.md#ticket-numbering) — place each
slice where it will actually be worked, not merely at the end, and check both `docs/tickets/` and
`docs/tickets/done/` for the surrounding positions. Children of a ticket take subticket positions
under their parent, per the same rules. Add a row to the delivery map in the same pass.

Create files in dependency order (blockers first) so you can reference real filenames in the "Blocked by" field. A blocker that is already complete lives in `docs/tickets/done/` — reference it there.

Do NOT use `gh issue create` or any GitHub CLI commands. Do NOT reference GitHub issue numbers. Use local filenames for all cross-references.

<ticket-template>
## Parent

Path to the parent work item — the PRD, or the coarse ticket this slice was carved from. A conversation-born ticket cites the owning durable doc (concern, roadmap line) instead — never a session — or drops this section and carries its own context.

## What to build

A concise description of this vertical slice. Describe the end-to-end behavior, not layer-by-layer implementation. Reference specific sections of the parent rather than duplicating content.

## Acceptance criteria

<!-- Behavioral only — see "Acceptance criteria hold the behavior altitude" -->

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Blocked by

- Blocked by `docs/tickets/RR-NNNN-title.md` (active) or `docs/tickets/done/RR-NNNN-title.md` (already complete). Refer to blockers **by slug**, not by number.

Or "None - can start immediately" if no blockers.

## Parent scope addressed

Reference the parent's user stories or acceptance criteria by number:

- User story 3
- User story 7

</ticket-template>

### Decision-bearing ticket lifecycle

A decision-bearing ticket is the working document for an [/align](../align/SKILL.md) session and
then becomes the implementation-ready feature ticket for the same outcome. Do not mint separate
decision and implementation tickets for that outcome.

- **At minting:** `Outcome`, `What to build`, and `Acceptance criteria` describe the alignment exit:
  the decision is landed in its durable home and the feature is unblocked. Hold the decision tree —
  evidence, alternatives, and open questions — in the ticket.
- **Concern promotion:** leave only the architectural contact surface in `concerns.md` under its
  stable anchor, add `→ queued as <ticket-slug>`, and move the deliberation into the ticket.
- **During alignment:** follow [/align](../align/SKILL.md)'s inline resolution rule; the ticket is the
  live working document.
- **At resolution:** land decisions in their durable homes, remove the resolved concern entry (or
  retain separately-scoped residue), and rewrite the same ticket in place to feature altitude:
  behavioral outcome, end-to-end work, acceptance criteria, blockers, and parent scope. Preserve
  its slug and parent; keep its queue position unless the resolved dependencies require reordering
  under the repository's numbering rules.
- **If the resolved feature is too coarse for one RFC:** retain the ticket as the parent/end-state
  and decompose it through `/to-tickets`; do not create a sibling merely to hold the implementation.
- **If alignment eliminates the feature:** complete the ticket as a landed decision; this is the
  only case where it closes without becoming an implementation ticket.

### Acceptance criteria hold the behavior altitude

- A criterion states what is observably true when the ticket is done — verifiable by a test, a
  probe, or a user action. Code shape (types, fields, formulas, module layout) is the RFC's
  (`/plan-impl`); ticket prose may sketch mechanism, criteria never do.
- Refactor tickets: criteria are that existing behavior is unchanged (suite green through the
  reshape), the new constraint is machine-enforced (a guard test fails when violated — never "the
  code looks right"), and the dependent work is unblocked.
- A refactor too large for one RFC splits into subtickets
  (→ [Ticket numbering](../../../docs/tickets/README.md#ticket-numbering)), one RFC per child; the
  parent's criteria state the end-state that only holds when all children land.
- While a ticket is decision-bearing, its provisional criteria follow the decision-bearing
  lifecycle above. Once transformed, this behavior-altitude rule applies in full.
- The `Outcome` line holds the same altitude as the criteria.
- A ticket that fits none of these shapes → `/align` before writing it.

### 6. Completing a ticket

When every acceptance box is checked, `git mv` the file from `docs/tickets/` to `docs/tickets/done/`. Fix any "Blocked by" references that pointed at it (they gain the `done/` segment).

Do NOT close or modify the parent; a parent ticket completes on its own acceptance criteria, not by its children emptying out.
