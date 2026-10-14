---
name: questions
description: See where the work stands among the open questions, or re-parent, merge or prune questions by hand. Read mid-turn for the store's other calls, and before closing, branching or dropping a question.
---

Mechanism: questions

# The open questions

Every open question of this tree is one file in `docs/questions/`; the current question of each
running session is the line in its own file under `docs/questions/sessions.d/`. `questions.py` is
the only writer of the sessions folder and of an entry's parts; an entry's body, the question's argument, is written by
hand. The window is the part of the store near a session's position, drawn before every message;
**depth** is the number of *part of* steps from a question to its root, derived, never written.

## Invoked by a person

- No argument: `questions.py --tree` and the session's window drawn whole,
  `--window --session <tag> --full`.
- With an argument: the tidy-up asked for, as calls — re-parent with `move`, merge with
  `close q-N merged q-M`, prune with `close q-N pruned '<reason>'`.

Asked where things stand mid-session: `questions.py --wake --session <tag>`; it registers nothing.

## The calls

`questions.py <call> … --session <tag>`, one event each, validated and written whole; `--help`
after a call says what it takes.

| call | writes |
|---|---|
| `at q-N` | this session's position, an open question |
| `open '<question>'` · `--under q-P` | a new open question, a root or under q-P; prints the id it was given |
| `open '<question>' --between q-U q-L` | a new question under q-U, with q-L moved under it and renamed; q-L must be part of q-U |
| `move q-K --under q-P` · `move q-K --to-root` | a new parent, q-K and everything under it renamed; a cycle is refused |
| `reword q-N '<question>'` | an open question's new words; its id, parts and body stay, and its file takes the words |
| `depend q-A --on q-B` · `undepend q-A --on q-B` | q-A cannot be asked until q-B is answered, or no longer waits; a cycle is refused |
| `close q-N <kind> '<pointer>'` | the closure, below |
| `suspect q-N` · `clear q-N` | the suspect flag |
| `lean q-N '<line>'` | the lean |
| `assign q-N <path>` | the owner, the record of the work that answers the question |
| `realize q-N '<link>'` | the trace link, `A7 "<name>", …` or `derived`, replacing the one it carried |

`open` leaves the session where it stands: to stand on the new question, call `at` on the id it
printed. A refused call writes nothing and says why; fix it and call again in the same turn. Under
`debug=on` the reply opens, after the announce line when there is one, with Q1's table — a row
for each question the turn stood on, opened or closed, as the calls printed them, a move mid-turn
included; a row for a process; a row for an uncharted ask; a row for banter — never the call itself.

Free text goes in single quotes, which neither bash nor PowerShell expands; a text holding an
apostrophe goes in double quotes, with no backtick or `$` inside.

## A raised question

**Look it up first.** Every question a message raises is looked for before anything is opened, in
*the docs*: the architecture, ADRs, the glossary, the mechanism docs, the code, and the decisions
waiting in the `## Decisions` lists of the questions' bodies, where a decision sits until it has
a home. Found, point to it and open nothing; a settled question is not reopened without new evidence against its answer. An
answer that leaves part unsettled is found only in part: the rest is a raised question of its
own. There is no need to search `done/`: a decided entry links to what holds its answer.

**Who settles what is not found.** A decision that is not load-bearing, settle in the turn and
report it, as `repair=report` does. A load-bearing one is the person's: settled in the turn, it
goes to its home; not settled, open it. Unsure whether it is load-bearing, treat it as
load-bearing.

**A request.** *Build X* is a proposed answer: lean it on the question X answers — *what is X
for?* — or open that question when none is held. Open *how to build X?* under it once X is
accepted; the ticket's plan answers it. A trivial request is settled by doing it.

**Where to open it.** Under the lowest question that contains it, whatever the session stands
on. One that bears on the current question — what that question cannot be answered without
deciding, or what the method's plan expects here — is opened `--between` the current question's
parent and the current question when answering it narrows the current one and answering the
current one contributes to it; when only the first holds, beside it, under the same parent, with
`depend <current> --on <new>`.

**Outgrown words.** When the discussion on a question has moved past its words — it took in a
related topic, or found what it was really asking — `reword` it in the turn that notices, as often
as that happens: the id stays, so nothing bound to it moves. A closed question is never reworded.
Reword when everything under the question still belongs under the new words; open a parent when
the old question stays a distinct part of the wider one.

**A missing parent.** When only a far question contains the message and two or more of its
children resemble it, the question those children jointly serve is missing. Size it by the
children, never by the message. Test it: would you look under it for this question? `open` it
under the far one, `move` each child you would look for under it, leave a child you doubt where
it is, call `at` on it, and say in the reply which moved and which you left. Neither the number
of children moved nor a second parent that would sit inside or around this one is a reason to
ask. Ask only when two parents would each take the same children. Then the turn is uncharted,
and the ask names each parent you weighed and the children it would take.

**Uncharted.** The reply does the work asked and puts the question's home to the user: the
question the message is one case of, never the message restated, the homes you weighed, and the
one you would choose. The row repeats in every reply until the user answers; then open it where
they said.

<installed by="product">
**U3** A question opened right under *How is this project built?* gets its trace link at once: the
answers it realizes — `questions.py realize q-N 'A7 "<name>"'` — or `realize q-N derived` for
none.
</installed>

## Closing

