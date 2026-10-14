---
name: ticket
description: >-
  Use to decompose a parent work into independently-workable child tickets.
  Use to mint ticket(s), possibly a single one, when planning implementation
  without one.
---

Mechanism: ticket

# Decompose into tickets

Break a parent work into independently-grabbable tickets using vertical slices
(tracer bullets), written as local markdown files under `docs/tickets/`. The
parent is a **PRD** at inception, a **coarse ticket** when zooming in; or the
currently discussed/referenced chunk of work; the same slicing principles apply
at every resolution.

## Layout

The shape of a ticket — its name, its folders, its header and sections, what
finishes it and what removes it — is [TICKET-FORMAT.md](./TICKET-FORMAT.md)'s,
under *The record*. Read it before writing one, and restate none of it here.

## Process

### 1. Locate the parent

Ask the user for the parent work item's path, unless it is already clear from
context.

If the parent is a document not already in your context window, read it from
the file. When the parent is the chunk of work under discussion, there is no
file — the tickets must then carry their own context.

<installed by="ticket">
**P12** Read the live tickets with `tickets.py --list` before ordering the queue or minting a ticket.
</installed>

### 2. Explore the codebase (optional)

If you have not already explored the codebase, do so to understand the current
state of the code.

### 3. Draft vertical slices

Break the parent into **tracer bullet** tickets. Each ticket is a thin vertical
slice that cuts through ALL integration layers end-to-end, NOT a horizontal
slice of one layer. Slice at the parent's own resolution: a coarse ticket's
children are thinner passes through the same territory, still demoable or
verifiable on their own.

Slices may be 'HITL' or 'AFK'. HITL slices require human interaction, such as
an architectural decision or a design review. AFK slices can be implemented
and merged without human interaction. Prefer AFK over HITL where possible.

A ticket blocked on unresolved product or architectural decisions may begin as
a **decision-bearing HITL ticket**. It is the eventual feature ticket in an
earlier phase, not a separate decision slice; name it for the product outcome
it will deliver.

<vertical-slice-rules>
- The goal is to break down into small deliverables that can be tested by
  user, before the entire schema/service/UI is built. Vertical step-by-step.
- Each slice delivers a narrow but COMPLETE path through every layer
  (schema, API, UI, tests)
- A completed slice is demoable or verifiable on its own
- Prefer many thin slices over few thick ones
- A chunk that is already ticket-sized yields a single ticket — a valid
  outcome, not a failed decomposition
</vertical-slice-rules>

### 3.1 Impact the proposed split

Run [/impact](../impact/SKILL.md) on the draft split. Record its output in
the body of the parent's question. If the recommendation is narrow or rethink, revise the draft and
run `/impact` again until the split is what you will present.

`/impact`'s current output is whether the split is balanced (proceed, narrow,
rethink, postpone). Record that. It does not yet recommend spec / ticket /
RFC / re-slice; that extension is the parent's, not this skill's.

### 4. Quiz the user

Present the **post-impact** breakdown as a numbered list, plus the impact
note. For each slice, show:

- **Title**: short descriptive name
- **Interaction**: HITL / AFK
- **Depends on**: which other slices (if any) must complete first
- **Parent scope covered**: which user stories or acceptance criteria of the
  parent this addresses

Ask the user:

- Does the granularity feel right? (too coarse / too fine)
- Are the dependency relationships correct?
- Should any slices be merged or split further?
- Are the correct slices marked as HITL and AFK?

Read `breakdown` from `AGENTS.md`'s local block. When it is `ask`,
do not mint until the user approves this presentation. That approval is what
gets minted. Ask again only if a later `/impact` would change membership,
granularity, or dependencies. Recording the impact text, or copy-edits, is
not a new approval. When `breakdown` is `auto`, mint the post-impact
breakdown without waiting.

Iterate until the user approves the breakdown (or `auto` applies).

### 5. Create the ticket files

For each approved slice, write the ticket under `docs/tickets/`, named and
registered per [TICKET-FORMAT.md](./TICKET-FORMAT.md).

Create tickets in dependency order (blockers first) so you can reference real
filenames in the `Depends on` field. A blocker that is already complete lives
in `docs/tickets/done/` — reference it there.

Write each file to [The record](./TICKET-FORMAT.md#the-record) — the header,
its fields, the sections it admits, and the citation conventions; `Minted` is
the day it is written. `Answers` links the question the slice's goal answers:
open it in the store under the parent ticket's question when the store holds
none, and `assign` it to the slice.
Each child carries a one-line pointer to the parent's recorded `/impact`
assessment.

### Decision-bearing work

An align runs on the question its work answers, and that question's body is
its working document. A ticket is minted from the body once the form of the
work is seen, never before — for decision-bearing work, after its align.

- **Question promotion:** an open question in `docs/questions/` that becomes
  work is assigned to the ticket minted for it with `assign`; its argument
  stays in the entry.
- **At resolution:** the ticket is minted, or rewritten in place, at feature
  altitude ([TICKET-FORMAT.md](./TICKET-FORMAT.md)); open a new question for
  separately-scoped residue. Keep its place in the order unless the resolved
  dependencies require moving it.
- **If the resolved feature is too coarse for one RFC:** mint it as the
  parent's end-state and decompose it through `/ticket`.
- **If alignment eliminates the feature:** no ticket is minted; the question
  closes against where its decision landed. A
  live ticket minted before 2026-10-11 as an align's working document closes
  as a landed decision.

### Altitude decides whether a slice is a ticket

Criteria state observable behavior; code shape is the RFC's
(→ [Acceptance criteria](./TICKET-FORMAT.md#acceptance-criteria)).

- A refactor too large for one RFC splits into subtickets, one RFC per child.
- A slice whose criteria cannot be written at that altitude is not yet a
  ticket → `/align` first.

### 6. Completing a ticket

A ticket is finished and closed per the shelf's [The record](./TICKET-FORMAT.md#the-record);
`/maintain` carries the duty. Do NOT close or modify the parent; a parent
ticket completes on its own acceptance criteria, not by its children emptying
out.
