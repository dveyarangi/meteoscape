---
name: mechanism
description: >-
  Method is mechanism work: use before changing how the work is done here — a
  skill, a check, a record, the loop itself — before building or amending a
  mechanism, and before changing a rule inside an `<installed>` block, whose
  home is its mechanism's rules file. Not for what the project produces.
---

Mechanism: mechanism-shape

# Build and amend mechanisms

The only home of the shape. A rule carrying a name and date is that person's to amend.

## Is it a mechanism

A mechanism is part of **how the work gets done**. What the project produces is not one,
however much depends on it.

Test: does other work rely on this as a source of instruction or behavior *about how
to work*? Then it is a mechanism and owes a declaration.

- A system, never a file. One spans skills, scripts, records, and rules injected into
  skills it did not write.
- **A skill has one mechanism** *(the user, 2026-09-06)*. A mechanism may own several,
  each the act at one of its moments over a record it declares; a skill that acts on no
  record of the mechanism is not its own *(loosened, the user, 2026-10-10)*. Rules it
  needs in a skill it does not own are installed as text from its rules file, and no body
  restates one *(the user, 2026-09-07)*.
- Writing an entry into a record is not mechanism work. It belongs to the skill that
  owns the entry.

## Three homes, and the chain

| home | holds | reaches a session |
|---|---|---|
| `AGENTS.md` | meta-principles, and a mechanism's rules only as installed blocks | at start, every session |
| `.agents/skills/<name>/` | the act, and every rule read *in the work it governs* | when the skill is invoked |
| `.agents/mechanisms/<slug>/` | why the instruction is what it is: parts, moments, and the mechanism's rules in their single home | when installing, amending or debugging |

The cut is **when is this read**. There is no fourth home. What a skill's act needs — a call, a
refusal and what to do at it, a script's name — is instruction and stays in the skill; the doc
takes only what informs.

> The doc is the instruction's *why*. The evidence is the doc's *why*.
> *(the user, 2026-09-06)*

- Doc and instruction file are never the same file.
- One evidence per mechanism, belonging to its doc. It lives **outside `.agents/`**, under
  `docs/mechanisms/`, named by the slug *(the user, 2026-09-06)* — it cites records that
  cannot travel, so the doc never names it; the shelf declares the record.
- A skill's `EVIDENCE.md` predating its declaration is an unsorted mixture: doc
  material to the doc, the doc's own why to the evidence.

Working parts stay where the harness needs them — skills, scripts, tests. Directory,
doc sections and what a script parses are
[MECHANISM-FORMAT.md](./MECHANISM-FORMAT.md)'s; restate none of it here.

## Moments

A moment is an occasion at which a person acts on the mechanism. Every one carries an
instruction or a stated kind of absence, and either way a clause saying why.

| kind | means | carries |
|---|---|---|
| `elsewhere` | instructed, by another mechanism | the instruction file that does it |
| `embedded` | instructed, from the wrong home | where the instruction sits |
| `unowned by design` | no rule warranted | its reason, nothing else |
| `not yet` | a genuine gap | the open question it waits on, as a straw dog's binding |

There is no *none needed*: if nobody acts, it is not a moment. The verdict is per moment,
never per mechanism.

## Rules, injection and retraction

A rule lives in one file — `<slug>.rules.md`, in the mechanism's own directory. Nothing
reads it at session time: a generic core installer, never a per-mechanism one, writes
its rules into the targets as delimited and visibly owned blocks, and that is the only
form in which they reach anyone. A copy in a target is **installed, never authored**.

Author a rule in the skill's body when only that skill's act reads it. Put a rule that two
occasions read in the rules file and install it everywhere it is read, the owner's own skill
included *(the user, 2026-09-20)*.

- Removable as written: retraction leaves the target byte-identical.
- **No default mode.** A bare invocation refuses.
- **Refuse rather than guess** — missing target, missing anchor, block present and differing.
  A hand-edited block is drift to report, not a second opinion.
- A rules file's block is installed in every target it names, or the check fails.