**When** an answer lands, a question is found wrong, two are found to be one, one is parked, one
is made irrelevant, or one is replaced. **Do** `close` with its kind and pointer:

| kind | pointer |
|---|---|
| `decided` | a link to the doc, ADR or code that decided it, then who and when |
| `deferred` | `until <condition>, meanwhile <default>` |
| `merged` · `superseded` | the id it points to |
| `pruned` · `moot` | a one-line reason; a longer one goes to the entry's body |

The answer is never the deliberation itself. `suspect` every open child and dependent whose
assumption the answer changes; call `at` on the parent first if the closed question was current.
A `close` that finishes a subtree moves it to `docs/questions/done/` itself and says so; a closed
question with an open, deferred or suspect child stays live until that child closes. A `close`
refuses while the question's `## Decisions` list holds a decision with no home: land it, or move
it to the nearest open question above that holds everyone who needs it — on a merge or a
supersession, to the question it points to. Closing against a
decision still waiting in such a list, cite the list: the straw dogs waiting on the question come
due once every link of its answer is a home — never a question's list, a ticket or an RFC.

## Branching

**When** a question's shape hides parts whose expansion would change its answer; a split comes
back from an impact pass; or the person refutes a proposed answer by reshaping the question rather
than by choosing among its options. **Do** open each hidden part under it, with `depend` where one
cannot be asked before another; leave the parent open; call `at` on the first child that can be
worked. No answer lands on the parent, and none is put to the person as a proposal or a decision,
until its children close or are deferred with a default. How a kind
of question branches is the method's instrument; the moment is this one.

## Dropping

**When** a held question is not worth holding: its answer is entailed by what is settled and
nobody can say what one might have thought instead; or answering it costs more than it is worth;
or the person drops it. **Do** close it `pruned` with its reason, after moving out the open
children that stand alone and closing the rest; a prune that leaves an open child is refused.
A pruned question is kept, never deleted. *Moot* is another answer's doing, *deferred* keeps a
default; *pruned* says the question should not have been held.

## Records

**An entry** — one file in `docs/questions/`, named `<id>-<slug>.md`, the slug made by the
script from the question's words — so phrase a question short. Tier 2: read by the script, and by
a person through this skill. What removes one: it moves to `docs/questions/done/` with a wholly
closed subtree nothing open depends on, a deferred or suspect entry counting as open; it is never
deleted.

```md
# q-0090.0003 Which package manager do we use?

- **record of** what happened
- **part of** q-0090
- **depends on** q-0070, q-0080.0001
- **state** closed:decided, suspect
- **owner** [01-0011.0100](../tickets/01-0011.0100-the-open-questions-are-kept-by-a-mechanism.md)
- **answer** [the ADR](../adr/0004-scripts-run-on-the-standard-library-alone.md) — the user, 2026-09-28
- **realizes** A7 "The question store"
- **lean** the flat directory, for insertion cost
- **struck** 2, last 2026-10-02T19:40Z

A flat directory inserts in one write; nested folders were weighed and refused, since a question
moving between roots would move between folders.
```

**The body** follows the parts after one blank line: the question's argument — positions,
evidence, what was refuted — written by hand with the edit tools, never by the script, which keeps
it as it found it on every call. A line in it shaped like a part is not one.

**The decisions list** is the body's `## Decisions` section, up to the next `## ` heading: a
decision with nowhere to land yet is an item, `- ` or `N. `, and takes `→ <link>` to its home when
it lands. The script reads the list at `close` and in the check and never writes it; prose between
the items and a fenced block hold no decision.

**record of** opens the parts: what the entry is a record of — *what it intends to become* while
open, *what happened* once closed — so whoever writes its body meets the kind in context. The
script writes it from the state on every call, and the check holds the two equal; its earlier
name, `kind`, is reported.

Every other part but **state** is optional, and a closed entry must carry its **answer**. **struck** is
`<n>, last <YYYY-MM-DDTHH:MMZ>`, in UTC, written by the script alone, never by hand. **realizes**
is the trace link, kept as written and never resolved; a question without one carries its nearest
ancestor's, and the window never draws it. The state is
`open` or `closed:<kind>`, with `, suspect` after it at most. **The id is the place**: a root is
`q-NNNN`, a child its parent's id and one more position, `q-0090.0003`, the next after its
siblings. A
re-parent renames the moved question and everything under it — files, links, relations, session
lines, bare ids under `docs/` and every straw dog's binding — so an id seen earlier may be gone:
draw the window again. A reword changes the words and the file's name, never the id. *part
of* is the line the check holds the id against.

**The sessions folder** — `docs/questions/sessions.d/`, shared by all sessions, one file per
session named by its tag and holding its one row:
`<tag> running|ended <YYYY-MM-DDTHH:MMZ> <q-id>|- [<q-id>,… up to four]` — its tag, whether it
runs, when its line last changed, its current question or `-` before it has one, and its recent
ones; a row holding the date alone still reads, as that day's start. A store still holding the
single file `docs/questions/sessions` is read with it, and carried into the folder at its first
write. Tier 1 through the window and
the wake's read. What removes a row: kept by design — an ended row lets a later wake offer to
resume.

**A silent row ends at the next wake.** Every wake ends each other running row whose session
nothing has seen for three hours, and says nothing of it. A session is seen while its messages
reach a hook — the window drawn, or Cursor's prompt hook — or it writes its row; the next message
turns an ended row running again.
