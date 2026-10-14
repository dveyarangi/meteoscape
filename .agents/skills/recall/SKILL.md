---
name: recall
description: Determine where the project stands and what to work on next, with the decisions already taken surfaced alongside the questions genuinely still open. Use when asked what is next, where things stand, or to continue or pick up work.
---

Mechanism: not yet


Your goal is to find out the actual state of the project and the current and/or next things to focus on, without re-opening anything already settled. Start from the delivery status and the last session, and read what bears on the item in flight; survey more widely only when nothing is in flight or the trace meets a gap.
<hitl>
- Immediately, before starting heavier reads, greet user with short intro/greeting, show some immediate interesting status.
- Output wake/recall updates as the stages are comlpeted.
</hitl>
- Investigate last sessions and actual tickets against the roadmap/version plan and find out where are we standing. Sessions, `tickets/done` and `rfc/done` are dated snapshots — read them for *why*, never for *whether* something is still open. Check `git status` and recent log too: uncommitted work is part of the actual state.
- An open ticket or RFC whose work has landed in the tree, but whose acceptance criteria are not all checked, is the next session's first item. The still-open ticket is the evidence the work is unfinished; a session record is not. Live verification that could not complete in the shipping session is the usual remainder.
- Read the architecture and the open questions for the decisions and items that bear on it; look up a question's resolution or state wherever it lives — most pending items are at least referenced in existing documentation. Be thorough about the item in flight: follow its references until they converge, rather than reading each doc in isolation.
- Every question you surface as open must cite where it is *still* open — in a maintained doc (delivery status, the question store, architecture, ADRs, glossary, edge records) or in the working tree. Otherwise it is settled: cite the deciding artifact instead, including the code where the code settled it. A question with no home at all is a documentation gap, so report it as one.
- Build a compact summary of current state of the project and bring up all relevant items for current or next task, including the decisions already taken that bear on it, each with its reference. The summary must be written in simple but precise language, no moonspeak.

- In case of ambiguity, present it too user. In case when continuation requires decision making, invoke /align skill.
- Read the next item from the order the queue states; do not re-rank it. Check whether, since that order was set, priorities or product requirements changed, the order came to contradict itself — a dependency, a status or another statement of it — or a HITL resolution found complexity or a split the order does not yet reflect. Name each such occasion and put the reordering to the user. A last session's handoff is a list of candidates, not an order.
- Report drift you hit while reading (stale headers, docs the tree has outrun) rather than fixing it — fixing is outside recall's scope. A dated snapshot — a session record, a done ticket — does not drift: what the tree has since moved past in it is history, not drift.

## Installed from other mechanisms

<installed by="questions">
**Q2** Start from the wake's read — the one the host's session-start hook put in your context, or
`questions.py --wake --session <tag>` with the tag that read named; a bare `--wake` registers a new
session, and is for a host whose hook registered none. Report where the other sessions stand, what is suspect, which deferrals
may now be due, and which straw dogs are due; take this session's position from the person or
estimate it, and place it with `at`. Re-rank nothing another running session is on; then read the queue as this skill says.
</installed>

<installed by="ticket">
**P12** Read the live tickets with `tickets.py --list` before ordering the queue or minting a ticket.
</installed>
