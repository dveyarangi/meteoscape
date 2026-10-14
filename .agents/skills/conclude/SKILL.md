---
name: conclude
description: >-
  Use when a session ends, or the user asks to conclude the current chat.
---

Mechanism: not yet

First go over the session once more for what it left undone — a step a reply promised and did not
take, a decision not landed in its home, a change of its own not committed, drift met and not
reported — and finish or name each.

Write one session record under `docs/sessions/`: the account of what happened, for a reader who
has the tree and not the transcript. Substance before form — a session that produced decisions
is recorded by its decisions, not by its commits. It opens with
`- **record of** what happened`, the line after its title: it is of that kind and no other —
never repaired, never copied into the queue. It holds:

- Each decision with what chose it: the alternatives weighed, what refuted them, and the
  correction that turned the answer, in the user's words where the wording carried the point.
  The decision's home holds the result and who decided it; the reasoning stays here unless an
  evidence file or an ADR took it.
- General principles the session derived that have no durable home yet, each named as such, so
  the next session lands it rather than rediscovers it.
- What was done, briefly; what another record holds in full is linked, not repeated.
- What was refuted or went wrong, and what it taught.
- The open questions the session touched, each with where it stands and what it waits on.
- What continues, and the first step of the next session.
Session files live under `docs/sessions/`, named `NNNN-<YYYYMMDD>-<name>` with a constantly incrementing number.

The session's unpushed commits are the conclude's to settle, once the ended row is committed, by
the `push` switch: under `ask`, put to the user here; no other reply speaks of it.

## Installed from other mechanisms

<installed by="questions">
**Q3** Write a lean line on each question the session touched and left open —
`questions.py lean q-N '<line>' --session <tag>` — and nothing else: placements and closures were written as they
happened. As the conclude's last act, run `questions.py --end --session <tag>`.
</installed>