The installer is `inject_rules.py`: `<slug> --install`, with `--overwrite` when the source has
moved, which also takes the source's block out of a file it no longer names; `<slug> --retract`; `--check` over the tree, in the verification set. Grammar and block
form: [MECHANISM-FORMAT.md](./MECHANISM-FORMAT.md#the-rules-file).

A mechanism that injects nothing has no rules file. A project's own rules file, beside the
entry file, is the installer's other source, read through the same grammar and placed after
every mechanism's block; what it is and what it may override is R7's, installed at tier 1.

**A sentence about another mechanism is that mechanism's** *(the user, 2026-09-07)*. What
shapes how mechanisms are built around it — what `/maintain` must be handed at inception, for
one — is a rule in its rules file, installed here, never authored here. Its core function
reaches a session through its own description, strengthened at tier 1 where warranted; a
principle that resonates through the whole harness may land in `AGENTS.md` — that mechanism's
decision, rare, and investigated first.

## Mechanical by construction

A mechanism is designed from inception for mechanical derivation, checking and repair: its
identity, governing sources, dependencies and record contracts are explicit enough for a script
to enumerate what a change affects. Anything that can be maintained mechanically is; a missing
script is written as part of the repair; archived records are not exempt *(the user,
2026-09-05)*.

## What it produces

**Everything a mechanism produces is read by someone, or the doc says why nobody does**
*(the user, 2026-09-07)*. Name each artifact and its reader: a person at a stated moment, another
mechanism, a script, a check. An output with no reader is either dead weight or a missing reader,
and which of the two it is only becomes answerable once it is written down.

This covers what the mechanism emits as well as what it ships — a report nobody opens, a record
nothing indexes, a file dropped where nothing looks.

## Records

A mechanism with records declares what a record is — its fields, what a row means, its
tier, what removes a finished entry — in a format file beside its instruction file, referenced
from its doc and its skill, or in the skill itself where the format is small; never in the doc
*(the user, 2026-09-07; where, 2026-09-27)*.

<installed by="mechanism-shape">
**R1** Check a record-bearing mechanism's records with its maintainer script — format never
content, live rows only. Where the script is missing, write it: that is the maintenance.

**R4** Render an index on request; never commit one beside its records. A file listing what other
files each say for themselves is an index, whatever it is called — an allowlist, a register,
a manifest — and each entry belongs at its authored home, wrapped there if provisional.

**R5** Land a mechanism's rule in AGENTS.md only as an installed block from its rules file. While the
mechanism is undeclared, write the rule by hand and wrap it as a straw dog bound to the question
of what the mechanism owns, as you write it.

**R6** A skill is an instruction file of exactly one mechanism and opens its body with
`Mechanism: <slug>`. A skill no mechanism names opens it with `Mechanism:` then `not yet`,
wrapped as a straw dog bound to the question of what the skill owns, or `unowned by design` with
its reason. A script, test or hook a mechanism owns opens with `# Mechanism: <slug>`, after a
shebang where there is one. Write the line as you add the file; no list holds it.

**R8** Name no skill of a mechanism whose state is `installed` in another skill's own text: what it asks
of that skill reaches it as an installed block from its rules file.
</installed>

## Incept

1. **`/align` first**, on what the mechanism is in plain terms: its moments, its
   authority, its record shape, its index, the tier of each part, what retires it.
2. Write the doc to [MECHANISM-FORMAT.md](./MECHANISM-FORMAT.md), naming the parts it
   owns and the parts it relies on with their owners; and its rules file, installed before
   the doc is checked.
3. **Write the check before the thing it checks**, watching every diagnostic fail in
   both polarities.
4. **Run it over what already exists** and record the count of prior violations — or
   state that there was no prior corpus, rather than a manufactured zero.
5. Name what retires it.
6. **Name what would show it working, graded by someone who did not build it.**
   Pre-register it so a later session can answer without asking what was meant.

**Absence is not clearance**: a clean run means nothing was caught, never that the tree
obeys.

<installed by="maintain">
**M1** Name what `/maintain` must do for this mechanism — a maintainer script to run, records to
re-check when its surfaces move — as rules in its rules file targeting `/maintain`. Nothing is
written into `/maintain` by hand.
</installed>

## Amend and retire

Editing a skill that is an instruction file is amending its mechanism — run the steps
still live, aligning again when the shape itself moves. Amend a rule in its rules file, then
install it with overwrite; the block in a target is never the place. A mechanism is re-checked
when what governs it has moved; which skill does that is its doc's row, not this body's
sentence.

Retiring runs `--retract` first, then removes the mechanism's parts and its directory, its
own trigger among them. An always-on mechanism cannot be retired.

## Siblings

- [`/skill-up`](../skill-up/SKILL.md) writes a skill's text; this governs the system it
  belongs to. Both apply when a skill is an instruction file.
- [`/impact`](../impact/SKILL.md) traces a change's consequences; this asks whether a
  mechanism is sound at both ends.
- [`/maintain`](../maintain/SKILL.md) applies the shape's rules and owns none of them; what it
  asks of an inceptor is its own rule, installed above.
- [`/align`](../align/SKILL.md) is called by incept, before anything is built.
