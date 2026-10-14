---
name: harness
description: >-
  Use when asked to install the harness into a project, to update a tree that already holds it,
  or to confirm a copy is intact; and in a freshly installed tree, which has core and none of the
  project's own answers yet.
---

Mechanism: harness

The source is always the repository, cloned fresh at a ref; a working tree is never read. Where
that repository is, this tree says once:

Repository: https://github.com/dveyarangi/goodwolf-harness.git

That is the only authored home of it. The script reads its default `--from` there, an install
stamps a recipient's copy with the source the run actually read, and a fork edits the line once
and everything it installs names the fork. A check or an update from another `--from` sets the
line aside rather than reading an edit in core, as it does the local block and the block of any
mechanism of the tree's own.

Run the script from any clone of the harness, or from the tree's own copy once it has one. An
update is run by the incoming ref's installer, which reads what an earlier one left: run it from
a clone, since a tree's own copy may predate handing the run on.

```
python <clone>/.agents/scripts/gw/harness.py <target> --install [--replace-clone] [--from REPOSITORY] [--at REF]
python <clone>/.agents/scripts/gw/harness.py <target> --update [--overwrite] [--from REPOSITORY] [--at REF]
python <target>/.agents/scripts/gw/harness.py . --check [--from REPOSITORY]
python <target>/.agents/scripts/gw/harness.py . --links
```

`--from` defaults to the harness's own repository; `--at` to its default branch's head, and takes
a branch, a tag or a commit. To try a ref before it is pushed, pass a local clone's path as
`--from`: its committed `HEAD` is then the ref. The target is the top level of a git work tree.

`--links` is the per-clone step: the loader links are never committed, so a fresh clone of a
project that holds core runs it once, from the clone's own copy, with no source and no network.
It makes or repairs both links, names them in the clone's `.git/info/exclude`, and reports whether
each resolves; where the platform refuses, it prints the elevated commands and exits non-zero
until they have been run.

## What a run does

Copies every file under `.agents/` plus `AGENTS.md` and `CLAUDE.md`, the source's root
`LICENSE` as `.agents/LICENSE`, and its root `README.md` beside this skill, with the origin's local blocks removed and every straw-dog wrapper and `TODO` binding sheared so the rule stays and the question it waits on, which only this tree holds, does not;
stamps the entry file's announce line `<repository>@<ref>, <date>`, which is the tree's only
revision record and what every session there announces; merges core's hooks into each host's
shared hook file — `.claude/settings.json`, `.codex/hooks.json`, `.cursor/hooks.json` — beside the
project's own, an update replacing core's entries alone; makes the loader links; installs every
mechanism's rules and then the project's local file last; and runs the gate — the copy compared
against the ref, the injector's check, the shape check, in seconds. The report ends
`arrived: true` only when all three hold, and says beside it whether each loader link resolves.
The shipped suite is not run; a project that wants it runs it from its own verification set.
Whether a host reads the link is not observable from inside a tree; the first session announcing
the stamped line is the evidence a person reads.

## Refusals, and what to do

Every refusal writes nothing and names its step.

- **A link the platform refused to create** is not a refusal: everything else landed, and the
  report's `pending` lines are the exact commands. Present those for the hosts the person works
  in, verbatim, to run once in an elevated prompt; once they say they have, run `--links`
  yourself — it confirms each resolves without a source, and is never asked of the person.
- **A folder that is not a Git repository**: empty, the install runs `git init` there first and
  says so in its notes — every script of core reads a tree through Git, so a target is a
  repository. Holding files of its own, it is refused with the step: where the root goes is the
  person's decision, so they run `git init` there, or install at the root they mean.
- **A subfolder of a repository**: refused naming the top level. Install there; one installation
  is one tree.
- **Git refuses the target for dubious ownership**: the `.git` directory is owned by another
  identity than the one running — a sandbox and a shell often differ. The refusal carries Git's
  own `safe.directory` command; the person runs it once, then the install runs again.
- **A `<project-local>` block in the entry file**: its content is the project's and the file is
  overwritten. Move each fact into `local.rules.md` as a rule, delete the block, run again.
- **A core file that differs from the announced ref**: an edit made in core. Keep it out of core
  — a project's answer or override goes in the local file — and run `--update --overwrite`,
  which replaces the file and names it.
- **A file of the project's at a path the new ref adds**: refused naming it. Move it first, or
  run `--update --overwrite`, which replaces it and names it.
- **A tree that announces no ref**: a copy that predates this script. `--update --overwrite` is
  required; nothing is deleted, and files under `.agents/` outside the manifest are reported as
  the project's own.
- **The injector refused**: a malformed local file, an override naming a rule this ref no longer
  sends there, or a local anchor a new anchor now follows — asked before the copy. Fix the local
  file and run again.
- **Core already here, on an install**: a previous install, whole or stopped partway.
  `--update --overwrite` completes it.
- **A host's hook file that is not valid JSON, or sets a key core's hooks need otherwise**: the
  file is the project's as much as core's. Fix it by hand and run again; nothing rewrites it.
- **A junction, a directory or a file where a link goes**: the project's own. Move it; a symlink
  goes there.
- **No readable `Repository:` line beside the script**: with no `--from`, the script cannot tell
  where core comes from. Pass `--from` this once, then restore the line — it is what every later
  run reads.
- **A ref whose harness skill carries no such line**: not the harness, in the same sense as an
  entry file with no announce line. Check the ref, or the repository.
- **The source itself as target**: the origin is never installed into. A clean clone of it standing
  where the project was meant — the person asked for an install there and the host cloned — is
  turned into one from inside it, `harness.py . --install --replace-clone`: the tree is emptied,
  a repository begun afresh, and core installed at the clone's commit. A clone holding anything of
  its own — a change, an ignored file, a commit its origin's branches lack — is somebody's work and
  is refused: install into the project's own folder instead.

## Friction goes upstream

File any friction in a run — a crash, a workaround, a step this skill did not foresee — as an issue
on the harness's repository: the ref, the command, the platform, the step, the error verbatim, the
workaround. Nothing of the project's own. A workaround
left in the recipient links the issue.

## After the first install

The tree has core and no answers, and its entry file arrived after this session began, so none of
its rules are in your context: read it now — from here they govern this session, as they will
every next one. Write `local.rules.md` beside the entry file, in the rules-file format the entry file's *Project-local* section describes, from the environment you stand in: the
project's facts for the entry file, its autonomy switches, and its verification set — its
typechecker, its tests, every command required of landed work, read off its own toolchain, a
project without one having none of its own and its local file saying so; and, offered beside them,
the harness's checks. Then `inject_rules.py local --install`, and `--check`.
That check is the install's verification: the `commit` switch just written decides the install's
commit, as it decides any other, named in the project's own convention where it states one.

The person asked for a method to work by, not for files. Before asking anything, introduce it in
their language, in a few lines: who you now are to them, what you will do for them, and where you
stop for their yes. Ask each answer with the reason a project would choose it, in their terms —
*commit on my own once the checks pass, or ask each time* — never as a switch's name and values;
the origin's own answers, read in its clone, are not this project's and are offered as no default.
The harness's checks
are two kinds: those of the records the method keeps — `tickets.py`, `questions.py`, `edges.py`,
`product.py`, `maintain.py` — serve every project that works by it; those of core itself — `mechanisms.py`,
`inject_rules.py` — serve a project that means to change the harness. End with the first question the work asks. What was copied, gated and registered stays in the
files and the commit, said on request.

`uv run --offline --no-project python` is the harness's own habit; the scripts need only the
standard library, so a bare `python` works.
