---
name: skill-up
description: >-
  Aid agent skill creation or modification. Use when creating a new skill or changing an existing one.
---

Your goal is to aid agent skill creation or modification.

Writing rules:

- A skill is instruction, not story. Be precise and concise. Prefer umbrella terms to enumeration, unless can be interpreted wrong in context of the skill.
- State everything in definitive form — no evolution logic, no decision explanations.
- Blur wording where letting the model decide beats overfitting the instruction.

Before writing, browse the existing skill set and match its structure and vibe — frontmatter shape, file layout, linking style, tone, altitude. Derive the set's conventions from the set itself; do not impose foreign ones.

Verify the new or changed skill against the set:

- It does not overlap an existing skill, unless the overlap is intentional — then name it and link the owning skill.
- It does not contradict any existing skill.
- It does not misfit the set — wrong altitude, wrong output location, conventions the set does not use.

A fact the set already states in one skill is referenced from there, not restated.

The frontmatter description narrates the use case, not the implementation, and stays in line with the skill's intent. Capturing skill intent and usage is critical — /align when in tiniest doubt.

## Project-local divergence

A skill's core is portable; a project's own conventions are not. Keep every `SKILL.md` body free of project facts, so the set stays mergeable with the corpus it came from, and hold what is genuinely local behind a reference:

- Prefer an appendix file — `*-FORMAT.md`, `REFERENCE.md` — which may diverge freely.
- Where a file is too much, a compact `<project-local>` block closes the `SKILL.md`; the tag is the declaration, so it needs no sentence saying so.
- An appendix points at the project's own documentation for anything that documentation owns; it never restates it.

A body instruction that cannot be written without a project fact belongs in the appendix instead. The project's development process — `docs/process.md`, built up lazily as the process itself incepts or changes — is a corpus convention like `glossary.md`, so a body may cite it by name; its contents are the project's own.

A `<project-local>` block adds local facts; it never overrides the body.

## Merging a reference corpus

When asked to merge the skill corpus, ask which corpus to merge from.
Port body changes, fixing defects as you port; leave every appendix file and `<project-local>` block as it stands. A skill present in only one corpus is either local by intent or not yet ported — ask which.
