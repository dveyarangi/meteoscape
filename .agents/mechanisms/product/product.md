# product — keeps one account of what the project is for, and reads from the work how much of it is built

- **instruction** `.agents/skills/product/SKILL.md` — the act: keeping the product document, seeing each answer's coverage and the queue beside it
- **state** installed
- **record of** what must always hold

## How it works

A project's **product document** says what the project is for: the pains it relieves, the goals
it must not lose, the causes, and the answers — each answer a row with an id never renumbered and
a name. It is the home of the decisions taken under the purpose root, as the architecture and the
ADRs are the structure root's.

**The account is linked to the work through the question store, never through tickets.** A
question that builds an answer carries a trace link to it, by id and name; its sub-questions carry
it by trace propagation. The store keeps the link as written and never resolves it, so the
development method knows nothing of the product. An answer's coverage — absent, in progress,
present — is read from the questions that realize it, never written; the maintainer script renders
it on request, and the document holds no status of its own.

**The maintainer holds the document and the store to each other.** It finds the purpose root and
the structure root by their seeded words. What is broken fails the check: a document with no
answers heading, not in the format at all; an answer with no id or
name, an id written twice, a link naming no answer or quoting a name its answer no longer has, an
undecided row bound to nothing or to a question outside the purpose root. What is missing is
reported and never fails it: an open structure question with no link and not derived — an orphan
—, a decided answer nothing realizes, an open purpose question no row names. A tree with no
product document has nothing to check and passes.

**A decided purpose question is allocated in one step.** Its answer lands as a row — the row that
waited on it, or a new one — the question closes against the row, and the question of how to build
it opens in the structure root's branch, under the question it belongs to, with its trace link. A
question opened right under the structure root states its link at once, since it has no ancestor to
carry one; one that forgets is an orphan at the next check, never refused. Building that shows an
answer or its causes must change opens a purpose question like any other, and its decision is
allocated the same way.

It is **installed**. It ships with core like every mechanism,
since a project cannot yet take one alone. Its rules carry no condition: a tree that has
the mechanism keeps the document. **An install or an update writes it where none is**, empty, in
the words of its arrival shelf, by this mechanism's script — the third record written when absent,
after the delivery status and the store's roots. From its first line it is the project's: one
already there, in the format or not, is left, and the install names one that is not, which the
check fails.

**Who decided each rule.**

| rule | decided by |
|---|---|
| the document is the purpose root's home, linked to the work through the store | the user, 2026-10-12/13 |
| a trace link names an answer by id and name | the user, 2026-10-13 |
| only open and decided questions realize | settled at the plan, 2026-10-13 |
| U1 — the document is checked by `product.py` | the user, 2026-10-13, owed to `/maintain`'s M1 |
| one mechanism tells the account to every reader, shipped with core | the user, 2026-10-13 |
| U2 — a decided purpose question is allocated in one step, its building question opened under the question it belongs to | the user, 2026-10-13 and 2026-10-14 |
| U3 — a question opened right under the structure root states its link | the user, 2026-10-13 |
| the rules carry no condition: installed, the mechanism keeps the document | the user, 2026-10-14 |
| the install writes the empty document where none is, and leaves and names one in another form, which the check fails | the user, 2026-10-14 |

## Moments

| moment | instructed by | kind, and why |
|---|---|---|
| keeping the product document | `.agents/skills/product/SKILL.md` | |
| writing the document to its shape | `.agents/skills/product/PRODUCT-FORMAT.md` | |
| seeing each answer's coverage | `.agents/skills/product/SKILL.md` | |
| seeing, beside the queue, what each item realizes and which answers are left out | `.agents/skills/product/SKILL.md` | |
| checking the document's form | `.agents/scripts/gw/product.py` | |
| checking the document in a maintenance pass | `.agents/skills/maintain/SKILL.md` | |
| a purpose decision landing as an answer, its building question opened with a trace link | `.agents/skills/align/SKILL.md` | |
| a question opened right under the structure root stating its trace link | `.agents/skills/questions/SKILL.md` | |
| the root README told from the document | — | not yet |
| a release note's product half gathered from the coverage that moved | — | not yet |
| installing this mechanism into a tree, with the rest of core | `.agents/scripts/gw/harness.py` | |
| an install into a tree with no product document writing an empty one in the format | `.agents/scripts/gw/product.py` | |
| wording the empty document an install writes | `.agents/skills/product/PRODUCT-ARRIVAL.md` | |
| an install meeting a product document in another form: left as the project's and reported, and the check saying it is not in the format | `.agents/scripts/gw/harness.py` | |
| a project's existing account of what it is for brought into the format, by the person and the agent | — | not yet |
| removing this mechanism from a tree | — | not yet |

## Install adds, uninstall removes

| part | where |
|---|---|
| instruction file | `.agents/skills/product/SKILL.md` |
| format shelf | `.agents/skills/product/PRODUCT-FORMAT.md` |
| arrival shelf | `.agents/skills/product/PRODUCT-ARRIVAL.md` |
| this doc | `.agents/mechanisms/product/product.md` |
| its rules file | `.agents/mechanisms/product/product.rules.md` |
| the maintainer | `.agents/scripts/gw/product.py` |
| the maintainer's tests | `.agents/scripts/gw/test/test_product.py` |

## Relies on, and does not own

| part | where | owner |
|---|---|---|
| the trace link and what a question realizes | `.agents/scripts/gw/questions.py` → "def realizes(" | `questions` |
| test harness | `.agents/scripts/gw/test/repository.py` | `mechanism-shape` |
| the installer | `.agents/scripts/gw/inject_rules.py` | `mechanism-shape` |
| the pass that checks the document | `.agents/skills/maintain/SKILL.md` | `maintain` |
| the heading in `/align` where U2 is installed | `.agents/skills/align/SKILL.md` → "### Land resolutions as they are made" | `/align`'s own, its mechanism not yet |
| the heading in the questions skill where U3 is installed | `.agents/skills/questions/SKILL.md` → "## A raised question" | `questions` |
| the method's vocabulary | `.agents/glossary.md` | nobody removable |

## What it produces, and who reads it

- **The product document** — *what must always hold* — read by the person deciding what the
  project is for, and by whoever opens a building question for an answer.
- **The coverage rendering** — *what exists* — read by the person ordering the work, on request;
  never committed.
- **The queue rendering** — *what exists* — what each live ticket realizes, read through the
  store's owner part and the trace link, and the answers left out under each pain and goal; read
  by the person ordering the work, on request, never written into the queue.
- **The maintainer's report** — *what exists* — read by `/maintain` under U1. Its exit status is
  the verdict; its JSON is for the person reading a failure. It writes nothing.
- **The rules file** — *what must always hold* — read by the installer alone, and by whoever amends
  a rule of this mechanism that another skill reads. Its blocks sit in `/maintain`, `/align` and
  the questions skill.

Nothing else; no index.

## Not yet at the shape

**Four `not yet` rows of its own**, each bound to an open question: the README, the release note,
removal, and bringing a project's existing account into the format.

## What retires this

A project that keeps no account of what it is for: then no answer exists to realize, and coverage
reads nothing.

## What would show it working, graded by someone who did not build it

Pre-registered 2026-10-13. **The session that brings this tree's product document onto the
mechanism** grades it: did the format and the coverage rendering let it number the answers, link
the building questions and read each answer's coverage, without reading the history the format was
designed in? Each time it had to go back to that history for something the format or the skill
should have said is a miss, named in the evidence.
