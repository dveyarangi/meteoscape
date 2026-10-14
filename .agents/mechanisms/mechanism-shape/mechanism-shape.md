# mechanism-shape — what counts as a mechanism, what one is made of, and where each part lives

- **instruction** `.agents/skills/mechanism/SKILL.md` — the shape: membership, the three homes, moments, injection, records, incept, amend and retire
- **state** always on
- **record of** what must always hold

## How it works

A mechanism is part of how the work gets done, and it owes an account of itself: one instruction
file, a doc saying why that instruction is what it is, and evidence saying why the doc is. This
mechanism is that rule, and it is declared by its own shape — the first application, and the one
that would be worthless if the shape could not carry it.

The three homes cut on **when the thing is read** — session start, the work a rule governs, or
changing the mechanism itself. There is no fourth home because there is no fourth occasion, and any
other cut — by subject, by author, by importance — puts a rule where its reader is not.

**A format shelf declares form; why a form is what it is belongs here.** The shelf is read while
writing to the form, and a reason at that moment is text between the reader and the thing they
came for. The cut is the same one the three homes make, applied inside a mechanism's own parts.

**A mechanism declares its own records** because no other mechanism can say when someone else's
record is finished. A maintainer's duty to archive finished records is a duty to read that
declaration, so a record that carries none is a duty that cannot be discharged rather than a duty
nobody has.

**One mechanism per skill**, so that naming a skill names its owner. A skill with two owners would
make every reference ambiguous at the moment it is needed most, and a moment instructed
`elsewhere` names the skill, which resolves against a file rather than against a declaration that
may not exist yet. The converse is not required: a mechanism may own several skills when each acts
on a record it declares — the start and the end of one record are two acts of one mechanism, and
splitting them across two mechanisms to keep one skill each cuts a lifecycle in half. The record
is the brake: a skill acting on none of the mechanism's records is not its own.

**Mechanical by construction**, because a mechanism whose parts a script cannot enumerate cannot be
checked, and an unchecked declaration is exactly the label this shape exists to prevent.

It is **always on**. Nothing can install or uninstall the thing that defines what installing
means, so it has no lifecycle scripts, and the parts table below is what a person moving this
between trees takes rather than what an installer adds.

The check is what makes the declaration a claim rather than a label. It rules on form: whether
every named part is where the doc says, whether each moment carries an instruction or a stated
kind of absence, whether the referents resolve. Whether a moment *should* exist, and whether an
absence is honestly classified, are judgements it records and never makes.

## Moments

| moment | instructed by | kind, and why |
|---|---|---|
| deciding whether a thing is a mechanism | `.agents/skills/mechanism/SKILL.md` | |
| incepting one | `.agents/skills/mechanism/SKILL.md` | |
| telling an inceptor what to hand `/maintain` | `.agents/skills/mechanism/SKILL.md` | |
| amending a declared one, editing a skill that is an instruction file included | `.agents/skills/mechanism/SKILL.md` | |
| retiring a declared one | `.agents/skills/mechanism/SKILL.md` | |
| installing a declared mechanism into a tree, with the rest of core | `.agents/scripts/gw/harness.py` | |
| removing one declared mechanism from a tree | — | not yet |
| checking that a declaration is true | `.agents/scripts/gw/mechanisms.py` | |
| installing a mechanism's rules into skills, its own included, and the project's local file after every mechanism's | `.agents/scripts/gw/inject_rules.py` | |
| retracting them | `.agents/scripts/gw/inject_rules.py` | |
| reporting a retired tag left in core | `.agents/scripts/gw/mechanisms.py` | |
| writing a mechanism's rule where a session reads it, the entry file included, at `/align` or here | `.agents/skills/mechanism/SKILL.md` | |
| re-checking a mechanism when what governs it has moved | — | elsewhere — re-checking derived work against a changed source is maintenance, `.agents/skills/maintain/SKILL.md` |
| writing or changing a skill's text | — | elsewhere — a sibling mechanism's subject, and both apply when a skill is an instruction file, `.agents/skills/skill-up/SKILL.md` |
| recording that an installed skill belongs to no mechanism | `.agents/skills/skill-up/SKILL.md` | |
| asking whether every installed skill is claimed, and every part a mechanism owns names it | `.agents/scripts/gw/mechanisms.py` | |
| holding core to citing only what its mechanisms declare | `.agents/scripts/gw/mechanisms.py` | |
| finding a mechanism's doc, or asking what is declared at all | — | unowned by design — the directory is a routing table and the index renders it on request; looking something up needs no rule |

## Install adds, uninstall removes

| part | where |
|---|---|
| instruction file | `.agents/skills/mechanism/SKILL.md` |
| format shelf | `.agents/skills/mechanism/MECHANISM-FORMAT.md` |
| this doc | `.agents/mechanisms/mechanism-shape/mechanism-shape.md` |
| its rules file | `.agents/mechanisms/mechanism-shape/mechanism-shape.rules.md` |
| the check | `.agents/scripts/gw/mechanisms.py` |
| the check's tests | `.agents/scripts/gw/test/test_mechanisms.py` |
| the installer | `.agents/scripts/gw/inject_rules.py` |
| the installer's tests | `.agents/scripts/gw/test/test_inject_rules.py` |
| the test harness's tests | `.agents/scripts/gw/test/test_repository.py` |
| citation reader | `.agents/scripts/gw/docs_corpus.py` |
| test harness | `.agents/scripts/gw/test/repository.py` |

