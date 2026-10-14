# Development process

Work is tracked and argued in this repository. There is no external tracker: state, order and
argument all live in these files, so nothing is registered anywhere else — no GitHub issues, no
issue numbers. What each document owns is [the documentation map](./README.md)'s; this page holds
what connects them — the naming that links the document family, and the skill loop that moves work
through it.

## Naming

The document family shares names, never content:

- A ticket names the work; its other artifacts take the same basename —
  `docs/tickets/01-0119-live-window-edge-tolerance.md` ↔ `docs/rfc/01-0119-live-window-edge-tolerance.md`.
  Each moves to its own `done/` on its own completion, basename intact; repositioning a ticket
  renames its RFC in the same change.
- Cite a ticket by its slug, never by number; cite a plan by its ticket's slug ("the TWC provider
  RFC"), never by a serial or position.
- A spec is a local markdown file under `docs/`, named for the effort — agree the filename with the
  user (the existing release contract is [`v1-requirements.md`](./v1-requirements.md); not every PRD
  is a requirements doc). A spec is argument rather than a work item, so it registers nothing; the
  tickets it decomposes into carry the work onto [the queue](./tickets/README.md).

The ticket's own scheme — `RR-NNNN-slug`, position allocation, subticket depth — is
[TICKET-FORMAT.md § Numbering](../.agents/skills/ticket/TICKET-FORMAT.md#numbering)'s, as is
the delivery-state vocabulary ([§ Status](../.agents/skills/ticket/TICKET-FORMAT.md#status))
and the mechanics of the `done/` move
([§ One basename per work item](../.agents/skills/ticket/TICKET-FORMAT.md#one-basename-per-work-item)).

## The loop

The skill loop is the GoodWolf harness's, stated in [AGENTS.md § The loop](../AGENTS.md#the-loop);
its skills are under `.agents/skills/`.
