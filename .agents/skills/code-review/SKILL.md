---
name: code-review
description: >-
  Rules for reviewing code changes.
---


The goal of this skill is to compare current works input documentation (ticket, RFC and architectural docs) and the code and find out:
- How good the code shape matches and represents the documentation?
- Where the code shape went wrong or weird because of underspecification or contradiction in the docs?

If discrepancies found, describe them in short and suggest ways to amend documentation or/and code. Do not make changes until requested. 

- In case RFC (original or amended) describes undocumented architecture, make sure to point this out as a discrepancy.

In overall we must make sure that architecture -> ticket -> RFC -> code is as unambiguous and correct as possible.

Apply /sync-arch skill rules that you think are useful for this task.