# questions — every open question of the tree is kept in one store, with each session's current question known

- **instruction** `.agents/skills/questions/SKILL.md` — the formats, the calls, and closing, branching and dropping
- **state** installed
- **record of** what must always hold

## How it works

A discussion opens a question, splits it, dives into one branch and moves on; what was left open
above is carried in nobody's record. The store writes every open question down with its relations
and its state, and every running session's current question beside them, so a question left behind
is found again and an answer landed above an unexpanded shape is caught.

**The unit is the open question.** One entry per question, with two relations kept apart — *part
of*, a decomposition, and *depends on*, cannot be asked until — and a closure by recorded kind.
Level is depth in that structure, derived and never written; a shift in a conversation is a message
attaching to a different question. A ticket is a method's goal and stays the method's; the store is
core's substrate, beneath whatever method a tree runs.

**Three roots from the start.** A store holding no entry, at a first install or an update, is
seeded with three root questions and nothing else — no parts under them, no links between them:
the purpose, the structure, and the space of neighbours, history and evolution the project moves
in, worded on the shelf [`STORE-ARRIVAL.md`](../../skills/questions/STORE-ARRIVAL.md). Each is where a person's
judgement is spent: choosing the goal from the space of ideas; correcting the model where it is
ineffective, wasteful or destructive in the structure; and seeing what the model misses in the
landscape, which can move both the others. *What is this project?* is what the three answer
together, never an entry. How one root's answers bear on another's is the project's own, so
nothing fixes it.

**The turn.** Before drafting, the agent reads the window — the path from the root to its session's
current question, the children along it, the root's other open questions, the other roots, the
other sessions — and says what the turn is: on a question, placed on the lowest one that contains
the message and never on one that only resembles it, nor on a far one that holds it only as it
holds everything beneath it, where the parent is missing and is opened; a process, the agent carrying out what it
knows how to do, which is placed nowhere; uncharted, a question whose home the person settles; or
banter, a message that asks nothing of the work, answered by a reply that writes and settles
nothing.
What it places it writes by calling the script, one call per event, each
validated and written whole; the script gives a new question its id, nested under its parent's,
and a re-parent renames the subtree that moves, so an id always says where its question sits; a
reword gives an open question new words under the id it has, since the same question means the
same answers and never the same wording. The
window prints position,
never relevance: the one judgement of the turn is the agent's. The rule placing a message is
installed at tier 1, since its occasion is every turn.

**What keeps coming back rises.** A question reached twelve hours or more after it was opened or
last struck is struck, counted by the script from the `at` call with no judgement of the agent's;
the count shows on its window line and ranks it where a session starts. The time gap tells a
return from a stay without telling sessions apart, so a resumed conversation's new id changes
nothing; a question worked for days strikes too, so the count ranks time spent as well as returns.

**Delivery.** Where a host's hooks can add context, the window and the session's registration come
from them, under the host's own session id; the rule stays the floor every host reads. Claude Code
and Codex take context at session start and before every message; Cursor only at session start, so
its agent draws the window by the rule, and its prompt hook only marks the session seen. A window stays in the conversation once drawn, so the next
is drawn only when the session's position or an entry moved, and whole again after a compaction.
Either form ends with the counters — the tree's open tickets, open questions and straw dogs, each
with what came and went since the session's previous window, matched by name — since a ticket or
a straw dog moves while no entry does; the names are remembered outside the tree beside the
window's own memory, which a compaction empties and they outlive.
A conversation resumed under a new session id is the session it was: where the host names the
conversation more steadily than the session — the Claude Code desktop app does, in every process
it starts — the session is registered under that name, so a resume finds it already registered.

**Principles**, behind the rules and never installed:

- **Depth is the instrument against breadth**: when a question's open children outgrow what the
  window can show, find the question they jointly serve and insert it above them.
- **A skipped question is found by impasse**, or by the method's plan, never by walking
  presuppositions upward.
- **Decide at the level asked**; go down to look, and return.
- **Descend or hold is a value question**: resolve the higher question first only when its answer
  could flip this one and is cheaper to get than the flip would cost; otherwise decide under it,
  record the dependency, and the answer is born suspect.
- **The same question means the same answers**, never the same wording.
- **A question is held when it is worth its cost**, when someone can say what one might have
  thought instead, and when a clairvoyant could answer it without judgement.

**Three levels**, each usable without the next: the store, where the agent judges and nobody watches
it; a judge outside the generator, which catches the agent's own descents; the hook, after which
nothing is left to remember. The window's half of the hook lands with the store; the write after
the turn waits on the judge. Whether a question is load-bearing, or hides parts, is the judge's to
judge, since the agent fails at both; without a judge the instruction stands where the agent reads
it, and the agent tries.

**Rights.** An agent's rights over the store come from the role it starts with, which also grants
its permissions and its skill set. The harness has one role, the HITL session, driven by a person
and holding every right, so the store checks none. What a role is, and which mechanism keeps
roles, is an open question of the store.

## Moments

