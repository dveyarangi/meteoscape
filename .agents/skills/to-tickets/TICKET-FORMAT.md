# Ticket format

Two artifacts, owned by `/to-tickets`: the **ticket**, `docs/tickets/RR-NNNN-slug.md` → `done/` when
every box is checked; the **queue**, `docs/tickets/README.md`, which owns order and delivery state.

## Numbering

```
docs/tickets/done/01-0115-retentive-store-freshness.md
              │  │    └── slug — what the ticket is. Never changes. Cite by this.
              │  └─────── position — global across releases. Changes when priority changes.
              └────────── release — the contract the ticket serves.
```

- Positions step by 10. Insert by splitting the difference: `0015`, then `0012`, then `00105`. Never
  renumber anything else.
- A subticket appends a level: `0130.0010`. Depth is unbounded and means "is a child of", nothing
  else — work merely filed after `0130` takes `0135`. A slice carved out of unstarted work is
  usually a prerequisite, so it sorts *before* its origin and cannot nest.
- Positions are one global line across releases: `02-0130` runs between `01-0120` and `01-0150`. The
  folder groups by release; the delivery map is the only cross-release order.
- A release closes when its contract's criteria are met, not on a date. A later release's ticket may
  land first.
- Cite tickets by slug, never by number.
- Maintenance is a `Kind`, never a filename prefix.
- Completed tickets keep their number.

### One basename per work item

The ticket names the work; its other artifacts take the same basename —
`docs/tickets/01-0119-live-window-edge-tolerance.md` ↔ `docs/rfc/01-0119-live-window-edge-tolerance.md`.

- Each artifact moves to its own `done/` on its own completion, basename intact.
- Repositioning a ticket renames its RFC in the same change.
- Cite a plan by its ticket's slug ("the TWC provider RFC"), never by a serial or position.
- Artifacts predating this keep their names.

What an RFC *contains* is `/plan-impl`'s. Adoption dates and the legacy-id map are the queue's.

## Status

`Done` · `In progress` · `Ready` · `Partial` · `Planned` · `Blocked`

- **Ready** — dependencies complete, work can start. **Planned** — dependencies are not.
- **Partial** — some behavior landed; criteria remain open.
- **Blocked** — stuck for a reason *other than* an incomplete dependency. Waiting on a dependency is
  `Planned`.
- One parenthetical qualifier is allowed: `Planned (own align precedes)`, `Done (split)`. `Done`
  carries its date.

## The ticket

```md
# {Title}

- **Status:** {value} {(qualifier)}
- **Type:** HITL | AFK
- **Kind:** Maintenance
- **Plan:** [{title} RFC](../rfc/{basename}.md) — what it selected
- **Depends on:** [{title}](./RR-NNNN-slug.md) ({what it supplies})
- **Blocks:** [{title}](./RR-NNNN-slug.md) — {why}
- **Outcome:** {the delivered change, one or two sentences}

## Parent
## {Why this exists}          ← 0..n, titled for the claim each argues
## What to build
## Decisions this ticket's align owns
## Acceptance criteria
## Out of scope
## Parent scope addressed
```

Always present: `Status`, `Outcome`, `What to build`, `Acceptance criteria`. The rest appear when
they have something to say. Header fields keep this order; `Outcome` is always last.

