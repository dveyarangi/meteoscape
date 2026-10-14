# questions — rules installed into the entry file and skills

Machine input for the installer, read by nobody at session time. Amend a rule here, then
install it with overwrite; the block in a target is never the place.

| target | anchor |
|---|---|
| `AGENTS.md` | `## General rules` |
| `.agents/skills/recall/SKILL.md` | `## Installed from other mechanisms` |
| `.agents/skills/conclude/SKILL.md` | `## Installed from other mechanisms` |
| `.agents/skills/maintain/SKILL.md` | `## Installed from other mechanisms` |
| `.agents/skills/align/SKILL.md` | `### Land resolutions as they are made` |

## Q1 — every message is placed before it is answered

- **target** `AGENTS.md`
- **authority** the user, 2026-09-28 to 2026-10-05

<rule>
Before drafting a reply, say what the turn is, reading this turn's window — the one the host's
hook put in your context, or `questions.py --window --session <tag>`, the script being
`.agents/scripts/gw/questions.py`:

- **On a question**: call `at` on the lowest question that contains the message. One that only
  resembles it is not its home; from a question that does not contain it, go up. Going up past
  two or more questions that resemble the message, their parent is not its home either: the
  question they jointly serve is missing — read the questions skill and open it, or the turn is
  uncharted. So is a question that contains the message only as loosely as it contains everything
  under it.
- **A new question**: the question the message is one case of, worded as the store would hold it.
  Look for its answer in the docs and the code first — found, point to it and open nothing for
  it; the turn is on the question that contains it, placed as above — a missing parent is still
  opened. Not found, or what the answer leaves unsettled, `open` it under the lowest question
  that contains it, and call `at` on it.
- **A process**, carrying out what you know how to do: no call. One run for a question is a turn
  on that question.
- **Uncharted**, a question whose home you cannot settle: no call. Ask the user where it belongs,
  in every reply until answered.
- **Banter**, a message that asks nothing of the work — no question about the project, nothing
  to do or decide: no call. Answer it. The reply writes nothing and settles nothing; a doubt, or
  an answer that would do either, makes the turn another kind.

The calls:

- `questions.py at q-0004 --session <tag>`
- `questions.py open '<question>' --under q-0004 --session <tag>`, which prints the id it gave
- `questions.py close q-0004 decided '[link](../path.md) — who, date' --session <tag>`

The store's other calls are made whenever the turn's own work settles, opens or moves a question.
Only the working agent calls, never a helper. For any other call, a closure, a branching or a
drop, read the questions skill.
</rule>

## Q2 — the wake opens at where the work stands

- **target** `.agents/skills/recall/SKILL.md`
- **authority** the user, 2026-09-29 to 2026-10-04

<rule>
Start from the wake's read — the one the host's session-start hook put in your context, or
`questions.py --wake --session <tag>` with the tag that read named; a bare `--wake` registers a new
session, and is for a host whose hook registered none. Report where the other sessions stand, what is suspect, which deferrals
may now be due, and which straw dogs are due; take this session's position from the person or
estimate it, and place it with `at`. Re-rank nothing another running session is on; then read the queue as this skill says.
</rule>

## Q3 — the conclude writes the leans and ends the session

- **target** `.agents/skills/conclude/SKILL.md`
- **authority** the user, 2026-09-29 and 2026-10-03

<rule>
Write a lean line on each question the session touched and left open —
`questions.py lean q-N '<line>' --session <tag>` — and nothing else: placements and closures were written as they
happened. As the conclude's last act, run `questions.py --end --session <tag>`.
</rule>

## Q4 — the store is checked, and finished subtrees archived

- **target** `.agents/skills/maintain/SKILL.md`
- **authority** the user, 2026-09-29, for M1's duty

<rule>
Check the question store with `questions.py --check`. A diagnostic is a finding; repair it under
the repair policy. Move each subtree it reports ready for `done/` with `move_doc.py`, every entry
of the subtree in one invocation, into `docs/questions/done/`.
</rule>

## Q5 — a question is named by a link and its words

- **target** `AGENTS.md`
- **authority** the user, 2026-10-03 — rule failure 17; every mention a link, 2026-10-12

<rule>
Every time a reply names a question — a table's cell included — its whole id is a link to its
entry; the first time, its question follows as the window writes it. No word stands in for a
question a reader has not been shown — *as before*, *the same* — it is named. A question the store
does not hold yet is written out, never named after the ticket it will belong to.
</rule>

## Q6 — a decision lands as it is made

- **target** `.agents/skills/align/SKILL.md`
- **authority** the user, 2026-10-11; moved here from the ticket's P7

<rule>
Land a decision as it is made, with its provenance: final in its durable home where no open
question's answer can change its form or home, otherwise as a straw dog bound to the nearest open
ancestor whose answer can. One with nowhere to land yet — its home is work not done — is a line in
the `## Decisions` list of the lowest question holding everyone who needs it, and takes
`→ <link>` when it lands. Close the question it answers against where it landed, and when a line
lands, repoint every entry closed against its list there.
</rule>