| moment | instructed by | kind, and why |
|---|---|---|
| placing a message before answering it | `AGENTS.md` | |
| closing, branching or dropping a question | `.agents/skills/questions/SKILL.md` | |
| re-parenting, merging or pruning by hand | `.agents/skills/questions/SKILL.md` | |
| drawing the window | `.agents/scripts/gw/questions.py` | |
| registering a session and delivering its window through a host's hook | `.agents/scripts/gw/questions.py` | |
| writing entries and the position from a call | `.agents/scripts/gw/questions.py` | |
| writing a question's argument, the body after its parts, by hand | `.agents/skills/questions/SKILL.md` | |
| landing a decision an align makes, and holding one with nowhere to land yet | `.agents/skills/align/SKILL.md` | |
| checking the store | `.agents/scripts/gw/questions.py` | |
| reading where the work stands when a session wakes | `.agents/skills/recall/SKILL.md` | |
| writing the session's leans and ending it | `.agents/skills/conclude/SKILL.md` | |
| archiving the subtree a closure finishes | `.agents/scripts/gw/questions.py` | |
| sweeping a wholly closed subtree a closure left behind | `.agents/skills/maintain/SKILL.md` | |
| installing this mechanism into a tree, with the rest of core | `.agents/scripts/gw/harness.py` | |
| seeding the roots of a store holding no entry, called by the install | `.agents/scripts/gw/questions.py` | |
| judging a message outside the agent | — | not yet |
| detecting a shape that hides children | — | not yet |
| holding a ticket's open questions under the question it answers | `.agents/skills/ticket/SKILL.md` | |
| saying which straw dogs are due, and carrying their bindings through a rename | `.agents/scripts/gw/questions.py` | |
| carrying the hook wiring into a recipient tree | `.agents/scripts/gw/harness.py` | |
| removing this mechanism from a tree | — | not yet |

## Install adds, uninstall removes

| part | where |
|---|---|
| instruction file | `.agents/skills/questions/SKILL.md` |
| this doc | `.agents/mechanisms/questions/questions.md` |
| the shelf of a fresh store's roots | `.agents/skills/questions/STORE-ARRIVAL.md` |
| its rules file | `.agents/mechanisms/questions/questions.rules.md` |
| the store's script | `.agents/scripts/gw/questions.py` |
| its tests | `.agents/scripts/gw/test/test_questions.py` |
| the shelf of Claude Code's hook wiring | `.agents/skills/questions/hooks/.claude/settings.json` |
| the shelf of Codex's hook wiring | `.agents/skills/questions/hooks/.codex/hooks.json` |
| the shelf of Cursor's hook wiring | `.agents/skills/questions/hooks/.cursor/hooks.json` |
| the hooks' wrapper, launched by a Git alias | `.agents/scripts/gw/hook.sh` |
| its line endings, kept LF in every clone | `.agents/.gitattributes` |

## Relies on, and does not own

| part | where | owner |
|---|---|---|
| the mover | `.agents/scripts/gw/move_doc.py` | `ticket` |
| citation reader | `.agents/scripts/gw/docs_corpus.py` | `mechanism-shape` |
| test harness | `.agents/scripts/gw/test/repository.py` | `mechanism-shape` |
| the shape check | `.agents/scripts/gw/mechanisms.py` | `mechanism-shape` |
| the installer | `.agents/scripts/gw/inject_rules.py` | `mechanism-shape` |
| the interpreter record the wrapper reads, made by the link step | `.agents/scripts/gw/harness.py` | `harness` |
| the method's vocabulary | `.agents/glossary.md` | nobody removable |

## What it produces, and who reads it

- **A fresh store's roots** — *what it intends to become* — read by the first session's `/recall`
  and every window after, before the project has written a question of its own; worded on the
  shelf, written by the script, the project's from then on.
- **The entries** — *what it intends to become, what happened once closed* — read by the script at every window, wake, declaration and check, by a
  person through `--tree`, and by the product mechanism's script, which asks `realizes` for each
  question's trace link — a part the store keeps as written and never resolves.
- **The sessions folder** — *what exists* — one file per session, named by its tag and holding its
  line, so no session's write meets another's; read by the script for every window and wake, so
  each session sees where the others stand; a wake ends the sessions gone silent.
- **The window** — *what exists* — read by the agent before every message, from the host's hook or the rule.
- **The wake's read** — *what exists* — read by the agent at session start, from the hook or `/recall`; it names
  the straw dogs due, whose text `/maintain` rewrites.
- **The fingerprint of each session's last window**, outside the tree — *what exists* — read by the script alone,
  to tell whether anything moved; a compaction clears it.
- **The hook wiring** — *what must always hold* — read by the installer, which merges each shelf
  file into the host file at its own path beside the project's hooks, and by each host from there.
- **The hook's answers** — *what exists* — read by the host, which places them in the agent's context.
- **The check's report** — *what exists* — read by `/maintain` at its pass and by `/verify` through the
  verification set.
- **The rules file** — *what must always hold* — read by the installer alone. Its blocks sit in the
  entry file, `/recall`, `/conclude`, `/maintain` and `/align`.

Nothing else; the tree is rendered on request and never committed.

## Not yet at the shape

**Four `not yet` rows**, each bound to an open question.

**The sessions folder** is one folder in the working tree, and that is how sessions see each other;
sessions that do not share the directory do not see each other.

**The store's paths** are painted doors held by hand in the shape check.

## What retires this

If it works, nothing: it is the core other things are built on. Two conditions would show that it
does not work as a substrate. A host that comes to keep a conversation's question structure itself
— position, tree, and the moments with the same outputs — in which case the store is the host's.
Or its own measure: over a stated span, the calls and suspect marks led to no amendment
the session would not have made anyway, counted as judged shifts, suspect marks cleared and
reopenings refused against the turns and tokens spent declaring — it costs and does not save. The
store becoming the ticketing is not a retirement.

## What would show it working, graded by someone who did not build it

Three yes-or-no tests, pre-registered at the align that incepted it:

1. Drift deliberately in a chat: does the turn's `at` call name the shift in the same turn?
2. Break a session at a deep question: does the next wake open at it, with its path?
3. Change a parent's answer: is every child under it reported suspect before anyone reads them?

The third is what the mechanism was raised for. And per host, recorded as observed or not: does a
live session register under the host's own id through its hook, and, in Claude Code and Codex, is
the window in context before the agent drafts, with no call of its own?