| Field | Rule |
|---|---|
| `Status` | A [status](#status) value. |
| `Type` | `HITL` needs a human decision or review; `AFK` merges unattended. |
| `Kind` | `Maintenance` when the work delivers no product capability. Absent otherwise. |
| `Plan` | The RFC link plus one clause on what it selected. Absent until a plan exists. |
| `Depends on` | Blockers, each with a parenthetical naming what it supplies — not a bare link. |
| `Blocks` | Only when the blocking relation is itself an argument; carries its `— why`. |
| `Outcome` | Observable behavior, never code shape. Copied verbatim into the delivery map. |

One-off fields (`Trigger`, `Related`, `Owning decision`) are fine when the ticket carries that fact.
Older tickets use `Legacy id:` / `RFC:` / `Parent PRD` / `User stories addressed`; leave them, don't
write them.

| Section | Rule |
|---|---|
| `Title` | Names the outcome, not the mechanism. No number, no release. |
| `Parent` | The PRD or coarse ticket this was carved from; otherwise the durable doc owning the context (architecture section, roadmap phase, concern). Never a session. A subticket says which slice it is and what the parent keeps. |
| Narrative | Titled for what it argues (`What goes wrong today`, `Why this is not a Gateway concern`). Diagram the mechanism; link the evidence (`reservoir.py:113`, an ADR anchor). Say what is deliberately *not* a defect. Omit entirely when the framing is uncontested. |
| `What to build` | End-to-end behavior, not a file-by-file plan. Each constraint carries its reason. |
| `Decisions this ticket's align owns` | One bullet per open question, each saying why it cannot be answered yet. After the align it becomes `What this ticket does not decide`, resolved entries struck and answered inline. |
| `Acceptance criteria` | Checkboxes, each observably true when done. |
| `Out of scope` | What a reader expects and won't find, each with its actual home. |
| `Parent scope addressed` | The parent's stories or criteria this closes, by number. |

### Acceptance criteria

- Behavior altitude, always: types, fields, formulas and module layout are the RFC's.
- Name the instrument when the naive check would pass for the wrong reason — "pinned by counting
  transport calls, not by inspecting the gate."
- Refactor tickets: behavior unchanged, the new constraint machine-enforced by a failing guard test,
  dependents unblocked.
- A parent split into subtickets states the end-state that holds only when all children land.
- Provisional criteria say so in the heading, and are firmed in place at the align.
- Check a box only for work that satisfied it; a criterion satisfied early is checked with a date.

### Conventions

- Cite by slug through a relative link; add the `done/` segment when the target completes.
- Local files only — no `gh issue create`, no issue numbers.
- Reference the ADRs, architecture, glossary and concerns; never restate them.
- Strike superseded text, answer inline in bold, keep the question.
- Date anything that changed after minting.
- Update the queue in the same pass.
- Wrap at ~100 columns.

## The queue

```md
# Delivery status

**Last updated:** YYYY-MM-DD
**Current stage:** {what landed, what is next, links to both}

{who owns what: roadmap = direction, requirements = contract, architecture/ADRs = design,
 tickets = criteria; sessions and done/ are history}

## Status vocabulary
## Available today
## Delivery map
## Ticket numbering
### Legacy ids
## Recommended execution order
## Decisions still owned by tickets
## Maintenance rule
```

| Section | Rule |
|---|---|
| `Last updated` | The date **delivery state** last moved, not the date the file was last touched. A copy-edit or a link repair does not advance it; a status flip, a minted ticket, or a reorder does. A reader uses it to ask "how stale is this queue", which an edit date would answer wrongly. |
| `Status vocabulary` | Points at [Status](#status); defines nothing. Adds only what is true of this repo's use of it. |
| `Available today` | `Capability \| Status \| Current behavior` — what a caller can do now and what is honestly missing. Each row links the ticket that changes it. |
| `Delivery map` | `# \| Ticket \| Kind \| Status \| Depends on \| Outcome` — the canonical order, one row per ticket across all open releases. `Maint` rows hold a position but appear in no capability table. |
| `Ticket numbering` | This repo's adoption record. Points at [Numbering](#numbering); restates none of it. |
| `Legacy ids` | `Legacy \| Now`, after a scheme change. |
| `Recommended execution order` | The reasoning behind the order, never a second copy of it. Superseded stretches stay as written under a dated heading. |
| `Decisions still owned by tickets` | One bullet per ticket holding an unresolved decision. |
| `Maintenance rule` | Update this page and the ticket header when delivery state changes; link here instead of restating status elsewhere. |
