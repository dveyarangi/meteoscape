# Mechanical record moves

- **Status:** Done
- **Type:** AFK
- **Kind:** Maintenance
- **Depends on:** [doc-corpus integrity gate](./01-0127-docs-integrity-gate.md) (the corpus
  primitives the mover transforms with, and the guards that verify each move)
- **Outcome:** Closing a ticket or RFC into `done/` and archiving a session into `history/` are
  performed by one mechanical mover that re-depths the moved record's links and rewrites every
  inbound reference, leaving nothing link-shaped to hand-edit; the integrity gate verifies each
  move.

## Parent

[cicd.md § CI pipeline](../../cicd.md#ci-pipeline) — the gate polices moves after the fact; this
ticket removes the hand-performed step the gate cannot reach.

## Why the manual step must go

The 0127 RFC records its own residual hole: the moment a record moves into an exempt directory,
its outbound links leave the gated set, so the re-depth of the moved file stays owed by
convention — checked by nobody. And the incident record shows the manual step is the injection
vector, not just a toil cost: the 59 invisible `\x01` characters that passed both `grep` and
reading were introduced by a *hand-performed re-depth repair pass*. Detection plus manual repair
still routes every close through the step that caused the worst defect.

The transformation is wholly mechanical — `git mv`, fold the depth change into every relative
link inside the moved file, rewrite every inbound reference corpus-wide — which is what makes it
script-shaped. One mover serves all three lifecycle moves: ticket → `done/`, RFC → `done/`,
session → `history/YYYY-MM/`.

## What to build

A script at `.agents/scripts/move_doc.py` (home decided at minting: beside the skills that own
the close-out ritual, stable across the `.claude`/`.codex`/`.cursor` symlinks), run via
`uv run python`. Given tracked source→destination pairs — one or several in a batch; *(landing
2026-08-18)* a paired close moves ticket and RFC in one invocation so each moved record cites the
other's *final* home, which single-file moves cannot achieve — it:

- performs the `git mv`;
- re-depths every relative link inside the moved record — link *paths* only, `#anchor` fragments
  and all prose untouched;
- rewrites every inbound reference to the old path across the corpus;
- refuses the move (writing nothing) when source or destination falls outside the tracked corpus;
- ends by naming the verification command — the two guard modules are the proof of the move, so
  the script owns the transformation and the gate owns the truth.

Judgment stays out: no box-checking, no status flips, no queue prose. Those are the close-out's
human half, and the conventions guard already polices their outcome.

## Acceptance criteria

- [x] Moving an active ticket or RFC into `done/` re-depths its internal links and rewrites every
      inbound reference; both guard modules pass immediately after, with zero manual edits —
      pinned by running the guards as the acceptance instrument.
- [x] Archiving a session into `history/YYYY-MM/` passes the same bar.
- [x] The mover changes nothing but link paths: statuses, boxes, and prose are otherwise
      byte-identical — pinned by diffing a synthetic corpus move.
- [x] A move whose source or destination is outside the tracked corpus is refused with nothing
      written, pinned by a negative test.
- [x] The re-depth transform is unit-covered on nested `../` paths and anchor-carrying inbound
      links, through synthetic corpora.
- [x] [TICKET-FORMAT.md](../../../.agents/skills/to-tickets/TICKET-FORMAT.md)'s completion rule and
      [cicd.md](../../cicd.md#ci-pipeline) name the mover as the mechanical step of a move.

## Out of scope

- Box-checking, status flips, and queue-row prose — judgment, kept manual; the
  [doc-corpus integrity gate](./01-0127-docs-integrity-gate.md) polices their outcome.
- Committing — the mover stages nothing beyond what `git mv` implies; `/commit` rules are
  untouched.