The last two are shared by every script in the tree and claimed here because this mechanism is
the one that cannot leave: where a shared part's ownership bites, the claimant is the always-on
mechanism, so no uninstall can remove what another mechanism needs *(the user, 2026-09-08,
applying the spec's ownership decision)*.

## Relies on, and does not own

| part | where | owner |
|---|---|---|
| the method's vocabulary | `.agents/glossary.md` | nobody removable |
| a `not yet`'s question and whether it is due, read by the check | `.agents/scripts/gw/questions.py` | `questions` |

## What it produces, and who reads it

- **This declaration** — *what must always hold* — read by whoever amends a mechanism or debugs one, and parsed by the check
  on every `/verify`.
- **The evidence**, one file per mechanism under `docs/mechanisms/`, named by the slug — *what happened* — read at amend time,
  by whoever is about to change this doc and needs to know what was already refuted. Never read
  during ordinary work, which is why it lives outside `.agents/` and is excluded from re-checks.
- **`--check`'s report** — *what exists* — read by `/verify` through the verification set, and by anyone who runs
  it. Its exit status is what the set consumes; its JSON is for the person reading a failure.
  Its `core cites` key lists every path under `docs/` a core file names and where it stands —
  a painted door, skipped inside an instance-owned block, or a leak — read by whoever ports
  core: an exclusion nobody can see is the review the check replaces, so all three are shown
  and never a total.
- **`--index`'s render** — *what exists* — read on request by someone asking what is declared. **Nothing runs it
  unasked**, and nothing consumes its output: it exists so the register never becomes a file, and
  a register nobody asks for is a register nobody needed.

- **Its rules file** — *what must always hold* — `mechanism-shape.rules.md`, read by the installer alone, and by whoever
  amends a rule of the shape that other skills read. Its block is installed in `/maintain`, in
  `/align`, in this mechanism's own skill, which reads R1 and R4 at incept and R5 when a rule
  is written, and — R7, the local file — in the entry file, where every session reads where a
  project's answers live, and in `/verify`, where the check that holds a local block to its
  source is run and a drifted one is routed to the file rather than edited in place. **A rule two occasions read is installed everywhere it is read, the owner's own
  skill included** *(the user, 2026-09-20)*: the rules file is read by nobody at session time and
  no body restates a rule, so installation is the only path such a rule has into its owner's body.
  The alternative — authored in the owner, installed elsewhere — puts one rule in two files and
  leaves the check nothing to compare the authored copy against.
- **The installer's `--check` report** — *what exists* — read by `/verify` through the verification set, and by
  anyone who runs it. Its exit status is what the set consumes; a block absent, drifted or
  owned by nothing is what it fails on, and a local block that is not last in its file, or an
  override naming a rule that is not installed where the override is.

- **A part's claim** — *what it intends to become, what must always hold once it names a mechanism
  or says unowned by design* — the `Mechanism:` line a file an agent edits opens
  with: a skill a declaration names, and every script, test and hook a mechanism owns, naming its
  slug, so the agent meets the doc that governs the file where it works; a skill none names, `not
  yet` as a straw dog at its authored home. Written by whoever adds the file, through R6; read by
  `--check` on every `/verify`, held to the parts tables both ways. Not a record of this
  mechanism: it is the file's own line, and no file lists them *(the user, 2026-09-20; every part
  that names its mechanism, 2026-10-11)*.

Nothing else is emitted. It writes no records beyond the mechanism directories that are its
records.

## Not yet at the shape

**Nothing runs the check unasked.** It runs when a person types it, or when the project's
verification set is run, which happens at `/verify`. That is better than remembering and weaker
than a mechanism that speaks at wake; this tree has no hook to speak from. A run that stays quiet
because nobody started it is indistinguishable from one that passed.

**Absence is not clearance.** A clean run means nothing was caught. It never means the tree obeys.

**Nothing refuses to retract the shape's own block from its own skill.** R1 and R4 are installed
into this mechanism's instruction file by the same tool that retracts them, and an always-on
mechanism cannot be retired. The shape's block absent from `/mechanism` under `--check` is the
signal that the always-on mechanism has lost what it installed into itself, and the check is
what says it happened.

**Six declared mechanisms are still thin evidence for a shape.** The first three each forced
amendments to it, the fourth passed its check unedited and sharpened one word — what each one
forced is in the evidence; the fifth and sixth left no account there — and
the rest of the corpus meets it at once.

## What retires this

A tree that can derive a mechanism's parts and moments from itself, making a doc that asserts them
a second home for what the code already says. Until then, declaration is the only way the claim
exists at all. Retirement removes the parts above and this directory; its entry point is its
skill's description, so retracting the mechanism takes it with the skill.

## What would show it working, graded by someone who did not build it

The next mechanism declared — `/maintain` — either passes
this check unedited, or the check has to change to admit it. Which of those happens is the shape's
first real test, and the session that runs it is not this one.

A declaration hand-fixed until the check went quiet is this mechanism failing, and reads
identically to success in the check's own output. The grader is whoever declares the second
mechanism: they answer whether the shape fitted something it was not written against, or whether
the second subject had to be bent to fit the first.
