# Ticket format

This shelf owns ticket naming, delivery-state vocabulary, the shape of a
ticket as a record, and what the queue in `docs/tickets/README.md` holds.
What an RFC *contains* is `/plan`'s.

## Numbering

```
docs/tickets/done/01-0010.0010-life-informs-dev-harness.md
              │  │    └── slug — what the ticket is.
              │  └─────── position — global. Changes when priority changes.
              └────────── release — the contract the ticket serves.
```

- Names are `01-NNNN-slug.md`. Positions step by 10. Insert by splitting the
  difference: `0015`, then `0012`. Positions stay four digits — longer numbers
  break numeric ordering. When the gap is exhausted, take the nearest free
  slot on the correct side. Never renumber anything else.
- Allocate a position where the ticket will actually be worked, not merely at
  the end, checking both `docs/tickets/` and `docs/tickets/done/` for the
  surrounding positions.
- A child appends a four-digit position: `01-0010.0010`. Depth is unbounded
  and means "is a child of", nothing else — work merely filed after `0010`
  takes `0020`.
- A release closes when its contract's criteria are met, not on a date. A
  later release's ticket may land first.
- Completed tickets keep their number.

### One basename per work item

A ticket and its RFC share a basename. Cite by slug through a relative link;
add the `done/` segment when the target completes.

When every acceptance box is checked, including `/verify`, move the ticket to
`docs/tickets/done/` and its RFC to `docs/rfc/done/`, and repair the
citations that pointed at them. A paired close (ticket + RFC) is one pass —
one invocation, so each moved record cites the other's final home:

```
uv run --offline --no-project python .agents/scripts/gw/move_doc.py \
    docs/tickets/RR-NNNN-slug.md docs/tickets/done/RR-NNNN-slug.md \
    docs/rfc/RR-NNNN-slug.md docs/rfc/done/RR-NNNN-slug.md
```

The mover repairs citations and touches nothing else — no checkbox, no
status, no date, no Git index. Eligibility and the ticket header are yours.
[/maintain](../maintain/SKILL.md) owns the surrounding pass.

Artifacts predating this keep their names.

## Status

`Done` · `In progress` · `Ready` · `Partial` · `Planned` · `Blocked`

- **Ready** — dependencies complete, work can start. **Planned** —
  dependencies are not.
- **Partial** — some behavior landed; criteria remain open.
- **Blocked** — stuck for a reason *other than* an incomplete dependency.
  Waiting on a dependency is `Planned`.
- One parenthetical qualifier is allowed: `Planned (own align precedes)`,
  `Ready (aligned 2026-09-08)`. `Done`'s parenthetical opens with its date;
  words may follow after a comma: `Done (2026-09-08, split)`.

## The contract

A ticket is a unit of agreed work. Whatever holds one states its outcome — one sentence of
observable behaviour; the question it
answers; what to build; its acceptance criteria, each observably true when done and one
of them verification; its parent, where it was carved from one; and its status. It is done when
every criterion holds, verification included.

The file under `docs/tickets/`, in the shape below, is the contract's default form. A project's own
board — issues, Linear, Jira — stands in for the file where each of its items states all of the
above; the harness supplies no adapter, and its scripts read the file form alone.

## The record

A ticket is a record of the ticket mechanism, and this section is its
declared shape — what `tickets.py --check` holds every live ticket to, format
never content *(the user, 2026-09-08)*.

- **A record** is one ticket file under `docs/tickets/`, live until paired
  close moves it to `done/`. **Tier 2**: read when the ticket is planned,
  implemented or verified, or through a citation. **What removes an entry**:
  paired close, when every acceptance box is checked, the `/verify` box
  included. Archived records are matched by name for pairing and exempt from
  everything else; older fields in them are left, and a live record carries
  none.
- **The kind** is *what it intends to become* while the ticket is live, and
  *what happened* once it closes. A ticket carries it as `- **record of**
  what it intends to become`, the line after its title; the mover turns it
  to `what happened` as it closes the pair. The mark has no colon, which
  tells it from a field; its earlier name, `kind`, is reported.
- **The shape** is read from `Minted`. A ticket is minted from the body of
  the question it answers once the work's form is seen, never before, and
  holds what is actual for the work — the existing state where it bears
  included — filling the picture by references rather than restating it. A
  decision lands where it is made, the story goes to evidence or a session
  record, and the ticket links them. A checked box with its date is the whole
  verification record. A ticket
  minted before 2026-10-11 is held to the required sections and the `/verify`
  box alone, and is brought to this shape at its next touch.

### The header

