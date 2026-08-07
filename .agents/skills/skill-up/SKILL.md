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
