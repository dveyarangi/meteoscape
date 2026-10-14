---
name: verify
description: >-
  Use after an implementation pass, or to verify a landed slice before close.
  Whole verification of landed work: ticket, RFC, governing docs, and the
  project's verification set. Repair-and-report where that policy holds.
---

Mechanism: not yet

Compare the work to its ticket, RFC if any, governing docs, and every check
in the project's [verification set](#the-verification-set).
Find out:

- How well the work matches and represents the documentation
- Where the work went wrong or weird because of underspecification or
  contradiction in the docs
- Whether the verification set's checks hold

Look for architectural or responsibility leakage.

## Installed from other mechanisms

<installed by="edge">
**E4** When the landed work changes an edge — a promise in its Contract or Invariants, an invariant's
validator, or a check of its Extending — the same commit writes its record under `docs/edge/`. A
promise the landing makes true loses its `⚠ pending` mark, and the record leaves
`Normative (tentative)` when no mark is left; a landing that breaks a promise no decision changed
is a finding, never written into the record. The Roadmap entry of the ticket that landed is
removed. An extension observed live in this work has what was seen written in its sidecar, dated,
not only in the ticket or the session record.
</installed>

## The verification set

The project's verification set is its typechecker, its tests and every other command required
of landed work, named in the project's local rules file and installed here as the local block. A
failed check is unfinished work.
Discovery reporting success with zero tests is not verification; the run must show a positive
count. A clean run means nothing was caught, never that the tree obeys. `/implement` may run
named checks during the work; that run is not this pass.

<installed by="mechanism-shape">
**R7** A project's own answers and overrides are authored in one file beside the entry file,
`local.rules.md`, in the rules-file format, and reach a file only as the local block — the
installed block whose owner is `local` — which the installer writes after every mechanism's block
there, so the project's answer is what a reader meets after core's rule. An override names the rule it
overrides. A local change to a rule is written in the local file, never into a skill or the entry
file, and re-installed. The local block is the project's,
not core's, and a redeploy preserves it.
</installed>

<installed by="local">
**L3** The verification set: the project's CI and the harness's record checks, every one green.

```
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
```

```
uv run python .agents/scripts/gw/tickets.py --check
uv run python .agents/scripts/gw/edges.py --check
uv run python .agents/scripts/gw/questions.py --check
uv run python .agents/scripts/gw/product.py --check
uv run python .agents/scripts/gw/maintain.py --check
```
</installed>


## Check and repair

- Cross-check documents against each other and against code, in both directions.
  Ask whether the implementation contract could be reconstructed from the architecture
  alone; a load-bearing decision visible only in code is a documentation finding.
- Code that contradicts an accepted decision is a code finding. Do not settle a
  contradiction by weakening the rule.
- Check named validators still exist and still assert the promise they were named for.
  A missing or drifted validator is a finding, as is an unguarded normative promise.
  A promise about something that already exists — a recipient's tree, a stored record — is
  asserted only by a fixture built the way that thing came to be: one the code under test
  made cannot hold a shape that code now refuses, or lack a file that code now ships.
- Sweep the question store, `docs/questions/`, for entries in scope: a question the
  implementation has since answered closes with a pointer to its owning record, and a dead
  trigger retires.
- Apply repair-and-report — the entry file's `repair` switch — where it holds:
  make the repair, verify it, and record the violated rule, the change, the verification
  result and any remaining uncertainty in the owning work item.
- Everything else goes to [/align](../align/SKILL.md): a missing, ambiguous or
  contradictory rule, a new foundational decision, or work beyond the authorization.
  Pause that change; independently authorized work continues.

- Read the landed work against the open questions. What one's answer will change is a straw
  dog: wrap it and bind it to that question, per the entry file, and leave what no open question
  would change alone. Run `straw_dogs.py --guess` over the files the slice touched and judge its
  candidates.

Discrepancies:

- If repair-and-report holds — the four conditions under the entry file's `repair` switch —
  make the repair, verify it, and report in the owning work item. Cite the
  violated rule, what changed, the verification result and any remaining
  uncertainty. The `repair` switch is in `AGENTS.md`.
- Otherwise `/align`: present the discrepancy, affected constraints,
  recommended resolution and the decision needed. Do not amend until that
  returns.
- Do not rewrite a governing rule, weaken a validator or relax acceptance
  criteria to make a violation disappear. Action permissions (`commit`, `push`)
  still apply.

A missing RFC is not a defect of this skill when the ticket has none.

- Docstrings say what their own unit does. Apply
  [/improve-comments](../improve-comments/SKILL.md) to comments in scope and check
  that TODO tags still describe something pending.
- Read the pointers in the slice's code: each names, word for word, a heading or a bold lead that
  the record it points into holds. One that does not is a finding.


Apply `/plan` rules that help this review. Do not start a whole-tree
maintenance pass; `/maintain` owns that.