The bullet list after the mark, one form, ending at the first line that is
neither a bullet nor an indented continuation. Known fields in this order, a
one-off field anywhere before `Outcome`, `Outcome` last:

```md
# {Title}

- **record of** what it intends to become
- **Status:** {value} {(qualifier)}
- **Type:** HITL | AFK
- **Minted:** YYYY-MM-DD
- **Plan:** [{title} RFC](../rfc/{basename}.md) — what it selected
- **Depends on:** [{title}](./RR-NNNN-slug.md) ({what it supplies})
- **Blocks:** [{title}](./RR-NNNN-slug.md) — {why}
- **Answers:** [q-NNNN](../questions/q-NNNN-{slug}.md)
- **Outcome:** {the delivered change, one sentence}
```

| Field | Presence | Checked | Written |
|---|---|---|---|
| `Status` | required | a [status](#status) value with at most one parenthetical; `Done`'s opens with the date | |
| `Type` | required | `HITL` or `AFK` | `HITL` needs a human decision or review; `AFK` merges unattended. |
| `Minted` | required | a day, `YYYY-MM-DD` | the day the ticket was written; its shape is read from it |
| `Plan` | exactly when an RFC with the ticket's basename exists under `docs/rfc/` or its `done/` | its link resolves to that RFC | plus one clause on what it selected |
| `Depends on` | optional | every link resolves | blockers, each with a parenthetical naming what it supplies — not a bare link |
| `Blocks` | optional | every link resolves | only when the blocking relation is itself an argument; carries its `— why` |
| `Answers` | required | one link to an entry of the question store, live or in `done/`, whose `owner` is this ticket | the question the ticket's goal answers — its *what for*; its open questions sit under that entry, and a child ticket's question under its parent's |
| one-off fields | optional | every link resolves | `Trigger`, `Related`, `Owning decision` and the like, when the ticket carries that fact |
| `Outcome` | required, last | one sentence | observable behavior, never code shape |

`Kind` is not a field. Older tickets use `Legacy id:` / `RFC:` / `Parent PRD`
/ `User stories addressed`; they are archived, leave them.

### The sections

- `Title` — names the outcome, not the mechanism. No number, no release.
- `Parent` — the spec or coarse ticket this was carved from; otherwise the
  durable doc owning the context. Never a session. A subticket says which
  slice it is and what the parent keeps.
- `What to build` — **required**. End-to-end behavior, not a file-by-file
  plan. Each constraint carries its reason. Rewritten in place as decisions
  land.
- No `Open issues` section: a ticket's unresolved decisions and HITL forks are
  entries of the question store under its `Answers` question, each holding its
  own argument. A reader draws them with `questions.py --tree <its Answers id>`.
- `Acceptance criteria` — **required**. Checkboxes, each observably true when
  done; one names `/verify`. Provisional criteria say so in the heading, after
  a dash, and are firmed in place at the align.
- `Out of scope` — what a reader expects and won't find, each with its actual
  home.
- `Parent scope addressed` — the parent's stories or criteria this closes, by
  number. The record of the split the user approved; nothing derives coverage
  from it yet.

A ticket holds the five sections named above and nothing else; its
`Acceptance criteria` holds checkbox lines, their continuations and blank
lines, nothing else.

### Acceptance criteria

- Behavior altitude, always: types, fields, formulas and module layout are
  the RFC's.
- Name the instrument when the naive check would pass for the wrong reason.
- Refactor tickets: behavior unchanged, the new constraint machine-enforced
  by a failing guard test, dependents unblocked.
- A parent split into subtickets states the end-state that holds only when
  all children land.
- Check a box only for work that satisfied it; a criterion satisfied early is
  checked with a date.
- Every ticket includes a `/verify` criterion. A ticket is not Done until
  `/verify` has been run against it. Do not move to `done/` without it.

### Pairing

For every file under `docs/rfc/` or `docs/rfc/done/`, a ticket with the
same basename exists under `docs/tickets/` or `docs/tickets/done/`, and both
sit in the same folder state. Only names are read; nothing inside an RFC is.

### Conventions

- Cite by slug through a relative link; add the `done/` segment when the
  target completes.
- Reference the architecture, ADRs, glossary, open questions and edge records;
  never restate them.
- Date a criterion checked early and a status flip; nothing else accretes.
- Wrap at ~100 columns.

## The queue

The queue is `docs/tickets/README.md`: the order of the work and its
candidate. It copies nothing a ticket says; the live tickets are listed by
`tickets.py --list`. It keeps no account of steps done: the
session records hold it. It is of the kind *what it intends to become*, and
carries `- **record of** what it intends to become` on the line after its
title, held by `tickets.py --check` where the queue exists.
