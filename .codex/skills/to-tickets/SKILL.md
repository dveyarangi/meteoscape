---
name: prd-to-tickets
description: Break a PRD into independently-workable tickets and write each as a local markdown file in docs/tickets/. Use when the user wants to turn a PRD into a list of concrete tasks.
---

# PRD to Tickets

Break a PRD into independently-grabbable tickets using vertical slices (tracer bullets), written as local markdown files under `docs/tickets/`.

## Layout

- **Active tickets** live flat in `docs/tickets/NNN-short-title.md`.
- **Completed tickets** move to `docs/tickets/done/NNN-short-title.md` (all acceptance boxes checked). Keep the filename; only the folder changes.
- The **PRD** is referenced by its own path (e.g. `docs/v1-requirements.md`); tickets do not duplicate it.

## Process

### 1. Locate the PRD

Ask the user for the PRD file path (e.g. `docs/v1-requirements.md`).

If the PRD is not already in your context window, read it from the file.

### 2. Explore the codebase (optional)

If you have not already explored the codebase, do so to understand the current state of the code.

### 3. Draft vertical slices

Break the PRD into **tracer bullet** tickets. Each ticket is a thin vertical slice that cuts through ALL integration layers end-to-end, NOT a horizontal slice of one layer.

Slices may be 'HITL' or 'AFK'. HITL slices require human interaction, such as an architectural decision or a design review. AFK slices can be implemented and merged without human interaction. Prefer AFK over HITL where possible.

<vertical-slice-rules>
- The goal is to break down into small deliverables that can be tested by user, before the entire schema/service/UI is built. Vertical step-by-step.
- Each slice delivers a narrow but COMPLETE path through every layer (schema, API, UI, tests)
- A completed slice is demoable or verifiable on its own
- Prefer many thin slices over few thick ones
</vertical-slice-rules>

### 4. Quiz the user

Present the proposed breakdown as a numbered list. For each slice, show:

- **Title**: short descriptive name
- **Type**: HITL / AFK
- **Blocked by**: which other slices (if any) must complete first
- **User stories covered**: which user stories from the PRD this addresses

Ask the user:

- Does the granularity feel right? (too coarse / too fine)
- Are the dependency relationships correct?
- Should any slices be merged or split further?
- Are the correct slices marked as HITL and AFK?

Iterate until the user approves the breakdown.

### 5. Create the ticket files

For each approved slice, write a markdown file at `docs/tickets/NNN-short-title.md` (e.g. `docs/tickets/003-add-user-auth.md`).

Number tickets starting from the next available number (check what files already exist in `docs/tickets/` **and** `docs/tickets/done/`).

Create files in dependency order (blockers first) so you can reference real filenames in the "Blocked by" field. A blocker that is already complete lives in `docs/tickets/done/` — reference it there.

Do NOT use `gh issue create` or any GitHub CLI commands. Do NOT reference GitHub issue numbers. Use local filenames for all cross-references.

<ticket-template>
## Parent PRD

`docs/<prd-file>.md` (whichever PRD file was used)

## What to build

A concise description of this vertical slice. Describe the end-to-end behavior, not layer-by-layer implementation. Reference specific sections of the parent PRD rather than duplicating content.

## Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Blocked by

- Blocked by `docs/tickets/NNN-title.md` (active) or `docs/tickets/done/NNN-title.md` (already complete)

Or "None - can start immediately" if no blockers.

## User stories addressed

Reference by number from the parent PRD:

- User story 3
- User story 7

</ticket-template>

### 6. Completing a ticket

When every acceptance box is checked, `git mv` the file from `docs/tickets/` to `docs/tickets/done/`. Fix any "Blocked by" references that pointed at it (they gain the `done/` segment).

Do NOT close or modify the parent PRD file.
