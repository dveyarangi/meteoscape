# Mechanism format

This shelf owns the mechanism directory, the doc's sections, the two tables a script
parses, and the record shape of the mechanism set itself. What a mechanism *is*, and
how one is incepted, amended or retired, is [/mechanism](./SKILL.md)'s.

## Directory

```
.agents/mechanisms/<slug>/
    <slug>.md          the doc — required, exactly one
    <slug>.rules.md    the rules file — only if the mechanism injects
```

The slug is the directory name, lowercase and hyphenated; every filename repeats it. **No bullet
declares the rules file** — it is found by that name, so a second statement of it could only
disagree with the directory.

**The directory holds these two files and nothing else.** Working parts live where the harness
needs them: skills in `.agents/skills/`, scripts in `.agents/scripts/gw/`, tests in
`.agents/scripts/gw/test/`. A file
put here was put here to be read, and nothing reads it, so the check reports it.

The rules file is machine input, read by the installer alone and never at session time. Its
grammar is [The rules file](#the-rules-file) below.

## The rules file

```md
# <slug> — rules installed into skills

| target | anchor |
|---|---|
| `.agents/skills/maintain/SKILL.md` | `## Installed from other mechanisms` |

## R1 — <title>

- **target** `.agents/skills/maintain/SKILL.md`
- **authority** the user, 2026-09-07

<rule>
Check a record-bearing mechanism's records with its maintainer script — format never
content, live rows only. Where the script is missing, write it: that is the maintenance.
</rule>
```

Prose before the table is the file's own preamble and is not read.

- **The anchor table** names every target the file installs into, one row each: the target a
  backticked repo-relative path, the anchor a backticked line that occurs exactly once in the
  target, whole and newline-terminated. **A mechanism has one place in a target**: a target
  named twice is refused.
- **One `## ` section per rule.** The heading's first token, before ` — `, is the rule's id,
  unique in the file. **target** repeats, one path per bullet, each a row of the table.
  **authority** is who decided the rule and when, read and reported, never interpreted.
  **overrides**, at most once, names the core rule this one replaces as `` `<slug>/<id>` ``: the
  slug must have a rules file, the id must be in it, and that rule must name every target this
  section names — read from its declared targets, never from whether its block is present — or
  the section is refused naming this rule. The citation is rendered into the block, after the
  id, as `*(overrides <slug>/<id>)*`, so a reader meets the disagreement where they meet the rule.
- **The body** is the span between a line that is exactly `<rule>` and a line that is exactly
  `</rule>`, installed byte for byte. It holds no markdown citation — the mover rewrites a
  relative link per the file it sits in, so one body in two directories would drift apart — no
  heading line, no `<installed` or `</installed>`, and no `<straw-dog>`. A section with two spans,
  or none, is refused.
- **A rule that expires is wrapped around its section**: the tag opens before the heading and
  closes after `</rule>`, outside the body, so a target receives the rule and never the wrapper.
  A tag inside a body is refused.

**What the installer writes**, per target: one block holding every rule of the file that names
it, in file order, each a paragraph opening with its id, into the section the anchor heads:

```md
<installed by="mechanism-shape">
**R1** Check a record-bearing mechanism's records with its maintainer script — format never
content, live rows only. Where the script is missing, write it: that is the maintenance.

**R2** Compare a mechanism against what governs it with line endings normalised, its evidence
excluded, and installed blocks excluded.
</installed>
```

The block is found by its tag, never by its body, and compared whole against what the rules
file renders. **A rules file's block is installed in every target it names, or the check
fails**: an absent block, a drifted one, and a block nothing owns — its slug has no rules file,
or that file does not name the file the block sits in — are each a diagnostic. Every example of the tag or an anchor in a doc sits in a code span or fence, on one
line; the installer looks through code and never takes an example for the thing.

The installer: `inject_rules.py <slug> --install [--overwrite]`, `<slug> --retract`, `--check`.
A named mode or a refusal; every target validated before anything is written; retraction
leaves the target byte-identical; a differing block refuses until the caller says overwrite,
and then the block is replaced whole and the report carries what it replaced. The contract is
the architecture's; the entry file owns the prohibition on editing a block in place.

**The project's own rules file is one more source.** `local.rules.md` sits beside the entry
file, outside the core directory, in this same grammar, and is read as the slug `local` — a
mechanism directory of that name is refused. Its block must be the last in its file, so anchor a
local rule where every mechanism's block precedes it.

## The doc

```md
# <slug> — <what it is, in one line>

- **instruction** `<path>` — what it holds
- **state** always on
- **record of** what must always hold

## How it works

## Moments

## Install adds, uninstall removes

## Relies on, and does not own

## What it produces, and who reads it

## Not yet at the shape

## What retires this

## What would show it working, graded by someone who did not build it
```

Sections appear in this order. All but the two tables are prose and are never parsed — but two
absences are diagnostics. A doc missing the **grading** section names no grader, and has been
labelled rather than declared. A doc missing **What it produces, and who reads it** leaves its
outputs unaccounted: every artifact a mechanism emits or ships names its reader there — a person
at a stated moment, another mechanism, a script — or the section says why nobody reads it. Who the
reader is, and whether they are enough, is judgment and never the check's; that the question was
answered at all is not.

**An output listed by a bullet names its kind**, after its name, before its reader:
`- **<output>** — *<kind>* — <who reads it>`. The kind is one of the four kinds of record —
*what it intends to become*, *what must always hold*, *what exists*, *what happened* — or
*its format's*, for an output that is a record of another mechanism and takes the kind that
format declares. A record whose kind moves with its state names the first and the rule after
it: *what it intends to become, what happened once closed*. A bullet with no kind, or another,
is a diagnostic; the section's prose and nested bullets name no output.

**The title line names the job, not the procedure.** What the mechanism is for and holds true,
never the steps its script runs — a declaration written beside its implementation takes the
script's verbs, and a reader then cannot tell what the mechanism would still own if the
implementation changed.

### Header bullets

- **instruction** — backticked repo-relative path to a skill the mechanism owns.
  Required, and never the doc itself.
  One bullet: a declaration names one skill, and a second skill
  of the same mechanism has no field to stand in.
- **state** — `always on` or `installed`, and nothing else. `always on` means nothing can install
  or uninstall it, so it has no lifecycle scripts and that absence is a property. It is what tells
  a reader which way to read the parts table.
- **record of** — `what must always hold`, and nothing else: the doc is the record its
  instruction is repaired to. This format is the kind's authored home; the bullet is the kind
  where an agent editing the doc meets it, and the check holds the two equal. The bullet's
  earlier name, `kind`, is reported.
- There is no evidence bullet. The evidence is a record declared under [Records](#the-evidence-is-a-record-of-the-shape)
  below and found by the slug; the doc never names it, since it is the instance's and a recipient
  does not have it. Which ticket declared the mechanism is the evidence's first paragraph *(the
  user, 2026-09-09)*: the one check that read such a bullet is replaced by the rule that a
  `not yet` row may not wait on a question already answered, which needs no field.

## Moments

```md
| moment | instructed by | kind, and why |
```

- **moment** — the occasion, in the words a person would use for it.
- **instructed by** — a backticked path, or `—`.
- **kind, and why** — empty when the row is instructed. Otherwise one of `elsewhere`,
  `embedded`, `unowned by design`, `not yet`, a clause saying why, and — for all but
  `unowned by design` — its referent.

A row carries an instruction or an absence, never both and never neither.

A `not yet` row is a straw dog *(the user, 2026-09-20)*:

```md
| ordering the queue | — | <straw-dog question="q-N">not yet</straw-dog> |
```

Body: the kind alone; the referent is the question, and its words are the reason. A row
waiting on a question that is due, merged or superseded is a diagnostic. Unwrapped is unbound.
The shear strips the wrapper, so no id of this tree ships. The lister reports the row; this
check rules on the gap.

## The two tables

```md
| part | where |                 under "Install adds, uninstall removes"
| part | where | owner |         under "Relies on, and does not own"
```

The first title is its definition: **if uninstalling would not remove it, it is not a
part**. For an `always on` mechanism the same table is what a person moving it between
trees takes.

Relied-on parts never become an owner column on the first table — they are not added
by install, so listing them there contradicts its title.

**part** is a role name and may repeat. **where** is a backticked repo-relative path,
optionally with an anchor:

```
`.agents/skills/align/SKILL.md` → "### Challenge against the Edge records"
```

The phrase after `→` is checked as a verbatim substring of the file named. An owned part
is a whole file: in another's file a mechanism owns only what it installs there, which
its rules file names. The anchor serves a relied-on line — a heading another skill
carries, where a block is installed — so a line moved or renamed fails the check.

## Records

A mechanism that writes records declares each one where that record's format is declared — a
format file beside its instruction file, or its skill where the format is small; never its doc.
Three fields:

- **what a record is** — one file, one directory, or one row of a file that holds many.
- **tier** — when it is read.
- **what removes an entry** — the condition; `kept by design` where nothing does; or `not yet`,
  a straw dog bound to the question it waits on.

A record declared without all three is a diagnostic, and so is a mechanism that writes records and
declares none.

Neither diagnostic is emitted yet: finding a mechanism that owes a record declaration needs
`record-bearing` to be a declared field, which it is not. Until then the two sentences above are a
rule with no check behind them.

## Parsing

- Cells split on unescaped `|`; a literal pipe is `\|`.
- A row whose cell count differs from its header is a diagnostic, not a silent
  misparse.
- Every path is backticked and repo-relative; no cell carries a markdown link.
- An absence cell's referent is its binding, else its **first** code span — so one code span
  per cell, other skills named in words. A wrapper around any other kind is read for its body.
- Prose, the taxonomy's correctness, and whether a moment should exist are judgment. A
  script records them and rules on none of them.

## A part's claim

A file an agent edits says which mechanism's doc governs it, on its first line, so the agent
meets the doc where it works. The files that carry it are a mechanism's instruction file and
every part of its *Install adds, uninstall removes* table under `.agents/scripts/` — its
scripts, tests and hook. The doc and the rules file sit in the mechanism's own directory and a
shelf beside its skill, so their place already says whose they are; a file whose format holds
no comment carries none.

A skill a declaration names opens its body, after the frontmatter, with that mechanism's slug:

```md
Mechanism: ticket
```

Code opens with it as a comment, after a shebang where there is one:

```python
# Mechanism: ticket
```

The slug resolves to the doc by the directory rule above, so the line never names a path under
`docs/`. A skill no declaration names says so in the same place, with `Mechanism:` then the
moments grammar, `not yet` or `unowned by design` only:

```md
<straw-dog question="q-N">Mechanism: not yet</straw-dog>
```

That line is a straw dog like a `not yet` row; it becomes the slug when a declaration names the
skill. The check holds each line to the parts tables both ways: a part naming no mechanism or
another, a skill both named and claiming `not yet`, a skill naming a mechanism whose declaration
does not name it, and a script naming one whose parts do not list it are each a diagnostic. No
list holds these lines: each sits at its authored home.

## The evidence is a record of the shape

- **A record** is one file per mechanism, `docs/mechanisms/<slug>.evidence.md`, in the instance
  half: why the doc is what it is. A mechanism with none yet is a legitimate state.
- **Tier 2** — read at amend time, by whoever is about to change the doc.
- **What removes an entry**: the mechanism being retired. The file never moves.

## The mechanism set is its own register

No file holds the register. `.agents/mechanisms/<slug>/` is the enumeration, and the
index is rendered from the directories on request.

- **A record** is one mechanism directory; its fields are the header bullets above and
  its shape is this document.
- **Tier 2** — read when installing, amending or debugging a mechanism.
- **What removes an entry**: the mechanism being retired. A directory that outlives its
  mechanism is drift.
- **The index is derived and never committed.** A doc edit shows on the next render; a
  doc that cannot be parsed is reported rather than dropped.
