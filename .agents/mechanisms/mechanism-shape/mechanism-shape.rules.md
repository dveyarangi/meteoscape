# mechanism-shape — rules installed into skills

Machine input for the installer, read by nobody at session time. Amend a rule here, then
install it with overwrite; the block in a target is never the place.

| target | anchor |
|---|---|
| `.agents/skills/maintain/SKILL.md` | `## Installed from other mechanisms` |
| `.agents/skills/mechanism/SKILL.md` | `## Records` |
| `.agents/skills/align/SKILL.md` | `### Land resolutions as they are made` |
| `.agents/skills/skill-up/SKILL.md` | `## Installed from other mechanisms` |
| `AGENTS.md` | `## Project-local` |
| `.agents/skills/verify/SKILL.md` | `## The verification set` |

## R1 — records are checked by their maintainer script

- **target** `.agents/skills/maintain/SKILL.md`
- **target** `.agents/skills/mechanism/SKILL.md`
- **authority** the user, 2026-09-07

<rule>
Check a record-bearing mechanism's records with its maintainer script — format never
content, live rows only. Where the script is missing, write it: that is the maintenance.
</rule>

## R2 — a mechanism is compared against what governs it

- **target** `.agents/skills/maintain/SKILL.md`
- **authority** the user, 2026-09-07

<rule>
Compare a mechanism against what governs it with line endings normalised, its evidence
excluded, and installed blocks excluded.
</rule>

## R3 — story leaves the doc

- **target** `.agents/skills/maintain/SKILL.md`
- **authority** the user, 2026-09-07

<rule>
Move story out of a doc into its evidence.
</rule>

## R4 — an index is derived

- **target** `.agents/skills/maintain/SKILL.md`
- **target** `.agents/skills/mechanism/SKILL.md`
- **authority** the user, 2026-09-07

<rule>
Render an index on request; never commit one beside its records. A file listing what other
files each say for themselves is an index, whatever it is called — an allowlist, a register,
a manifest — and each entry belongs at its authored home, wrapped there if provisional.
</rule>

## R5 — a mechanism's rule reaches the entry file installed

- **target** `.agents/skills/align/SKILL.md`
- **target** `.agents/skills/mechanism/SKILL.md`
- **authority** the user, 2026-09-20; the binding a question, 2026-10-04

<rule>
Land a mechanism's rule in AGENTS.md only as an installed block from its rules file. While the
mechanism is undeclared, write the rule by hand and wrap it as a straw dog bound to the question
of what the mechanism owns, as you write it.
</rule>

## R6 — a part names its mechanism

- **target** `.agents/skills/skill-up/SKILL.md`
- **target** `.agents/skills/mechanism/SKILL.md`
- **authority** the user, 2026-09-08; the binding a question, 2026-10-04; one owner, not one skill,
  2026-10-10; every part naming its mechanism, 2026-10-11

<rule>
A skill is an instruction file of exactly one mechanism and opens its body with
`Mechanism: <slug>`. A skill no mechanism names opens it with `Mechanism:` then `not yet`,
wrapped as a straw dog bound to the question of what the skill owns, or `unowned by design` with
its reason. A script, test or hook a mechanism owns opens with `# Mechanism: <slug>`, after a
shebang where there is one. Write the line as you add the file; no list holds it.
</rule>

## R7 — a project's answers live in its local file

- **target** `AGENTS.md`
- **target** `.agents/skills/verify/SKILL.md`
- **authority** the user, 2026-09-10

<rule>
A project's own answers and overrides are authored in one file beside the entry file,
`local.rules.md`, in the rules-file format, and reach a file only as the local block — the
installed block whose owner is `local` — which the installer writes after every mechanism's block
there, so the project's answer is what a reader meets after core's rule. An override names the rule it
overrides. A local change to a rule is written in the local file, never into a skill or the entry
file, and re-installed. The local block is the project's,
not core's, and a redeploy preserves it.
</rule>

## R8 — an installed mechanism is reached by its rules, not by name

- **target** `.agents/skills/skill-up/SKILL.md`
- **target** `.agents/skills/mechanism/SKILL.md`
- **authority** the user, 2026-09-27

<rule>
Name no skill of a mechanism whose state is `installed` in another skill's own text: what it asks
of that skill reaches it as an installed block from its rules file.
</rule>
