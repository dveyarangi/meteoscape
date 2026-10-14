# maintain — holds documentation, implementation and records in agreement, and repairs the drift

- **instruction** `.agents/skills/maintain/SKILL.md` — the pass: scope, the four things, straw dogs, archiving, finish
- **state** installed
- **record of** what must always hold

## How it works

`/maintain` holds four things in agreement, per documentation-and-implementation pair a project
has: docs are derived work of the meta-rules and take their format; a record and the thing it is
of agree, repaired in the direction its kind gives — the thing to a record of *what must always
hold*, a record of *what exists* regenerated from the thing; live records are derived work of
their declared format; **every fact has one home**.
Its occasion is **drift** — a governing side that moved with no landing behind it, or a sum of
clean landings that no longer agrees. Agreement over a landed slice is verification's, at
`/verify`, and this mechanism does not repeat it.

It is **installed**. A tree without it still runs its ring, unmaintained; the parts table below is
what an installer adds and an uninstaller removes. It is reached from the ring in the entry file
and from `/verify` naming it. Nothing in the entry file is its part: the ring belongs to the loop,
and this mechanism sits on it. The harness mechanism places it in a tree with the rest of core;
removing it alone is declared below as a gap, not assumed away.

Its record is the marks — one row per mechanism per level, moved only by the closing step of a
maintenance, from which dueness is derived. A record is due when what it depends on moved, and a
mechanism has two dependences: at `parts` its doc is due when a part it owns moved since its mark
— the parts table's rows, whole files, a relied-on part being its owner's doc to watch; at
`output` its records are due when its own doc, rules file or skill moved, and its doc and skill
when the mechanism shape's did — every mechanism's doc and skill are the shape's outputs, read
against it one mechanism at a time in that mechanism's own row, the entry file governing none in
particular *(the user, 2026-10-11)*. `maintain.py
--check` derives that at every pass and never fails on it — being due is news, not a defect — and
`--mark` is the only writer; the format is the shelf beside the skill, `MARKS-FORMAT.md`. A due mechanism joins
whatever scope a pass declared, because a pass that closes one ticket would otherwise never reach
a mechanism doc. A mark fingerprints the surface as it stands when written, so what moved between
the re-check and the mark is cleared unread; marking is therefore the step that closes the
re-check. It fingerprints each file of the surface too, so a level falling due names what moved,
was added or went, and the re-check reads those rather than guessing *(the user, 2026-10-11)*.

In a recipient the mechanisms that came with core are maintained where core is made: the clock
leaves them out and a mark refuses them, and the origin's marks never ship.
A recipient's own mechanisms have no home yet, so its clock reads an empty set.
The due list is read at every pass and printed by the check; it is not announced, so a tree
where no pass runs is not told.

The ticket mechanism's rules on paired close and on its records, and the mechanism shape's rules
on records and re-checks, reach the body as installed blocks.

One rule sits in the body by hand inside a straw dog: a spec's agreements before archiving it,
which is `/spec`'s and waits for `/spec` to be declared.

The body names no other skill except `/align`. What is not this mechanism's is stated as what it
does not do — a landed slice is verified, not maintained — never as who does it instead; this
table is where the other party is named.

**Who decided each rule.** The body carries rules by ID and no attribution, because attribution
serves the maintainer at amend time, not the agent at execution; this doc carries it. A rule with
a name and date below is that person's to amend, through `/align`; the rest came with the selected
skills or with a pass under the repair policy, and a maintainer may amend them under
repair-and-report, recording the cause in the evidence.

| rule | decided by |
|---|---|
| A1, A2, A4 | the user, 2026-09-07; A1's three outcomes of a due pair, the user, 2026-10-11 |
| B4, F4, the marks' format | the user, 2026-09-27; B4's two levels and the format's `parts`, `output` and `repaired`, the user, 2026-10-11 |
| B1, D4 | the user, 2026-09-06 |
| C1 | the user, 2026-09-06 — eligibility is the maintainer's, never the script's |
| A3, B2, D3 | drafted into the process document 2026-09-05, never separately decided |
| B3 | a maintenance pass, 2026-09-07, from `TICKET-FORMAT` stating the duty unconditionally |
| C2 | the user, 2026-10-04 — whether a straw dog is due is the store's to say |
| C3 | the install RFC of 2026-09-06 |
| E1–E3 | `/denoise` as selected, 2026-09-05 |
| the mechanism shape's block, R1–R4 | the user, 2026-09-07, in the shape's rules file; installed here |
| the ticket mechanism's block, P1, P2, P3, P5 | in the ticket mechanism's rules file, where each rule carries its own authority; installed here |
| P4 | drafted into the process document 2026-09-05 as a spec rule; held here by hand for `/spec`, undeclared |

## Moments

| moment | instructed by | kind, and why |
|---|---|---|
| declaring a scope and running a pass over it | `.agents/skills/maintain/SKILL.md` | |
| re-checking derived work when what governs it moved — a doc against the meta-rules, an implementation against its doc, records against their format | `.agents/skills/maintain/SKILL.md` | |
| holding a landed slice to its governing docs, both ways | — | elsewhere — landing-time agreement is verification, `.agents/skills/verify/SKILL.md` |
| knowing a re-check is due | `.agents/skills/maintain/SKILL.md` | |
| marking a level re-checked | `.agents/skills/maintain/SKILL.md` | |
| rewriting a straw dog that is due, and retiring the block | `.agents/skills/maintain/SKILL.md` | |
| guessing where a straw dog nobody wrapped stands, and judging each guess | `.agents/scripts/gw/straw_dogs.py` | |
| cleaning prose and records to one home per fact | `.agents/skills/maintain/SKILL.md` | |
| closing a finished ticket with its RFC | `.agents/skills/maintain/SKILL.md` | |
| updating the header at close | `.agents/skills/maintain/SKILL.md` | |
| checking a mechanism's records against their declared format, the ticket records among them | `.agents/skills/maintain/SKILL.md` | |
| repairing mechanically, history included | — | elsewhere — a meta-rule, read where it lives, `.agents/skills/mechanism/SKILL.md` |
| disposing of a concern | — | elsewhere — a concern is an open question of the store, closed by a recorded kind that points to the ADR, architecture section or code that owns its answer, `.agents/skills/questions/SKILL.md` |
| checking links outside a close | — | not yet |
| cleaning inline comments in scope | — | elsewhere — verification applies the comment skill to landed work, `.agents/skills/verify/SKILL.md` |
| running the verification set the scope touched | `.agents/skills/maintain/SKILL.md` | |
| installing this mechanism into a tree, with the rest of core | `.agents/scripts/gw/harness.py` | |
| removing this mechanism from a tree | — | not yet |
| picking up a dream | — | unowned by design — the entry file says *may*, a permission and not a duty, while the dream skill is experimental |

## Install adds, uninstall removes

| part | where |
|---|---|
| instruction file | `.agents/skills/maintain/SKILL.md` |
| format shelf | `.agents/skills/maintain/MARKS-FORMAT.md` |
| this doc | `.agents/mechanisms/maintain/maintain.md` |
| its rules file | `.agents/mechanisms/maintain/maintain.rules.md` |
| the listing script | `.agents/scripts/gw/straw_dogs.py` |
| its tests | `.agents/scripts/gw/test/test_straw_dogs.py` |
| the clock | `.agents/scripts/gw/maintain.py` |
| its tests | `.agents/scripts/gw/test/test_maintain.py` |

## Relies on, and does not own

| part | where | owner |
|---|---|---|
| the mover | `.agents/scripts/gw/move_doc.py` | `ticket` |
| the mover's tests | `.agents/scripts/gw/test/test_paired_close.py` | `ticket` |
| the mover's tests | `.agents/scripts/gw/test/test_refusals.py` | `ticket` |
| the mover's tests | `.agents/scripts/gw/test/test_citations.py` | `ticket` |
| the mover's tests | `.agents/scripts/gw/test/test_command_line.py` | `ticket` |
| the mover's tests | `.agents/scripts/gw/test/test_failure_contract.py` | `ticket` |
| the ticket maintainer | `.agents/scripts/gw/tickets.py` | `ticket` |
| whether a straw dog is due, read by the listing | `.agents/scripts/gw/questions.py` | `questions` |
| citation reader | `.agents/scripts/gw/docs_corpus.py` | `mechanism-shape`, the one that cannot leave |
| test harness | `.agents/scripts/gw/test/repository.py` | `mechanism-shape` |
| the shape check | `.agents/scripts/gw/mechanisms.py` | `mechanism-shape` |
| the installer | `.agents/scripts/gw/inject_rules.py` | `mechanism-shape` |
| the method's vocabulary | `.agents/glossary.md` | nobody removable |

## What it produces, and who reads it

- **The pass's report** — *what happened* — read by the person who asked for the pass, and by `/conclude` when
  the session is recorded.
- **Repaired files** — *its format's* — read by whoever reads them next; the report names each repair and the
  rule it restored.
- **Moved records** — *its format's* — read through their repaired citations; the mover reports what it
  rewrote and what it could not.
- **A retired straw dog's replacement sentence** — *what must always hold* — read where the block was.
- **The listing script's guesses** — *what exists* — read by the maintainer at T3 over a declared scope, and by
  `/verify` over the files a slice touched; never by a check, since a guess is judged and never
  fails a run.
- **The rules file** — *what must always hold* — one rule, M1, targeting `/mechanism`'s *Incept*, read by the installer
  alone and installed there as this mechanism's block.
- **The marks**, `docs/mechanisms/maintenance.md` — *what exists* — read by the clock at every pass. The
  instance's record: a recipient keeps its own, and the origin's never ships.
- **The clock's report** — *what exists* — read by `/maintain` at the start of every pass, a due
  level naming the files that moved, were added or went since its mark, which the re-check reads;
  and by `/verify` through the verification set, where only an unreadable mark or surface fails it.

Nothing else; no index.

## Not yet at the shape

**One rule held by hand.** P4 is `/spec`'s, and `/spec` is undeclared, so the body carries it
inside a straw dog bound to the question of what `/spec` owns.

**Two `not yet` rows**, each bound to an open question.

## What retires this

A tree in which every one of the four agreements is held by a script in the verification set,
leaving a pass no judgment to apply. Until then this is the judgment half and the scripts are its
parts.

## What would show it working, graded by someone who did not build it

Two graders, two questions, pre-registered at the align that declared this mechanism.

**The user** grades the shape amendments this declaration forced — installed text replacing
injected pointers, a sentence about another mechanism being that mechanism's, and the record
obligation moving from *none by property* to *not yet*: did the shape change because
`/maintain` did not fit it, or was this declaration bent to fit the shape? A declaration
hand-fixed until the check went quiet reads identically to success.

**The session that declares the ticket mechanism** grades this
declaration as the first to lean on it: it takes the mover and the citation reader as its own,
installs the paired-close block into the body, and retires the two `embedded` rows. Did those
land against this doc as written, or did the doc have to be rewritten to receive them? **Graded
2026-09-09**; the answer is in the evidence.
